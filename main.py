import streamlit as st
import json
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
import requests
from urllib.parse import urlencode
import base64

# Page configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="Khisba GIS - 3D Global Vegetation Analysis",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== GOOGLE OAUTH CONFIGURATION ====================

# Load Google OAuth secrets
def load_google_config():
    try:
        if "web" in st.secrets:
            client_config = dict(st.secrets["web"])
        elif os.path.exists("client_secret.json"):
            with open("client_secret.json", "r") as f:
                client_config = json.load(f)["web"]
        else:
            # Demo credentials (replace with your own)
            client_config = {
                "client_id": st.secrets.get("GOOGLE_CLIENT_ID", "your-client-id.apps.googleusercontent.com"),
                "client_secret": st.secrets.get("GOOGLE_CLIENT_SECRET", "your-client-secret"),
                "redirect_uris": [st.secrets.get("GOOGLE_REDIRECT_URI", "http://localhost:8501")],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        return client_config
    except Exception:
        return None

GOOGLE_SCOPES = "openid email profile"

# Initialize session state for Google auth
if "google_user_info" not in st.session_state:
    st.session_state.google_user_info = None
if "google_auth_code" not in st.session_state:
    st.session_state.google_auth_code = None
if "google_access_token" not in st.session_state:
    st.session_state.google_access_token = None

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
    
    h2 {
        font-size: 1.5rem !important;
        color: var(--primary-green) !important;
    }
    
    h3 {
        font-size: 1.25rem !important;
        margin-bottom: 1rem !important;
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
    
    /* Login Card Specific */
    .login-card {
        max-width: 400px;
        margin: 100px auto;
        text-align: center;
    }
    
    .login-button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        background: white;
        color: #757575;
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 12px 24px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s ease;
        text-decoration: none;
        margin: 20px 0;
    }
    
    .login-button:hover {
        background: #f8f8f8;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .login-button img {
        width: 18px;
        height: 18px;
    }
    
    /* Input fields */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stDateInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: var(--secondary-black) !important;
        border: 1px solid var(--border-gray) !important;
        color: var(--text-white) !important;
        border-radius: 6px !important;
        padding: 10px 12px !important;
        font-size: 14px !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stDateInput > div > div > input:focus {
        border-color: var(--primary-green) !important;
        box-shadow: 0 0 0 2px rgba(0, 255, 136, 0.2) !important;
    }
    
    /* Map container */
    .map-container {
        border: 1px solid var(--border-gray);
        border-radius: 10px;
        overflow: hidden;
        height: 600px;
    }
    
    /* 3D Globe container */
    .globe-container {
        border: 1px solid var(--border-gray);
        border-radius: 10px;
        overflow: hidden;
        height: 600px;
        background: #000;
        position: relative;
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
    
    /* Compact Login Form */
    .compact-login {
        background: var(--card-black);
        border: 1px solid var(--border-gray);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    }
    
    .compact-login h4 {
        color: var(--primary-green);
        margin-bottom: 15px;
    }
    
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==================== GOOGLE AUTH FUNCTIONS ====================

def get_google_auth_url():
    """Generate Google OAuth URL for embedded login"""
    client_config = load_google_config()
    if not client_config:
        return None
    
    params = {
        "client_id": client_config["client_id"],
        "redirect_uri": client_config["redirect_uris"][0],
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": "streamlit_gis_app"  # Add state for security
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
    return auth_url

def exchange_code_for_token(code):
    """Exchange authorization code for access token"""
    client_config = load_google_config()
    if not client_config:
        return None
    
    token_url = "https://oauth2.googleapis.com/token"
    
    data = {
        "code": code,
        "client_id": client_config["client_id"],
        "client_secret": client_config["client_secret"],
        "redirect_uri": client_config["redirect_uris"][0],
        "grant_type": "authorization_code"
    }
    
    try:
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            token_data = response.json()
            st.session_state.google_access_token = token_data.get("access_token")
            return token_data.get("access_token")
    except Exception as e:
        st.error(f"Token exchange failed: {e}")
    
    return None

def get_user_info(access_token):
    """Get user info using access token"""
    if not access_token:
        return None
    
    user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(user_info_url, headers=headers)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Failed to get user info: {e}")
    
    return None

def handle_google_auth_callback():
    """Handle Google OAuth callback"""
    query_params = st.query_params
    
    if "code" in query_params:
        code = query_params["code"]
        st.session_state.google_auth_code = code
        
        # Exchange code for token
        access_token = exchange_code_for_token(code)
        if access_token:
            # Get user info
            user_info = get_user_info(access_token)
            if user_info:
                st.session_state.google_user_info = user_info
                st.session_state.google_access_token = access_token
                # Clear the code from URL
                st.query_params.clear()
                st.rerun()
        else:
            st.error("Failed to authenticate with Google")

# Handle OAuth callback
handle_google_auth_callback()

# ==================== EARTH ENGINE INITIALIZATION ====================

def auto_initialize_earth_engine():
    """Automatically initialize Earth Engine with service account credentials"""
    try:
        # You can use your existing service account credentials here
        # For security, consider using st.secrets or environment variables
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

# ==================== LOGIN PAGE ====================

if not st.session_state.google_user_info:
    # Show compact login form
    st.markdown("""
    <div class="main-container">
        <div class="content-container" style="max-width: 500px; margin: 50px auto;">
            <div class="card login-card">
                <h1 style="text-align: center; margin-bottom: 10px;">🌍 KHISBA GIS</h1>
                <p style="text-align: center; color: #999999; margin-bottom: 30px;">3D Global Vegetation Analytics</p>
                
                <div style="text-align: center; padding: 10px;">
                    <p style="color: #00ff88; font-weight: 600; margin-bottom: 20px;">Sign in to access the platform</p>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Create columns for centering
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="compact-login">', unsafe_allow_html=True)
        st.markdown('<h4 style="text-align: center;">Google Authentication</h4>', unsafe_allow_html=True)
        
        # Get Google auth URL
        auth_url = get_google_auth_url()
        
        if auth_url:
            # Create HTML button that opens in current window
            google_button_html = f"""
            <div style="text-align: center;">
                <a href="{auth_url}" target="_self" style="text-decoration: none;">
                    <div class="login-button">
                        <img src="https://www.google.com/favicon.ico" alt="Google">
                        Sign in with Google
                    </div>
                </a>
                <p style="color: #666666; font-size: 12px; margin-top: 10px;">
                    You'll be redirected to Google for authentication
                </p>
            </div>
            """
            st.markdown(google_button_html, unsafe_allow_html=True)
        else:
            st.error("Google OAuth configuration not found. Please check your secrets.")
            
            # Alternative: Simple username/password demo
            st.markdown('<div style="margin-top: 20px;">', unsafe_allow_html=True)
            st.markdown('<h4 style="color: #00ff88; margin-bottom: 15px;">Demo Login</h4>', unsafe_allow_html=True)
            
            demo_username = st.text_input("Username", placeholder="Enter demo username")
            demo_password = st.text_input("Password", type="password", placeholder="Enter demo password")
            
            if st.button("Demo Login", type="primary", use_container_width=True):
                if demo_username and demo_password:
                    # Simple demo authentication
                    st.session_state.google_user_info = {
                        "name": "Demo User",
                        "email": "demo@example.com",
                        "picture": "https://api.dicebear.com/7.x/avataaars/svg?seed=khisba"
                    }
                    st.rerun()
                else:
                    st.warning("Please enter username and password")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.stop()

# ==================== MAIN APPLICATION (After Authentication) ====================

# Get user info for display
user_info = st.session_state.google_user_info

# Main Dashboard Layout
st.markdown(f"""
<div class="compact-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <div>
        <h1>🌍 KHISBA GIS</h1>
        <p style="color: #999999; margin: 0; font-size: 14px;">Interactive 3D Global Vegetation Analytics</p>
    </div>
    <div style="display: flex; gap: 10px; align-items: center;">
        <div class="user-badge">
            <img src="{user_info.get('picture', 'https://api.dicebear.com/7.x/avataaars/svg?seed=khisba')}" alt="Profile">
            <span>{user_info.get('name', 'User')}</span>
        </div>
        <span class="status-badge">Connected</span>
        <span class="status-badge">3D Mapbox Globe</span>
        <span class="status-badge">v2.0</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Logout button in sidebar
with st.sidebar:
    st.markdown(f"""
    <div class="card">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
            <img src="{user_info.get('picture', 'https://api.dicebear.com/7.x/avataaars/svg?seed=khisba')}" style="width: 40px; height: 40px; border-radius: 50%;">
            <div>
                <p style="margin: 0; font-weight: 600; color: #fff;">{user_info.get('name', 'User')}</p>
                <p style="margin: 0; font-size: 12px; color: #999;">{user_info.get('email', '')}</p>
            </div>
        </div>
        <div style="text-align: center;">
            <button onclick="logout()" style="background: #ff4444; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; width: 100%; font-weight: 600;">
                🚪 Logout
            </button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # JavaScript for logout
    st.markdown("""
    <script>
    function logout() {
        // Clear session state via query params
        window.location.search = "?logout=true";
    }
    </script>
    """, unsafe_allow_html=True)
    
    # Handle logout
    if st.query_params.get("logout") == "true":
        st.session_state.google_user_info = None
        st.session_state.google_access_token = None
        st.session_state.google_auth_code = None
        st.query_params.clear()
        st.rerun()

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
            }});

            map.addLayer({{
              'id': 'selected-area-fill',
              'type': 'fill',
              'source': 'selected-area',
              'layout': {{}},
              'paint': {{
                'fill-color': '#00ff88',
                'fill-opacity': 0.2
              }}
            }});

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
            }});

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
        <span class="status-badge">Google Auth</span>
    </div>
</div>
""", unsafe_allow_html=True)
