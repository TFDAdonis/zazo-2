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
    
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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
            
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Authentication failed: {e}")
            st.query_params.clear()

# Show login page if not authenticated
# Show login page if not authenticated
if not st.session_state.google_credentials:
    # Add custom CSS for login page (same CSS as before, but fixed the string)
    
    # Login Page Layout
    st.markdown("""
    <div class="login-container">
        <!-- Left Section: Visual Animation & Branding -->
        <div class="login-left">
            <div class="globe-animation">
                <div class="globe-circle"></div>
                <div class="globe-grid"></div>
                <div class="globe-meridians">
                    <div class="meridian"></div>
                    <div class="meridian"></div>
                    <div class="meridian"></div>
                    <div class="meridian"></div>
                </div>
            </div>
            
            <div class="platform-title">KHISBA GIS</div>
            <div class="platform-subtitle">
                Analyze global vegetation using high-resolution satellite imagery from 
                Sentinel-2, Landsat 8, and MODIS. Process Earth observation data in real-time 
                with Google Earth Engine's powerful analytics platform.
            </div>
            
            <div style="display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap; justify-content: center;">
                <span class="status-badge">Sentinel-2</span>
                <span class="status-badge">Landsat 8</span>
                <span class="status-badge">MODIS</span>
                <span class="status-badge">NDVI/EVI</span>
                <span class="status-badge">Time Series</span>
            </div>
        </div>
        
        <!-- Right Section: Login Card -->
        <div class="login-right">
            <div class="login-card">
                <div class="login-header">
                    <div class="login-icon">🛰️</div>
                    <div class="login-title">Satellite Analytics Portal</div>
                    <div class="login-subtitle">
                        Sign in to access multi-spectral satellite imagery analysis, 
                        vegetation monitoring, and environmental change detection tools.
                    </div>
                </div>
                
                <div class="features-list">
                    <div class="feature-item">
                        <span class="feature-icon">📡</span>
                        <span>Multi-spectral satellite imagery (10m resolution)</span>
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">🌿</span>
                        <span>Vegetation indices: NDVI, EVI, SAVI, NDWI</span>
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">📊</span>
                        <span>Time-series analysis & trend detection</span>
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">🌎</span>
                        <span>Global coverage with historical data since 1984</span>
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">⚡</span>
                        <span>Real-time processing with Google Earth Engine</span>
                    </div>
                </div>
                
                <!-- Google Login Button -->
                <div id="google-login-section"></div>
                
                <div class="or-divider">
                    <span>QUICK ACCESS</span>
                </div>
                
                <!-- Satellite Data Sources -->
                <div class="demo-credentials">
                    <div class="demo-title">
                        <span>🛰️</span> Satellite Data Sources
                    </div>
                    <div class="demo-info">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 15px 0;">
                            <div style="background: rgba(0, 100, 255, 0.1); padding: 10px; border-radius: 6px; text-align: center;">
                                <div style="font-weight: 600; color: #00ff88;">Sentinel-2</div>
                                <div style="font-size: 11px; color: #999;">10m resolution</div>
                            </div>
                            <div style="background: rgba(0, 200, 100, 0.1); padding: 10px; border-radius: 6px; text-align: center;">
                                <div style="font-weight: 600; color: #00ff88;">Landsat 8</div>
                                <div style="font-size: 11px; color: #999;">30m resolution</div>
                            </div>
                        </div>
                        Full analytics features require Google authentication for Earth Engine API access.
                    </div>
                </div>
                
                <div class="terms-text">
                    By signing in, you agree to KHISBA GIS 
                    <a href="#" class="terms-link" onclick="showTerms()">Terms of Service</a> 
                    and 
                    <a href="#" class="terms-link" onclick="showPrivacy()">Privacy Policy</a>. 
                    Satellite data provided by ESA, NASA, and USGS via Google Earth Engine.
                </div>
                
                <!-- Platform Partners -->
                <div style="display: flex; justify-content: center; gap: 20px; margin-top: 25px; opacity: 0.7;">
                    <div style="font-size: 12px; color: #666;">Powered by:</div>
                    <div style="display: flex; gap: 15px; align-items: center;">
                        <span style="color: #00ff88; font-weight: 600;">Google Earth Engine</span>
                        <span style="color: #ccc;">•</span>
                        <span style="color: #00ff88; font-weight: 600;">ESA Sentinel</span>
                        <span style="color: #ccc;">•</span>
                        <span style="color: #00ff88; font-weight: 600;">NASA Landsat</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
    function previewDemo() {
        // Create a modal for demo preview
        const modal = document.createElement('div');
        modal.innerHTML = `
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 10000;
                backdrop-filter: blur(5px);
            ">
                <div style="
                    background: linear-gradient(135deg, #0a0a0a, #111111);
                    border: 1px solid rgba(0, 255, 136, 0.3);
                    border-radius: 15px;
                    padding: 30px;
                    width: 90%;
                    max-width: 500px;
                    position: relative;
                ">
                    <button onclick="this.parentElement.parentElement.remove()" style="
                        position: absolute;
                        top: 15px;
                        right: 15px;
                        background: none;
                        border: none;
                        color: #999;
                        font-size: 20px;
                        cursor: pointer;
                    ">×</button>
                    
                    <div style="text-align: center; margin-bottom: 25px;">
                        <div style="font-size: 48px; margin-bottom: 15px;">🛰️</div>
                        <h3 style="color: #00ff88; margin-bottom: 10px;">Satellite Imagery Demo</h3>
                        <p style="color: #ccc; line-height: 1.6;">
                            For full access to KHISBA GIS satellite analytics platform, 
                            please sign in with Google to authenticate with Earth Engine API.
                        </p>
                    </div>
                    
                    <div style="background: rgba(0, 255, 136, 0.1); border-radius: 10px; padding: 20px; margin: 20px 0;">
                        <div style="color: #00ff88; font-weight: 600; margin-bottom: 10px;">Demo Features Available:</div>
                        <div style="color: #ccc; font-size: 14px; line-height: 1.5;">
                            • Sample vegetation index maps<br>
                            • Historical trend visualization<br>
                            • Area selection tools<br>
                            • Basic analytics dashboard
                        </div>
                    </div>
                    
                    <div style="text-align: center;">
                        <button onclick="window.location.href='#google-login-section'" style="
                            background: linear-gradient(90deg, #00ff88, #00cc6a);
                            color: #000;
                            border: none;
                            padding: 12px 30px;
                            border-radius: 8px;
                            font-weight: 600;
                            cursor: pointer;
                            margin: 10px;
                        ">Sign In for Full Access</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    function showTerms() {
        // Create terms modal
        const modal = document.createElement('div');
        modal.innerHTML = `
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.9);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 10000;
                padding: 20px;
            ">
                <div style="
                    background: #0a0a0a;
                    border: 1px solid rgba(0, 255, 136, 0.3);
                    border-radius: 15px;
                    padding: 30px;
                    width: 90%;
                    max-width: 600px;
                    max-height: 80vh;
                    overflow-y: auto;
                    position: relative;
                ">
                    <button onclick="this.parentElement.parentElement.remove()" style="
                        position: absolute;
                        top: 15px;
                        right: 15px;
                        background: none;
                        border: none;
                        color: #999;
                        font-size: 20px;
                        cursor: pointer;
                    ">×</button>
                    
                    <h3 style="color: #00ff88; margin-bottom: 20px; text-align: center;">KHISBA GIS - Terms of Service</h3>
                    
                    <div style="color: #ccc; line-height: 1.6; font-size: 14px;">
                        <p><strong>1. Platform Usage</strong><br>
                        KHISBA GIS is a satellite imagery analytics platform for research, education, and environmental monitoring purposes.</p>
                        
                        <p><strong>2. Data Sources</strong><br>
                        All satellite imagery is sourced from Google Earth Engine, which aggregates data from ESA (Sentinel), NASA (Landsat), and USGS.</p>
                        
                        <p><strong>3. User Responsibilities</strong><br>
                        Users must comply with data usage policies of respective satellite data providers and attribute data sources appropriately.</p>
                        
                        <p><strong>4. API Limitations</strong><br>
                        Platform usage is subject to Google Earth Engine API rate limits and quota restrictions.</p>
                        
                        <p><strong>5. Privacy</strong><br>
                        We only store authentication information and user preferences. Analysis results are processed in real-time and not permanently stored.</p>
                        
                        <p><strong>6. Intellectual Property</strong><br>
                        Satellite imagery remains property of respective space agencies. Analytical outputs are available for user download and use.</p>
                    </div>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1);">
                        <div style="color: #00ff88; font-weight: 600;">Contact:</div>
                        <div style="color: #ccc; font-size: 13px;">support@khisba-gis.com</div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    function showPrivacy() {
        // Create privacy modal
        const modal = document.createElement('div');
        modal.innerHTML = `
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.9);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 10000;
                padding: 20px;
            ">
                <div style="
                    background: #0a0a0a;
                    border: 1px solid rgba(0, 255, 136, 0.3);
                    border-radius: 15px;
                    padding: 30px;
                    width: 90%;
                    max-width: 600px;
                    max-height: 80vh;
                    overflow-y: auto;
                    position: relative;
                ">
                    <button onclick="this.parentElement.parentElement.remove()" style="
                        position: absolute;
                        top: 15px;
                        right: 15px;
                        background: none;
                        border: none;
                        color: #999;
                        font-size: 20px;
                        cursor: pointer;
                    ">×</button>
                    
                    <h3 style="color: #00ff88; margin-bottom: 20px; text-align: center;">Privacy Policy</h3>
                    
                    <div style="color: #ccc; line-height: 1.6; font-size: 14px;">
                        <p><strong>1. Data Collection</strong><br>
                        We collect only your Google authentication information (email, name, profile picture) to provide personalized access to the platform.</p>
                        
                        <p><strong>2. Data Usage</strong><br>
                        Your information is used solely for authentication and personalization. We do not share your data with third parties.</p>
                        
                        <p><strong>3. Satellite Data Processing</strong><br>
                        All satellite imagery analysis is performed through Google Earth Engine API. Your analysis parameters are processed in real-time but not stored.</p>
                        
                        <p><strong>4. Cookies & Tracking</strong><br>
                        We use session cookies for authentication only. No tracking cookies or analytics are implemented.</p>
                        
                        <p><strong>5. Data Security</strong><br>
                        All data transmission is encrypted using SSL/TLS. Authentication tokens are securely managed via Google OAuth 2.0.</p>
                        
                        <p><strong>6. Data Deletion</strong><br>
                        You can request account deletion at any time by contacting support. This removes all stored authentication information.</p>
                        
                        <p><strong>7. Compliance</strong><br>
                        We comply with Google Earth Engine's terms of service and data usage policies for all satellite data processing.</p>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    </script>
    """, unsafe_allow_html=True)
    
    # Add Google Login Button with Interactive Features
    if google_config:
        try:
            flow = create_google_flow(google_config)
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            # JavaScript for interactive login button
            st.markdown(f"""
            <script>
                // Create interactive Google login button
                const loginSection = document.getElementById('google-login-section');
                loginSection.innerHTML = `
                    <a href="{auth_url}" class="google-login-btn">
                        <svg width="20" height="20" viewBox="0 0 24 24" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));">
                            <path fill="#ffffff" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="#ffffff" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="#ffffff" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                            <path fill="#ffffff" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                        </svg>
                        Continue with Google
                    </a>
                    
                    <div style="text-align: center; margin-top: 15px;">
                        <div style="display: inline-flex; align-items: center; gap: 8px; color: #666; font-size: 12px;">
                            <span>🔐</span>
                            <span>Secured by Google OAuth 2.0</span>
                        </div>
                    </div>
                `;
                
                // Add click animation
                const loginBtn = loginSection.querySelector('.google-login-btn');
                loginBtn.addEventListener('click', function(e) {{
                    // Add loading state
                    this.innerHTML = `
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3); border-top: 2px solid white; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                            <span>Connecting to Google...</span>
                        </div>
                    `;
                    this.style.opacity = '0.8';
                    this.style.pointerEvents = 'none';
                    
                    // Show processing message
                    setTimeout(() => {{
                        document.body.insertAdjacentHTML('beforeend', `
                            <div style="position: fixed; top: 20px; right: 20px; background: rgba(0, 255, 136, 0.9); color: black; padding: 12px 20px; border-radius: 8px; z-index: 9999; animation: slideIn 0.3s ease;">
                                <strong>✓</strong> Redirecting to Google authentication...
                            </div>
                        `);
                    }}, 500);
                }});
                
                // Add CSS for animations
                const style = document.createElement('style');
                style.textContent = `
                    @keyframes spin {{
                        0% {{ transform: rotate(0deg); }}
                        100% {{ transform: rotate(360deg); }}
                    }}
                    @keyframes slideIn {{
                        from {{ transform: translateX(100%); opacity: 0; }}
                        to {{ transform: translateX(0); opacity: 1; }}
                    }}
                `;
                document.head.appendChild(style);
            </script>
            """, unsafe_allow_html=True)
            
            # Add floating particles animation for background
            st.markdown("""
            <script>
                // Create floating particles
                function createParticles() {
                    const container = document.querySelector('.login-container');
                    const particleCount = 30;
                    
                    for (let i = 0; i < particleCount; i++) {
                        const particle = document.createElement('div');
                        particle.style.position = 'absolute';
                        particle.style.width = Math.random() * 4 + 1 + 'px';
                        particle.style.height = particle.style.width;
                        particle.style.background = 'rgba(0, 255, 136, 0.2)';
                        particle.style.borderRadius = '50%';
                        particle.style.left = Math.random() * 100 + '%';
                        particle.style.top = Math.random() * 100 + '%';
                        particle.style.zIndex = '0';
                        
                        // Animation
                        particle.style.animation = `float ${Math.random() * 20 + 10}s linear infinite`;
                        particle.style.animationDelay = Math.random() * 5 + 's';
                        
                        container.appendChild(particle);
                    }
                }
                
                // Add CSS for particle animation
                const particleStyle = document.createElement('style');
                particleStyle.textContent = `
                    @keyframes float {
                        0%, 100% { 
                            transform: translate(0, 0) rotate(0deg);
                            opacity: 0.2;
                        }
                        25% { 
                            transform: translate(20px, -20px) rotate(90deg);
                            opacity: 0.4;
                        }
                        50% { 
                            transform: translate(0, -40px) rotate(180deg);
                            opacity: 0.2;
                        }
                        75% { 
                            transform: translate(-20px, -20px) rotate(270deg);
                            opacity: 0.4;
                        }
                    }
                `;
                document.head.appendChild(particleStyle);
                
                // Create particles when page loads
                window.addEventListener('load', createParticles);
            </script>
            """, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Error creating auth flow: {e}")
    else:
        st.markdown("""
        <div style="text-align: center; padding: 40px; background: rgba(255, 0, 0, 0.1); border-radius: 12px; border: 1px solid rgba(255, 0, 0, 0.2);">
            <div style="font-size: 48px; margin-bottom: 20px;">⚠️</div>
            <h3 style="color: #ff4444; margin-bottom: 10px;">Configuration Required</h3>
            <p style="color: #cccccc;">Google OAuth configuration not found. Please contact your administrator.</p>
            <button onclick="window.location.reload()" style="
                background: rgba(0, 255, 136, 0.1);
                border: 1px solid rgba(0, 255, 136, 0.3);
                color: #00ff88;
                padding: 10px 20px;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
                margin-top: 20px;
            ">Retry Connection</button>
        </div>
        """, unsafe_allow_html=True)
    
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
            <img src="{user_info.get('picture', '')}" alt="Profile">
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
            <img src="{user_info.get('picture', '')}" style="width: 40px; height: 40px; border-radius: 50%;">
            <div>
                <p style="margin: 0; font-weight: 600; color: #fff;">{user_info.get('name', 'User')}</p>
                <p style="margin: 0; font-size: 12px; color: #999;">{user_info.get('email', '')}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚪 Logout", type="secondary", use_container_width=True):
        st.session_state.google_credentials = None
        st.session_state.google_user_info = None
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
