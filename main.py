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
from google.oauth2.credentials import Credentials
import base64
import requests

# Page configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="Khisba GIS - 3D Global Vegetation Analysis",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== CUSTOM CSS ====================
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
    
    /* Login container */
    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 40px 30px;
        background: var(--card-black);
        border: 1px solid var(--border-gray);
        border-radius: 15px;
        text-align: center;
    }
    
    .login-icon {
        font-size: 3rem;
        color: var(--primary-green);
        margin-bottom: 20px;
    }
    
    .login-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        background: #4285F4;
        color: white !important;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: 600;
        text-decoration: none;
        border: none;
        cursor: pointer;
        transition: all 0.3s ease;
        margin-top: 20px;
    }
    
    .login-btn:hover {
        background: #3367D6;
        transform: translateY(-2px);
    }
    
    .login-btn img {
        width: 20px;
        height: 20px;
    }
    
    /* Google icon container */
    .google-icon-container {
        background: white;
        padding: 8px;
        border-radius: 4px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
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
    
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Small auth container */
    .auth-container {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1000;
    }
    
    .user-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        border: 2px solid var(--primary-green);
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)

# ==================== INLINE GOOGLE AUTH ====================

def get_google_auth_url(client_config):
    """Generate Google OAuth URL for inline authentication"""
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        client_config,
        scopes=[
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'openid'
        ],
        redirect_uri='http://localhost:8501'  # Streamlit default
    )
    
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    return auth_url, state

def get_google_user_info(access_token):
    """Get user info from Google API"""
    try:
        response = requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error fetching user info: {e}")
    return None

# Load Google config
def load_google_config():
    try:
        # Try to load from Streamlit secrets
        if "GOOGLE_CLIENT_ID" in st.secrets and "GOOGLE_CLIENT_SECRET" in st.secrets:
            return {
                "web": {
                    "client_id": st.secrets["GOOGLE_CLIENT_ID"],
                    "client_secret": st.secrets["GOOGLE_CLIENT_SECRET"],
                    "redirect_uris": ["http://localhost:8501"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            }
        
        # Try to load from file
        if os.path.exists("client_secret.json"):
            with open("client_secret.json", "r") as f:
                return json.load(f)
        
        return None
    except Exception as e:
        st.error(f"Error loading Google config: {e}")
        return None

# Initialize session state
if "google_auth_url" not in st.session_state:
    st.session_state.google_auth_url = None
if "google_auth_state" not in st.session_state:
    st.session_state.google_auth_state = None
if "google_user_info" not in st.session_state:
    st.session_state.google_user_info = None
if "access_token" not in st.session_state:
    st.session_state.access_token = None

# Load Google config
google_config = load_google_config()

# Handle OAuth callback from URL parameters
query_params = st.query_params
if "code" in query_params and "state" in query_params:
    if not st.session_state.google_user_info:
        try:
            # Exchange authorization code for tokens
            flow = google_auth_oauthlib.flow.Flow.from_client_config(
                google_config,
                scopes=[
                    'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/userinfo.profile',
                    'openid'
                ],
                state=query_params["state"]
            )
            flow.redirect_uri = 'http://localhost:8501'
            
            flow.fetch_token(code=query_params["code"])
            credentials = flow.credentials
            
            # Get user info
            st.session_state.access_token = credentials.token
            user_info = get_google_user_info(credentials.token)
            
            if user_info:
                st.session_state.google_user_info = user_info
                # Clear URL parameters
                st.query_params.clear()
                st.rerun()
                
        except Exception as e:
            st.error(f"Authentication error: {e}")

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

# Initialize Earth Engine
if 'ee_auto_initialized' not in st.session_state:
    with st.spinner("Initializing Earth Engine..."):
        if auto_initialize_earth_engine():
            st.session_state.ee_auto_initialized = True
            st.session_state.ee_initialized = True
        else:
            st.session_state.ee_auto_initialized = False
            st.session_state.ee_initialized = False

# Initialize session states
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

# ==================== AUTHENTICATION CHECK ====================

# Show login page if not authenticated
if not st.session_state.google_user_info:
    # Generate auth URL if not already generated
    if google_config and not st.session_state.google_auth_url:
        try:
            auth_url, state = get_google_auth_url(google_config)
            st.session_state.google_auth_url = auth_url
            st.session_state.google_auth_state = state
        except Exception as e:
            st.error(f"Failed to generate auth URL: {e}")
    
    # Show login interface
    st.markdown("""
    <div style="height: 100vh; display: flex; align-items: center; justify-content: center;">
        <div class="login-container">
            <div class="login-icon">🌍</div>
            <h1 style="text-align: center;">KHISBA GIS</h1>
            <p style="color: #999999; margin-bottom: 30px; text-align: center;">3D Global Vegetation Analytics</p>
            
            <div style="padding: 20px; border-radius: 10px; background: rgba(0, 255, 136, 0.05); border: 1px solid rgba(0, 255, 136, 0.2);">
                <p style="color: #00ff88; font-weight: 600; margin-bottom: 15px;">Sign in to access the platform</p>
            </div>
            
            <div style="margin-top: 30px;">
    """, unsafe_allow_html=True)
    
    # Google Sign In Button
    if st.session_state.google_auth_url:
        # Create a form that redirects to the auth URL
        st.markdown(f"""
        <form action="{st.session_state.google_auth_url}" method="get">
            <button type="submit" class="login-btn" style="width: 100%;">
                <div class="google-icon-container">
                    <svg width="18" height="18" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
                        <path fill="#4285F4" d="M45.12 24.5c0-1.56-.14-3.06-.4-4.5H24v8.51h11.84c-.51 2.75-2.06 5.08-4.39 6.64v5.52h7.11c4.16-3.83 6.56-9.47 6.56-16.17z"/>
                        <path fill="#34A853" d="M24 46c5.94 0 10.92-1.97 14.56-5.33l-7.11-5.52c-1.97 1.32-4.49 2.1-7.45 2.1-5.73 0-10.58-3.87-12.31-9.07H4.34v5.7C7.96 41.07 15.4 46 24 46z"/>
                        <path fill="#FBBC05" d="M11.69 28.18C11.25 26.86 11 25.45 11 24s.25-2.86.69-4.18v-5.7H4.34C2.85 17.09 2 20.45 2 24c0 3.55.85 6.91 2.34 9.88l7.35-5.7z"/>
                        <path fill="#EA4335" d="M24 10.75c3.24 0 6.13 1.11 8.41 3.29l6.31-6.31C34.91 4.18 29.93 2 24 2 15.4 2 7.96 6.93 4.34 14.12l7.35 5.7c1.73-5.2 6.58-9.07 12.31-9.07z"/>
                    </svg>
                </div>
                <span>Continue with Google</span>
            </button>
        </form>
        """, unsafe_allow_html=True)
    else:
        st.error("Google authentication not configured")
    
    st.markdown("""
            </div>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #222;">
                <p style="color: #666; font-size: 12px; text-align: center;">
                    After clicking, you'll be redirected back to this page automatically
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.stop()

# ==================== MAIN APPLICATION (After Authentication) ====================

# Get user info
user_info = st.session_state.google_user_info

# Small user info in top right
st.markdown(f"""
<div class="auth-container">
    <div style="display: flex; align-items: center; gap: 10px; background: rgba(0,0,0,0.8); padding: 8px 15px; border-radius: 25px; border: 1px solid #222;">
        <img src="{user_info.get('picture', '')}" class="user-avatar" onclick="document.getElementById('logout-modal').style.display='block'">
        <div style="font-size: 12px;">
            <div style="font-weight: 600;">{user_info.get('name', 'User')}</div>
            <div style="color: #999; font-size: 10px;">{user_info.get('email', '')}</div>
        </div>
        <span class="status-badge" style="margin-left: 10px; font-size: 10px;">✓</span>
    </div>
</div>

<div id="logout-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 2000; align-items: center; justify-content: center;">
    <div style="background: #0a0a0a; border: 1px solid #222; border-radius: 10px; padding: 30px; width: 300px; text-align: center;">
        <h3 style="color: #00ff88; margin-bottom: 20px;">Logout?</h3>
        <p style="color: #999; margin-bottom: 30px;">Are you sure you want to sign out?</p>
        <div style="display: flex; gap: 10px;">
            <button onclick="document.getElementById('logout-modal').style.display='none'" style="flex: 1; background: #222; color: white; border: none; padding: 10px; border-radius: 5px; cursor: pointer;">Cancel</button>
            <button onclick="window.location.href='?logout=true'" style="flex: 1; background: #00ff88; color: black; border: none; padding: 10px; border-radius: 5px; font-weight: 600; cursor: pointer;">Logout</button>
        </div>
    </div>
</div>

<script>
// Close modal when clicking outside
document.getElementById('logout-modal').addEventListener('click', function(e) {{
    if (e.target.id === 'logout-modal') {{
        document.getElementById('logout-modal').style.display = 'none';
    }}
}});
</script>
""", unsafe_allow_html=True)

# Handle logout
if "logout" in st.query_params:
    st.session_state.google_user_info = None
    st.session_state.google_auth_url = None
    st.session_state.access_token = None
    st.query_params.clear()
    st.rerun()

# Main Dashboard
st.markdown(f"""
<div class="compact-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; margin-top: 20px;">
    <div>
        <h1>🌍 KHISBA GIS</h1>
        <p style="color: #999999; margin: 0; font-size: 14px;">Interactive 3D Global Vegetation Analytics</p>
    </div>
    <div style="display: flex; gap: 10px; align-items: center;">
        <span class="status-badge">Connected</span>
        <span class="status-badge">3D Mapbox Globe</span>
        <span class="status-badge">v2.0</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==================== HELPER FUNCTIONS ====================
# ... [Keep all your existing helper functions here] ...

# ==================== MAIN LAYOUT ====================
# ... [Keep all your existing main layout code here] ...

# Footer
st.markdown("""
<div style="text-align: center; color: #666666; font-size: 12px; padding: 20px 0; margin-top: 50px;">
    <p style="margin: 5px 0;">KHISBA GIS - Interactive 3D Global Vegetation Analytics Platform</p>
    <p style="margin: 5px 0;">Created by Taibi Farouk Djilali - Clean Green & Black Design</p>
    <div style="display: flex; justify-content: center; gap: 10px; margin-top: 10px;">
        <span class="status-badge">3D Mapbox</span>
        <span class="status-badge">Earth Engine</span>
        <span class="status-badge">Streamlit</span>
        <span class="status-badge">Inline Google Auth</span>
    </div>
</div>
""", unsafe_allow_html=True)
