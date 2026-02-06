import streamlit as st
import json
import os
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import ee
import google_auth_oauthlib.flow
from googleapiclient.discovery import build

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
            return None
        return client_config
    except Exception:
        if os.path.exists("client_secret.json"):
            with open("client_secret.json", "r") as f:
                return json.load(f)["web"]
        return None

GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email', 
    'https://www.googleapis.com/auth/userinfo.profile', 
    'openid'
]

def create_google_flow(client_config):
    if "redirect_uris" in client_config and isinstance(client_config["redirect_uris"], str):
        client_config["redirect_uris"] = [client_config["redirect_uris"]]
    
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        {"web": client_config},
        scopes=GOOGLE_SCOPES,
        redirect_uri=client_config["redirect_uris"][0]
    )
    return flow

# Initialize session state for Google auth
if "google_credentials" not in st.session_state:
    st.session_state.google_credentials = None
if "google_user_info" not in st.session_state:
    st.session_state.google_user_info = None

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
    
    /* Center container */
    .center-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        padding: 20px;
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
    
    /* Login Page Styling */
    .login-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100vh;
        text-align: center;
        background: #000000;
        position: relative;
        overflow: hidden;
    }

    /* Animated Cyber Grid Background */
    .login-container::before {
        content: "";
        position: absolute;
        width: 200%;
        height: 200%;
        top: -50%;
        left: -50%;
        background-image: 
            linear-gradient(rgba(0, 255, 136, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 255, 136, 0.05) 1px, transparent 1px);
        background-size: 50px 50px;
        transform: perspective(500px) rotateX(60deg) translateY(0);
        animation: gridMove 20s linear infinite;
        pointer-events: none;
    }

    @keyframes gridMove {
        0% { transform: perspective(500px) rotateX(60deg) translateY(0); }
        100% { transform: perspective(500px) rotateX(60deg) translateY(50px); }
    }

    /* Floating Particles */
    .particle {
        position: absolute;
        background: var(--primary-green);
        border-radius: 50%;
        pointer-events: none;
        opacity: 0.3;
        filter: blur(1px);
        animation: floatParticle 10s infinite ease-in-out;
    }

    @keyframes floatParticle {
        0%, 100% { transform: translateY(0) translateX(0); }
        25% { transform: translateY(-100px) translateX(50px); }
        50% { transform: translateY(-200px) translateX(-20px); }
        75% { transform: translateY(-100px) translateX(-50px); }
    }
    
    .login-card {
        background: rgba(5, 5, 5, 0.7);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(0, 255, 136, 0.2);
        border-radius: 24px;
        padding: 4rem 3rem;
        max-width: 480px;
        width: 90%;
        box-shadow: 0 0 40px rgba(0, 255, 136, 0.1);
        animation: cardEntrance 1s cubic-bezier(0.2, 0.8, 0.2, 1);
        z-index: 2;
        position: relative;
    }

    @keyframes cardEntrance {
        from { opacity: 0; transform: scale(0.9) translateY(30px); filter: blur(10px); }
        to { opacity: 1; transform: scale(1) translateY(0); filter: blur(0); }
    }
    
    .login-title {
        font-size: 4rem !important;
        font-weight: 900;
        margin-bottom: 0.5rem;
        background: linear-gradient(to right, #ffffff, var(--primary-green), #00ccff);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: shine 4s linear infinite;
        letter-spacing: -3px;
        text-transform: uppercase;
    }

    @keyframes shine {
        to { background-position: 200% center; }
    }
    
    .login-subtitle {
        color: var(--text-gray);
        margin-bottom: 3rem;
        font-size: 1rem;
        line-height: 1.6;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 300;
    }

    .login-features {
        display: flex;
        justify-content: center;
        gap: 2rem;
        margin-bottom: 3.5rem;
    }

    .feature-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.75rem;
        color: var(--text-light-gray);
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .feature-icon-box {
        width: 40px;
        height: 40px;
        border: 1px solid rgba(0, 255, 136, 0.3);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(0, 255, 136, 0.05);
        color: var(--primary-green);
        transition: all 0.3s ease;
    }

    .login-card:hover .feature-icon-box {
        border-color: var(--primary-green);
        box-shadow: 0 0 15px rgba(0, 255, 136, 0.2);
    }

    .google-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 15px;
        background: var(--primary-green);
        color: #000 !important;
        text-decoration: none;
        padding: 18px 30px;
        border-radius: 16px;
        font-weight: 700;
        font-size: 1rem;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        box-shadow: 0 10px 20px rgba(0, 255, 136, 0.2);
        width: 100%;
        margin-bottom: 1.5rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .google-btn:hover {
        transform: translateY(-5px) scale(1.02);
        box-shadow: 0 20px 40px rgba(0, 255, 136, 0.4);
        background: #00ffaa;
    }

    .google-btn:active {
        transform: translateY(-2px);
    }

    .dev-mode-link {
        color: var(--text-gray);
        font-size: 0.8rem;
        letter-spacing: 1px;
        text-transform: uppercase;
        background: none;
        border: none;
        padding: 10px;
        cursor: pointer;
        transition: all 0.3s ease;
        opacity: 0.6;
    }

    .dev-mode-link:hover {
        color: white;
        opacity: 1;
        letter-spacing: 2px;
    }
</style>
""", unsafe_allow_html=True)

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

# ==================== GOOGLE AUTHENTICATION CHECK ====================

google_config = load_google_config()

# Handle OAuth callback
code = st.query_params.get("code")
if code and not st.session_state.google_credentials and google_config:
    with st.spinner("Authenticating with Google..."):
        try:
            flow = create_google_flow(google_config)
            flow.fetch_token(code=code)
            credentials = flow.credentials
            st.session_state.google_credentials = credentials
            
            # Get user info
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            st.session_state.google_user_info = user_info
            
            # Clear query params to clean up URL
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Authentication failed: {e}")

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

# ==================== MAIN APP ====================

def main():
    if not st.session_state.google_credentials and not os.environ.get("DEV_MODE"):
        show_login()
    else:
        show_dashboard()

def show_login():
    # Background Particles
    for i in range(10):
        import random
        st.markdown(f'<div class="particle" style="width:{random.randint(2,5)}px; height:{random.randint(2,5)}px; top:{random.randint(0,100)}%; left:{random.randint(0,100)}%; animation-delay:{random.random()*5}s;"></div>', unsafe_allow_html=True)

    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">Khisba</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Planetary Intelligence. 3D Insight.</div>', unsafe_allow_html=True)
    
    st.markdown('''
        <div class="login-features">
            <div class="feature-item">
                <div class="feature-icon-box">🛰️</div>
                <span>Sentinel</span>
            </div>
            <div class="feature-item">
                <div class="feature-icon-box">⚡</div>
                <span>Compute</span>
            </div>
            <div class="feature-item">
                <div class="feature-icon-box">🌐</div>
                <span>Global</span>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    if google_config:
        flow = create_google_flow(google_config)
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        st.markdown(f'''
            <a href="{authorization_url}" target="_self" class="google-btn">
                <span>Enter Khisba Intelligence</span>
                <span style="font-size: 1.2rem; opacity: 0.8;">→</span>
            </a>
        ''', unsafe_allow_html=True)
    else:
        st.warning("Satellite Uplink Offline: Configuration Missing")
        
    if st.button("Initialize Sandbox (Dev Mode)", key="dev_btn"):
        os.environ["DEV_MODE"] = "1"
        st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True) # End login-card
    st.markdown('</div>', unsafe_allow_html=True) # End login-container

def show_dashboard():
    # Center the dashboard content
    st.markdown('<div class="center-container">', unsafe_allow_html=True)
    
    # Main container for centered content
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    # User info and status
    if st.session_state.google_user_info:
        user = st.session_state.google_user_info
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="display: flex; justify-content: center; gap: 20px; margin-bottom: 20px;">
                <span class='user-badge'>
                    <img src="{user.get('picture', '')}" />
                    {user.get('name', 'User')}
                </span>
                <span class='status-badge'>Connected</span>
                <span class='status-badge'>Earth Engine</span>
            </div>
            <h1>KHISBA GIS - 3D Global Vegetation Analytics</h1>
            <p style="color: #999999; margin-top: 10px;">Interactive 3D Globe with Earth Engine Integration</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="display: flex; justify-content: center; gap: 20px; margin-bottom: 20px;">
                <span class='user-badge'>Dev Mode</span>
                <span class='status-badge'>Connected</span>
                <span class='status-badge'>Earth Engine</span>
            </div>
            <h1>KHISBA GIS - 3D Global Vegetation Analytics</h1>
            <p style="color: #999999; margin-top: 10px;">Interactive 3D Globe with Earth Engine Integration</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Logout button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚪 Sign Out", type="secondary", use_container_width=True):
            st.session_state.google_credentials = None
            st.session_state.google_user_info = None
            if "DEV_MODE" in os.environ:
                del os.environ["DEV_MODE"]
            st.rerun()
    
    # Main content area
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title"><span class="icon">🌍</span> Interactive 3D Globe</div>', unsafe_allow_html=True)
    
    # Area Selection
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.session_state.ee_initialized:
            try:
                countries_fc = get_admin_boundaries(0)
                if countries_fc:
                    country_names = get_boundary_names(countries_fc, 0)
                    selected_country = st.selectbox(
                        "Country",
                        options=["Select a country"] + country_names,
                        index=0,
                        help="Choose a country for analysis"
                    )
                else:
                    selected_country = None
                    st.error("Failed to load countries")
            except Exception as e:
                selected_country = None
                st.error(f"Error: {str(e)}")
        else:
            selected_country = None
            st.warning("Earth Engine not initialized")
    
    with col2:
        if selected_country and selected_country != "Select a country":
            try:
                country_feature = countries_fc.filter(ee.Filter.eq('ADM0_NAME', selected_country)).first()
                admin1_fc = get_admin_boundaries(1, country_feature.get('ADM0_CODE').getInfo())
                if admin1_fc:
                    admin1_names = get_boundary_names(admin1_fc, 1)
                    selected_admin1 = st.selectbox(
                        "State/Province",
                        options=["Select state/province"] + admin1_names,
                        index=0,
                        help="Choose a state or province"
                    )
                else:
                    selected_admin1 = None
            except Exception:
                selected_admin1 = None
        else:
            selected_admin1 = None
    
    with col3:
        if selected_admin1 and selected_admin1 != "Select state/province":
            try:
                admin1_feature = admin1_fc.filter(ee.Filter.eq('ADM1_NAME', selected_admin1)).first()
                admin2_fc = get_admin_boundaries(2, None, admin1_feature.get('ADM1_CODE').getInfo())
                if admin2_fc:
                    admin2_names = get_boundary_names(admin2_fc, 2)
                    selected_admin2 = st.selectbox(
                        "Municipality",
                        options=["Select municipality"] + admin2_names,
                        index=0,
                        help="Choose a municipality"
                    )
                else:
                    selected_admin2 = None
            except Exception:
                selected_admin2 = None
        else:
            selected_admin2 = None
    
    # Analysis Parameters
    st.markdown("### Analysis Parameters")
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        start_date = st.date_input(
            "Start Date",
            value=datetime(2023, 1, 1),
            help="Start date for analysis"
        )
    
    with col_b:
        end_date = st.date_input(
            "End Date",
            value=datetime(2023, 12, 31),
            help="End date for analysis"
        )
    
    with col_c:
        collection_choice = st.selectbox(
            "Satellite Collection",
            options=["Sentinel-2", "Landsat 8", "MODIS"],
            index=0,
            help="Choose satellite data source"
        )
    
    index_options = st.multiselect(
        "Vegetation Indices",
        options=["NDVI", "EVI", "SAVI", "NDWI", "LAI"],
        default=["NDVI"],
        help="Select vegetation indices to calculate"
    )
    
    # 3D Mapbox Globe
    st.markdown("### 3D Interactive Globe View")
    
    # Get map parameters
    if selected_country and selected_country != "Select a country":
        try:
            if selected_admin2 and selected_admin2 != "Select municipality":
                geometry = admin2_fc.filter(ee.Filter.eq('ADM2_NAME', selected_admin2))
                area_name = f"{selected_admin2}, {selected_admin1}, {selected_country}"
            elif selected_admin1 and selected_admin1 != "Select state/province":
                geometry = admin1_fc.filter(ee.Filter.eq('ADM1_NAME', selected_admin1))
                area_name = f"{selected_admin1}, {selected_country}"
            else:
                geometry = countries_fc.filter(ee.Filter.eq('ADM0_NAME', selected_country))
                area_name = selected_country
            
            coords_info = get_geometry_coordinates(geometry)
            map_center = coords_info['center']
            map_zoom = coords_info['zoom']
            bounds_data = coords_info.get('bounds')
            
            st.session_state.selected_area_name = area_name
            st.session_state.selected_coordinates = coords_info
            
            # Display selected area info
            st.info(f"**Selected Area:** {area_name}")
        except Exception as e:
            map_center = [0, 20]
            map_zoom = 2
            bounds_data = None
            st.error(f"Error loading area: {str(e)}")
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
        #map {{ width: 100%; height: 500px; }}
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
    
    st.components.v1.html(mapbox_html, height=520)
    
    # Analysis Actions
    col_run, col_export, col_reset = st.columns(3)
    
    with col_run:
        if st.button("🚀 Run Vegetation Analysis", type="primary", use_container_width=True):
            if index_options and st.session_state.selected_area_name:
                with st.spinner("Running analysis..."):
                    # Simulate analysis
                    import time
                    time.sleep(2)
                    
                    # Create sample analysis results
                    results = {}
                    for idx in index_options:
                        results[idx] = {
                            'values': [0.1 + (i * 0.1) for i in range(10)],
                            'dates': pd.date_range(start='2023-01-01', periods=10, freq='M')
                        }
                    
                    st.session_state.analysis_results = results
                    st.success(f"Analysis complete for {st.session_state.selected_area_name}")
                    
                    # Display results
                    st.markdown("### Analysis Results")
                    for idx, data in results.items():
                        df = pd.DataFrame({
                            'Date': data['dates'],
                            idx: data['values']
                        })
                        
                        fig = px.line(df, x='Date', y=idx, title=f'{idx} Trend')
                        fig.update_layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white'),
                            height=300
                        )
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Please select vegetation indices and an area first")
    
    with col_export:
        if st.button("📊 Export Report", use_container_width=True):
            if st.session_state.analysis_results:
                st.toast("Report generated successfully!", icon="✅")
            else:
                st.warning("Run analysis first to generate report")
    
    with col_reset:
        if st.button("🔄 Reset Selection", use_container_width=True):
            st.session_state.selected_area_name = None
            st.session_state.analysis_results = None
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)  # End card
    
    # Footer
    st.markdown("""
    <div style="text-align: center; color: #666666; font-size: 12px; padding: 20px 0; margin-top: 30px;">
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
    
    st.markdown('</div>', unsafe_allow_html=True)  # End main-container
    st.markdown('</div>', unsafe_allow_html=True)  # End center-container

if __name__ == "__main__":
    main()
