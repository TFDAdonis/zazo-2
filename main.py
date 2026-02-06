import streamlit as st
import json
import tempfile
import os
import pandas as pd
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import ee
import traceback
import google_auth_oauthlib.flow
from googleapiclient.discovery import build

# Page configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="Khisba GIS - 3D Global Vegetation Analysis",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== CUSTOM CSS (Updated with Auth Styles) ====================

st.markdown("""
<style>
    /* Base styling */
    .stApp {
        background: #000000;
        color: #ffffff;
    }
    
    /* Remove Streamlit default padding */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Green & Black Theme */
    :root {
        --primary-green: #00ff88;
        --accent-green: #00cc6a;
        --primary-black: #000000;
        --card-black: #0a0a0a;
        --secondary-black: #111111;
        --border-gray: #222222;
        --text-white: #ffffff;
        --text-gray: #999999;
        --text-light-gray: #cccccc;
        --success-green: #00ff88;
        --danger-red: #ff4757;
        --warning-orange: #ffa502;
    }
    
    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-weight: 600;
        letter-spacing: -0.025em;
        color: var(--text-white) !important;
    }
    
    h1 {
        font-size: 2rem !important;
        background: linear-gradient(90deg, var(--primary-green), var(--accent-green));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem !important;
    }
    
    h2 {
        font-size: 1.5rem !important;
        color: var(--primary-green) !important;
    }
    
    h3 {
        font-size: 1.25rem !important;
        margin-bottom: 1rem !important;
    }
    
    /* Auth Container */
    .auth-container {
        max-width: 420px;
        margin: 80px auto;
        padding: 20px;
    }
    
    .auth-card {
        background: var(--card-black);
        border: 1px solid var(--border-gray);
        border-radius: 12px;
        padding: 30px;
        backdrop-filter: blur(10px);
    }
    
    .auth-header {
        text-align: center;
        margin-bottom: 30px;
    }
    
    .auth-logo {
        width: 80px;
        height: 80px;
        background: rgba(0, 255, 136, 0.1);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 20px;
        border: 2px solid var(--primary-green);
    }
    
    .auth-logo svg {
        width: 40px;
        height: 40px;
        color: var(--primary-green);
    }
    
    /* Form Fields */
    .form-group {
        margin-bottom: 20px;
        position: relative;
    }
    
    .form-label {
        display: block;
        margin-bottom: 8px;
        color: var(--text-light-gray);
        font-size: 14px;
        font-weight: 500;
    }
    
    .form-input {
        width: 100%;
        background: var(--secondary-black) !important;
        border: 1px solid var(--border-gray) !important;
        color: var(--text-white) !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
        transition: all 0.2s ease;
    }
    
    .form-input:focus {
        border-color: var(--primary-green) !important;
        box-shadow: 0 0 0 3px rgba(0, 255, 136, 0.1) !important;
        outline: none;
    }
    
    .form-input-with-icon {
        padding-left: 44px !important;
    }
    
    .form-icon {
        position: absolute;
        left: 16px;
        top: 50%;
        transform: translateY(-50%);
        color: var(--text-gray);
        transition: color 0.2s ease;
    }
    
    .form-group:focus-within .form-icon {
        color: var(--primary-green);
    }
    
    /* Password Toggle */
    .password-toggle {
        position: absolute;
        right: 16px;
        top: 50%;
        transform: translateY(-50%);
        background: none;
        border: none;
        color: var(--text-gray);
        cursor: pointer;
        padding: 4px;
    }
    
    .password-toggle:hover {
        color: var(--primary-green);
    }
    
    /* Checkbox */
    .checkbox-container {
        display: flex;
        align-items: center;
        gap: 10px;
        cursor: pointer;
    }
    
    .checkbox-input {
        width: 18px;
        height: 18px;
        accent-color: var(--primary-green);
        cursor: pointer;
    }
    
    .checkbox-label {
        color: var(--text-light-gray);
        font-size: 14px;
        cursor: pointer;
    }
    
    /* Auth Button */
    .auth-button {
        width: 100%;
        background: linear-gradient(90deg, var(--primary-green), var(--accent-green));
        color: var(--primary-black) !important;
        border: none !important;
        padding: 14px 24px !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        letter-spacing: 0.5px;
        transition: all 0.3s ease !important;
        margin-top: 10px !important;
        cursor: pointer !important;
    }
    
    .auth-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 255, 136, 0.3) !important;
    }
    
    .auth-button:disabled {
        opacity: 0.6;
        cursor: not-allowed !important;
    }
    
    /* Loading Spinner */
    .loading-spinner {
        width: 20px;
        height: 20px;
        border: 3px solid rgba(255, 255, 255, 0.3);
        border-top: 3px solid var(--text-white);
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 0 auto;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* Divider */
    .divider {
        display: flex;
        align-items: center;
        margin: 25px 0;
        color: var(--text-gray);
        font-size: 13px;
    }
    
    .divider::before,
    .divider::after {
        content: "";
        flex: 1;
        border-bottom: 1px solid var(--border-gray);
    }
    
    .divider span {
        padding: 0 15px;
    }
    
    /* Social Buttons */
    .social-buttons {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        margin-top: 20px;
    }
    
    .social-button {
        padding: 12px !important;
        background: var(--secondary-black) !important;
        border: 1px solid var(--border-gray) !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }
    
    .social-button:hover {
        border-color: var(--primary-green) !important;
        transform: translateY(-2px);
    }
    
    .social-icon {
        color: var(--text-white);
        transition: color 0.3s ease;
    }
    
    .social-button:hover .social-icon {
        color: var(--primary-green);
    }
    
    /* Toggle Link */
    .toggle-link {
        text-align: center;
        margin-top: 25px;
        color: var(--text-gray);
        font-size: 14px;
    }
    
    .toggle-link a {
        color: var(--primary-green);
        text-decoration: none;
        font-weight: 500;
        cursor: pointer;
    }
    
    .toggle-link a:hover {
        text-decoration: underline;
    }
    
    /* Status Messages */
    .status-message {
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 20px;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .status-success {
        background: rgba(0, 255, 136, 0.1);
        border: 1px solid rgba(0, 255, 136, 0.3);
        color: var(--primary-green);
    }
    
    .status-error {
        background: rgba(255, 71, 87, 0.1);
        border: 1px solid rgba(255, 71, 87, 0.3);
        color: var(--danger-red);
    }
    
    /* Layout Container */
    .main-container {
        display: flex;
        gap: 20px;
        max-width: 1800px;
        margin: 0 auto;
    }
    
    .sidebar-container {
        width: 320px;
        flex-shrink: 0;
    }
    
    .content-container {
        flex: 1;
        min-width: 0;
    }
    
    /* Cards */
    .card {
        background: var(--card-black);
        border: 1px solid var(--border-gray);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        transition: all 0.2s ease;
    }
    
    .card:hover {
        border-color: var(--primary-green);
    }
    
    .card-title {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--border-gray);
    }
    
    .card-title .icon {
        width: 32px;
        height: 32px;
        background: rgba(0, 255, 136, 0.1);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--primary-green);
        font-size: 16px;
    }
    
    /* Buttons */
    .stButton > button {
        width: 100%;
        background: linear-gradient(90deg, var(--primary-green), var(--accent-green));
        color: var(--primary-black) !important;
        border: none;
        padding: 12px 20px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 14px;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        margin: 5px 0;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0, 255, 136, 0.3);
    }
    
    /* Status badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        background: rgba(0, 255, 136, 0.1);
        color: var(--primary-green);
        border: 1px solid rgba(0, 255, 136, 0.3);
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    
    /* User info badge */
    .user-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 12px;
        background: rgba(0, 255, 136, 0.1);
        border: 1px solid rgba(0, 255, 136, 0.3);
        border-radius: 20px;
        font-size: 12px;
        color: var(--primary-green);
    }
    
    .user-badge img {
        width: 24px;
        height: 24px;
        border-radius: 50%;
    }
    
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==================== AUTHENTICATION SYSTEM ====================

def initialize_session_state():
    """Initialize session state variables for authentication"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'auth_mode' not in st.session_state:
        st.session_state.auth_mode = 'login'  # 'login' or 'signup'
    if 'show_password' not in st.session_state:
        st.session_state.show_password = False
    if 'remember_me' not in st.session_state:
        st.session_state.remember_me = False
    if 'auth_loading' not in st.session_state:
        st.session_state.auth_loading = False

def render_auth_page():
    """Render the authentication page"""
    
    # Toggle between login and signup
    def toggle_auth_mode():
        st.session_state.auth_mode = 'signup' if st.session_state.auth_mode == 'login' else 'login'
        st.session_state.show_password = False
    
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    
    # Header
    st.markdown('<div class="auth-header">', unsafe_allow_html=True)
    st.markdown('<div class="auth-logo">🌍</div>', unsafe_allow_html=True)
    st.markdown('<h1 style="text-align: center; margin-bottom: 5px;">KHISBA GIS</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #999999; margin-bottom: 30px;">Interactive 3D Global Vegetation Analytics</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Form
    if st.session_state.auth_mode == 'login':
        st.markdown('<h2 style="text-align: center; margin-bottom: 25px;">Sign In</h2>', unsafe_allow_html=True)
    else:
        st.markdown('<h2 style="text-align: center; margin-bottom: 25px;">Create Account</h2>', unsafe_allow_html=True)
    
    with st.form(key="auth_form"):
        if st.session_state.auth_mode == 'signup':
            # Name field for signup
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown('<div class="form-group">', unsafe_allow_html=True)
                st.markdown('<label class="form-label">First Name</label>', unsafe_allow_html=True)
                first_name = st.text_input(
                    "First Name",
                    key="first_name",
                    label_visibility="collapsed",
                    placeholder="John"
                )
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="form-group">', unsafe_allow_html=True)
                st.markdown('<label class="form-label">Last Name</label>', unsafe_allow_html=True)
                last_name = st.text_input(
                    "Last Name",
                    key="last_name",
                    label_visibility="collapsed",
                    placeholder="Doe"
                )
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Email field
        st.markdown('<div class="form-group">', unsafe_allow_html=True)
        st.markdown('<label class="form-label">Email Address</label>', unsafe_allow_html=True)
        email = st.text_input(
            "Email",
            key="auth_email",
            label_visibility="collapsed",
            placeholder="you@example.com"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Password field
        st.markdown('<div class="form-group">', unsafe_allow_html=True)
        st.markdown('<label class="form-label">Password</label>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 0.1])
        with col1:
            password_type = "text" if st.session_state.show_password else "password"
            password = st.text_input(
                "Password",
                type=password_type,
                key="auth_password",
                label_visibility="collapsed",
                placeholder="Enter your password"
            )
        
        with col2:
            eye_icon = "👁️‍🗨️" if st.session_state.show_password else "👁️"
            if st.button(eye_icon, key="toggle_password"):
                st.session_state.show_password = not st.session_state.show_password
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Remember me checkbox
        st.markdown('<div class="checkbox-container">', unsafe_allow_html=True)
        remember_me = st.checkbox(
            "Remember me",
            value=st.session_state.remember_me,
            key="auth_remember_me"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Submit button
        submit_text = "Sign In" if st.session_state.auth_mode == 'login' else "Create Account"
        submit_disabled = st.session_state.auth_loading
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submit_button = st.form_submit_button(
                label=submit_text,
                disabled=submit_disabled,
                type="primary",
                use_container_width=True
            )
        
        if submit_button:
            if st.session_state.auth_mode == 'login':
                handle_login(email, password, remember_me)
            else:
                handle_signup(email, password, f"{first_name} {last_name}", remember_me)
    
    # Social login divider
    st.markdown('<div class="divider"><span>Or continue with</span></div>', unsafe_allow_html=True)
    
    # Social buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("GitHub", key="github_auth", use_container_width=True):
            st.info("GitHub authentication coming soon!")
    with col2:
        if st.button("Google", key="google_auth", use_container_width=True):
            st.info("Google authentication coming soon!")
    with col3:
        if st.button("Twitter", key="twitter_auth", use_container_width=True):
            st.info("Twitter authentication coming soon!")
    
    # Toggle link
    toggle_text = "Don't have an account? Sign up" if st.session_state.auth_mode == 'login' else "Already have an account? Sign in"
    st.markdown(f'<div class="toggle-link">{toggle_text} <a onclick="toggleAuth()">{toggle_text.split("? ")[1]}</a></div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close auth-card
    st.markdown('</div>', unsafe_allow_html=True)  # Close auth-container
    
    # JavaScript for toggle
    st.markdown("""
    <script>
    function toggleAuth() {
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: 'toggle_auth'
        }, '*');
    }
    </script>
    """, unsafe_allow_html=True)

def handle_login(email, password, remember_me):
    """Handle login logic"""
    if not email or not password:
        st.error("Please enter both email and password")
        return
    
    st.session_state.auth_loading = True
    st.rerun()
    
    # Simulate API call
    import time
    time.sleep(1.5)
    
    # For demo purposes, accept any valid email format
    if "@" in email and len(password) >= 6:
        st.session_state.authenticated = True
        st.session_state.current_user = {
            "email": email,
            "name": email.split("@")[0].title(),
            "remember_me": remember_me
        }
        st.session_state.auth_loading = False
        st.success("Login successful!")
        st.rerun()
    else:
        st.session_state.auth_loading = False
        st.error("Invalid email or password. For demo: use any email and password >= 6 chars")

def handle_signup(email, password, name, remember_me):
    """Handle signup logic"""
    if not email or not password or not name:
        st.error("Please fill in all fields")
        return
    
    if len(password) < 6:
        st.error("Password must be at least 6 characters")
        return
    
    st.session_state.auth_loading = True
    st.rerun()
    
    # Simulate API call
    import time
    time.sleep(1.5)
    
    st.session_state.authenticated = True
    st.session_state.current_user = {
        "email": email,
        "name": name,
        "remember_me": remember_me
    }
    st.session_state.auth_loading = False
    st.success("Account created successfully!")
    st.rerun()

def render_logout_button():
    """Render logout button in sidebar"""
    with st.sidebar:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
            <div style="width: 40px; height: 40px; background: rgba(0, 255, 136, 0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #00ff88; font-size: 16px;">
                👤
            </div>
            <div>
                <p style="margin: 0; font-weight: 600; color: #fff;">{st.session_state.current_user['name']}</p>
                <p style="margin: 0; font-size: 12px; color: #999;">{st.session_state.current_user['email']}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ==================== EARTH ENGINE INITIALIZATION ====================

def auto_initialize_earth_engine():
    """Automatically initialize Earth Engine with service account credentials"""
    try:
        service_account_info = {
            "type": "service_account",
            "project_id": "citric-hawk-457513-i6",
            "private_key_id": "8984179a69969591194d8f8097e48cd9789f5ea2",
            "private_key": """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDFQOtXKWE+7mEY
JUTNzx3h+QvvDCvZ2B6XZTofknuAFPW2LqAzZustznJJFkCmO3Nutct+W/iDQCG0
1DjOQcbcr/jWr+mnRLVOkUkQc/kzZ8zaMQqU8HpXjS1mdhpsrbUaRKoEgfo3I3Bp
dFcJ/caC7TSr8VkGnZcPEZyXVsj8dLSEzomdkX+mDlJlgCrNfu3Knu+If5lXh3Me
SKiMWsfMnasiv46oD4szBzg6HLgoplmNka4NiwfeM7qROYnCd+5conyG8oiU00Xe
zC2Ekzo2dWsCw4zIJD6IdAcvgdrqH63fCqDFmAjEBZ69h8fWrdnsq56dAIpt0ygl
P9ADiRbVAgMBAAECggEALO7AnTqBGy2AgxhMP8iYEUdiu0mtvIIxV8HYl2QOC2ta
3GzrE8J0PJs8J99wix1cSmIRkH9hUP6dHvy/0uYjZ1aTi84HHtH1LghE2UFdySKy
RJqqwyozaDmx15b8Jnj8Wdc91miIR6KkQvVcNVuwalcf6jIAWlQwGp/jqIq9nloN
eld6xNbEmacORz1qT+4/uxOE05mrrZHC4kIKtswi8Io4ExVe61VxXsXWSHrMCGz0
TiSGr2ORSlRWC/XCGCu7zFIJU/iw6BiNsxryk6rjqQrcAtmoFTFx0fWbjYkG1DDs
k/9Dov1gyx0OtEyX8beoaf0Skcej4zdfeuido2A1sQKBgQD4IrhFn50i4/pa9sk1
g7v1ypGTrVA3pfvj6c7nTgzj9oyJnlU3WJwCqLw1cTFiY84+ekYP15wo8xsu5VZd
YLzOKEg3B8g899Ge14vZVNd6cNfRyMk4clGrDwGnZ4OAQkdsT/AyaCGRIcyu9njA
xdmWa+6VPMG7U65f/656XGwkBQKBgQDLgVyRE2+r1XCY+tdtXtga9sQ4LoiYHzD3
eDHe056qmwk8jf1A1HekILnC1GyeaKkOUd4TEWhVBgQpsvtC4Z2zPXlWR8N7SwNu
SFAhy3OnHTZQgrRWFA8eBjeI0YoXmk5m6uMQ7McmDlFxxXenFi+qSl3Cu4aGGuOy
cfyWMbTwkQKBgAoKfaJznww2ZX8g1WuQ9R4xIEr1jHV0BglnALRjeCoRZAZ9nb0r
nMSOx27yMallmIb2s7cYZn1RuRvgs+n7bCh7gNCZRAUTkiv3VPVqdX3C6zjWAy6B
kcR2Sv7XNX8PL4y2f2XKyPDyiTHbT2+dkfyASZtIZh6KeFfyJMFW1BlxAoGAAeG6
V2UUnUQl/GQlZc+AtA8gFVzoym9PZppn66WNTAqO9U5izxyn1o6u6QxJzNUu6wD6
yrZYfqDFnRUYma+4Y5Xn71JOjm9NItHsW8Oj2CG/BNOQk1MwKJjqHovBeSJmIzF8
1AU8ei+btS+cQaFE45A4ebp+LfNFs7q2GTVwdOECgYEAtHkMqigOmZdR3QAcZTjL
3aeOMGVHB2pHYosTgslD9Yp+hyVHqSdyCplHzWB3d8roIecW4MEb0mDxlaTdZfmR
dtBYiTzMxLezHsRZ4KP4NtGAE3iTL1b6DXuoI84+H/HaQ1EB79+YV9ZTAabt1b7o
e5aU1RW6tlG8nzHHwK2FeyI=
-----END PRIVATE KEY-----""",
            "client_email": "cc-365@citric-hawk-457513-i6.iam.gserviceaccount.com",
            "client_id": "105264622264803277310",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/cc-365%40citric-hawk-457513-i6.iam.gserviceaccount.com",
            "universe_domain": "googleapis.com"
        }
        
        credentials = ee.ServiceAccountCredentials(
            service_account_info['client_email'],
            key_data=json.dumps(service_account_info)
        )
        
        ee.Initialize(credentials, project='citric-hawk-457513-i6')
        return True
    except Exception as e:
        st.error(f"Earth Engine auto-initialization failed: {str(e)}")
        return False

# ==================== HELPER FUNCTIONS FOR EARTH ENGINE ====================

def get_admin_boundaries(level, country_code=None, admin1_code=None):
    """Get administrative boundaries from Earth Engine"""
    try:
        if level == 0:
            return ee.FeatureCollection("FAO/GAUL/2015/level0")
        elif level == 1:
            admin1 = ee.FeatureCollection("FAO/GAUL/2015/level1")
            if country_code:
                return admin1.filter(ee.Filter.eq('ADM0_CODE', country_code))
            return admin1
        elif level == 2:
            admin2 = ee.FeatureCollection("FAO/GAUL/2015/level2")
            if admin1_code:
                return admin2.filter(ee.Filter.eq('ADM1_CODE', admin1_code))
            elif country_code:
                return admin2.filter(ee.Filter.eq('ADM0_CODE', country_code))
            return admin2
    except Exception as e:
        st.error(f"Error loading boundaries: {str(e)}")
        return None

def get_boundary_names(feature_collection, level):
    """Extract boundary names from Earth Engine FeatureCollection"""
    try:
        if level == 0:
            names = feature_collection.aggregate_array('ADM0_NAME').distinct()
        elif level == 1:
            names = feature_collection.aggregate_array('ADM1_NAME').distinct()
        elif level == 2:
            names = feature_collection.aggregate_array('ADM2_NAME').distinct()
        else:
            return []
        
        names_list = names.getInfo()
        if names_list:
            return sorted(names_list)
        return []
        
    except Exception as e:
        st.error(f"Error extracting names: {str(e)}")
        return []

def get_geometry_coordinates(geometry):
    """Get center coordinates and bounds from geometry"""
    try:
        bounds = geometry.geometry().bounds().getInfo()
        coords = bounds['coordinates'][0]
        lats = [coord[1] for coord in coords]
        lons = [coord[0] for coord in coords]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        min_lat = min(lats)
        max_lat = max(lats)
        min_lon = min(lons)
        max_lon = max(lons)
        
        return {
            'center': [center_lon, center_lat],
            'bounds': [[min_lat, min_lon], [max_lat, max_lon]],
            'zoom': 6
        }
    except Exception as e:
        st.error(f"Error getting coordinates: {str(e)}")
        return {'center': [0, 20], 'bounds': None, 'zoom': 2}

# ==================== MAIN APPLICATION LOGIC ====================

# Initialize session state
initialize_session_state()

# Initialize Earth Engine on app start
if 'ee_auto_initialized' not in st.session_state:
    with st.spinner("Initializing Earth Engine..."):
        if auto_initialize_earth_engine():
            st.session_state.ee_auto_initialized = True
            st.session_state.ee_initialized = True
        else:
            st.session_state.ee_auto_initialized = False
            st.session_state.ee_initialized = False

# Initialize other session state
if 'ee_initialized' not in st.session_state:
    st.session_state.ee_initialized = False
if 'selected_geometry' not in st.session_state:
    st.session_state.selected_geometry = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'selected_coordinates' not in st.session_state:
    st.session_state.selected_coordinates = None
if 'selected_area_name' not in st.session_state:
    st.session_state.selected_area_name = None

# ==================== ROUTING LOGIC ====================

# Show authentication page if not authenticated
if not st.session_state.authenticated:
    render_auth_page()
    st.stop()

# ==================== MAIN DASHBOARD (After Authentication) ====================

# Main Dashboard Layout
st.markdown(f"""
<div class="compact-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <div>
        <h1>🌍 KHISBA GIS</h1>
        <p style="color: #999999; margin: 0; font-size: 14px;">Interactive 3D Global Vegetation Analytics</p>
    </div>
    <div style="display: flex; gap: 10px; align-items: center;">
        <div class="user-badge">
            <div style="width: 24px; height: 24px; background: rgba(0, 255, 136, 0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #00ff88; font-size: 12px;">
                👤
            </div>
            <span>{st.session_state.current_user['name']}</span>
        </div>
        <span class="status-badge">Connected</span>
        <span class="status-badge">3D Mapbox Globe</span>
        <span class="status-badge">v2.0</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Logout button in sidebar
render_logout_button()

# ==================== MAIN LAYOUT ====================

col1, col2 = st.columns([0.25, 0.75], gap="large")

# LEFT SIDEBAR - All controls
with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title"><div class="icon">🌍</div><h3 style="margin: 0;">Area Selection</h3></div>', unsafe_allow_html=True)
    
    if st.session_state.ee_initialized:
        try:
            countries_fc = get_admin_boundaries(0)
            if countries_fc:
                country_names = get_boundary_names(countries_fc, 0)
                selected_country = st.selectbox(
                    "Country",
                    options=["Select a country"] + country_names,
                    index=0,
                    help="Choose a country for analysis",
                    key="country_select"
                )
                
                if selected_country and selected_country != "Select a country":
                    country_feature = countries_fc.filter(ee.Filter.eq('ADM0_NAME', selected_country)).first()
                    
                    admin1_fc = get_admin_boundaries(1, country_feature.get('ADM0_CODE').getInfo())
                    if admin1_fc:
                        admin1_names = get_boundary_names(admin1_fc, 1)
                        selected_admin1 = st.selectbox(
                            "State/Province",
                            options=["Select state/province"] + admin1_names,
                            index=0,
                            help="Choose a state or province",
                            key="admin1_select"
                        )
                        
                        if selected_admin1 and selected_admin1 != "Select state/province":
                            admin1_feature = admin1_fc.filter(ee.Filter.eq('ADM1_NAME', selected_admin1)).first()
                            
                            admin2_fc = get_admin_boundaries(2, None, admin1_feature.get('ADM1_CODE').getInfo())
                            if admin2_fc:
                                admin2_names = get_boundary_names(admin2_fc, 2)
                                selected_admin2 = st.selectbox(
                                    "Municipality",
                                    options=["Select municipality"] + admin2_names,
                                    index=0,
                                    help="Choose a municipality",
                                    key="admin2_select"
                                )
                            else:
                                selected_admin2 = None
                        else:
                            selected_admin2 = None
                    else:
                        selected_admin1 = None
                        selected_admin2 = None
                else:
                    selected_admin1 = None
                    selected_admin2 = None
            else:
                st.error("Failed to load countries. Please check Earth Engine connection.")
                selected_country = None
                selected_admin1 = None
                selected_admin2 = None
                
        except Exception as e:
            st.error(f"Error loading boundaries: {str(e)}")
            selected_country = None
            selected_admin1 = None
            selected_admin2 = None
    else:
        st.warning("Earth Engine not initialized")
        selected_country = None
        selected_admin1 = None
        selected_admin2 = None
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Update selected geometry when area is selected
    if selected_country and selected_country != "Select a country":
        try:
            if selected_admin2 and selected_admin2 != "Select municipality":
                geometry = admin2_fc.filter(ee.Filter.eq('ADM2_NAME', selected_admin2))
                area_name = f"{selected_admin2}, {selected_admin1}, {selected_country}"
                area_level = "Municipality"
            elif selected_admin1 and selected_admin1 != "Select state/province":
                geometry = admin1_fc.filter(ee.Filter.eq('ADM1_NAME', selected_admin1))
                area_name = f"{selected_admin1}, {selected_country}"
                area_level = "State/Province"
            else:
                geometry = countries_fc.filter(ee.Filter.eq('ADM0_NAME', selected_country))
                area_name = selected_country
                area_level = "Country"
            
            coords_info = get_geometry_coordinates(geometry)
            
            st.session_state.selected_geometry = geometry
            st.session_state.selected_coordinates = coords_info
            st.session_state.selected_area_name = area_name
            st.session_state.selected_area_level = area_level
            
        except Exception as e:
            st.error(f"Error processing geometry: {str(e)}")
    
    # Analysis Parameters Card
    if selected_country and selected_country != "Select a country":
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title"><div class="icon">⚙️</div><h3 style="margin: 0;">Analysis Settings</h3></div>', unsafe_allow_html=True)
        
        col_a, col_b = st.columns(2)
        with col_a:
            start_date = st.date_input(
                "Start Date",
                value=datetime(2023, 1, 1),
                help="Start date for analysis",
                key="start_date"
            )
        with col_b:
            end_date = st.date_input(
                "End Date",
                value=datetime(2023, 12, 31),
                help="End date for analysis",
                key="end_date"
            )
        
        collection_choice = st.selectbox(
            "Satellite Collection",
            options=["Sentinel-2", "Landsat 8", "MODIS"],
            index=0,
            help="Choose satellite data source",
            key="collection_select"
        )
        
        index_options = st.multiselect(
            "Vegetation Indices",
            options=["NDVI", "EVI", "SAVI", "NDWI", "LAI"],
            default=["NDVI"],
            help="Select vegetation indices to calculate",
            key="index_select"
        )
        
        if st.button("🚀 Run Analysis", type="primary", use_container_width=True, key="run_analysis"):
            st.info("Analysis feature - select indices and run vegetation analysis on the selected area.")
        
        st.markdown('</div>', unsafe_allow_html=True)

# RIGHT CONTENT - Map and Results
with col2:
    # Selected Area Info
    if st.session_state.selected_area_name:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">
                <div class="icon">📍</div>
                <h3 style="margin: 0;">Selected Area</h3>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <p style="margin: 0; font-size: 18px; font-weight: 600; color: #00ff88;">{st.session_state.selected_area_name}</p>
                    <p style="margin: 5px 0 0 0; color: #999999; font-size: 14px;">{st.session_state.get('selected_area_level', 'Region')}</p>
                </div>
                <span class="status-badge">Selected</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # 3D Globe Map
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title"><div class="icon">🗺️</div><h3 style="margin: 0;">3D Interactive Globe</h3></div>', unsafe_allow_html=True)
    
    # Get map parameters
    if st.session_state.selected_coordinates:
        map_center = st.session_state.selected_coordinates['center']
        map_zoom = st.session_state.selected_coordinates['zoom']
        bounds_data = st.session_state.selected_coordinates.get('bounds')
    else:
        map_center = [0, 20]
        map_zoom = 2
        bounds_data = None
    
    # Mapbox Token (public token for demo)
    mapbox_token = "pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4M29iazA2Z2gycXA4N2pmbDZmangifQ.-g_vE53SD2WrJ6tFX7QHmA"
    
    # Create 3D Mapbox Globe HTML
    mapbox_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <script src="https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.js"></script>
      <link href="https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.css" rel="stylesheet">
      <style>
        body {{ margin: 0; padding: 0; }}
        #map {{ width: 100%; height: 530px; }}
        .coordinates-display {{
          position: absolute;
          bottom: 10px;
          left: 10px;
          background: rgba(0,0,0,0.7);
          color: #00ff88;
          padding: 8px 12px;
          border-radius: 6px;
          font-size: 12px;
          font-family: monospace;
          z-index: 1000;
        }}
        .mapboxgl-popup-content {{
          background: #0a0a0a;
          color: #ffffff;
          border: 1px solid #222222;
          border-radius: 8px;
          padding: 15px;
        }}
        .mapboxgl-popup-content h3 {{
          color: #00ff88;
          margin: 0 0 10px 0;
          font-size: 16px;
        }}
        .mapboxgl-popup-content p {{
          margin: 0;
          color: #cccccc;
          font-size: 14px;
        }}
        .mapboxgl-popup-close-button {{
          color: #ffffff;
          font-size: 20px;
        }}
      </style>
    </head>
    <body>
      <div id="map"></div>
      <div class="coordinates-display">
        <span>Lat: <span id="lat-display">0.00</span></span> | 
        <span>Lon: <span id="lon-display">0.00</span></span>
      </div>
      <script>
        mapboxgl.accessToken = '{mapbox_token}';
        
        const map = new mapboxgl.Map({{
          container: 'map',
          style: 'mapbox://styles/mapbox/satellite-streets-v12',
          center: {map_center},
          zoom: {map_zoom},
          projection: 'globe',
          antialias: true
        }});
        
        map.addControl(new mapboxgl.NavigationControl());
        map.addControl(new mapboxgl.FullscreenControl());
        
        map.on('style.load', () => {{
          map.setFog({{
            'color': 'rgb(10, 10, 10)',
            'high-color': 'rgb(20, 20, 30)',
            'horizon-blend': 0.1,
            'space-color': 'rgb(5, 5, 10)',
            'star-intensity': 0.8
          }});
        }});
        
        map.on('load', () => {{
          map.on('mousemove', (e) => {{
            document.getElementById('lat-display').textContent = e.lngLat.lat.toFixed(2) + '°';
            document.getElementById('lon-display').textContent = e.lngLat.lng.toFixed(2) + '°';
          }});
          
          {f'''
          if ({bounds_data}) {{
            const bounds = {bounds_data};
            
            map.addSource('selected-area', {{
              'type': 'geojson',
              'data': {{
                'type': 'Feature',
                'geometry': {{
                  'type': 'Polygon',
                  'coordinates': [[
                    [bounds[0][1], bounds[0][0]],
                    [bounds[1][1], bounds[0][0]],
                    [bounds[1][1], bounds[1][0]],
                    [bounds[0][1], bounds[1][0]],
                    [bounds[0][1], bounds[0][0]]
                  ]]
                }}
              }}
            }};

            map.addLayer({{
              'id': 'selected-area-fill',
              'type': 'fill',
              'source': 'selected-area',
              'layout': {{}},
              'paint': {{
                'fill-color': '#00ff88',
                'fill-opacity': 0.2
              }}
            }};

            map.addLayer({{
              'id': 'selected-area-border',
              'type': 'line',
              'source': 'selected-area',
              'layout': {{}},
              'paint': {{
                'line-color': '#00ff88',
                'line-width': 3,
                'line-opacity': 0.8
              }}
            }};

            map.flyTo({{
              center: {map_center},
              zoom: {map_zoom},
              duration: 2000,
              essential: true
            }});
          }}
          ''' if bounds_data else ''}
        }});
      </script>
    </body>
    </html>
    """
    
    st.components.v1.html(mapbox_html, height=550)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Analysis Results Section
    if st.session_state.analysis_results:
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="compact-header"><h3>Analysis Results</h3><span class="status-badge">Complete</span></div>', unsafe_allow_html=True)
        
        results = st.session_state.analysis_results
        
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title"><div class="icon">📊</div><h3 style="margin: 0;">Summary Statistics</h3></div>', unsafe_allow_html=True)
        
        summary_data = []
        for index, data in results.items():
            if data['values']:
                values = [v for v in data['values'] if v is not None]
                if values:
                    summary_data.append({
                        'Index': index,
                        'Mean': round(sum(values) / len(values), 4),
                        'Min': round(min(values), 4),
                        'Max': round(max(values), 4),
                        'Count': len(values)
                    })
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="section-divider"></div>
<div style="text-align: center; color: #666666; font-size: 12px; padding: 20px 0;">
    <p style="margin: 5px 0;">KHISBA GIS - Interactive 3D Global Vegetation Analytics Platform</p>
    <p style="margin: 5px 0;">Created by Taibi Farouk Djilali - Clean Green & Black Design</p>
    <div style="display: flex; justify-content: center; gap: 10px; margin-top: 10px;">
        <span class="status-badge">3D Mapbox</span>
        <span class="status-badge">Earth Engine</span>
        <span class="status-badge">Streamlit</span>
        <span class="status-badge">User Auth</span>
    </div>
</div> 
""", unsafe_allow_html=True)
