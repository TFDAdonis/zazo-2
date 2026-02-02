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

# Get current Streamlit Cloud URL dynamically
def get_current_url():
    """Get the current Streamlit Cloud URL"""
    try:
        # Get query parameters to check if we're in OAuth callback
        query_params = st.query_params.to_dict()
        
        # Get current URL from Streamlit's internal config
        # In Streamlit Cloud, we can get it from the environment
        import os
        streamlit_url = os.environ.get('STREAMLIT_SERVER_BASE_URL_PATH', '')
        
        if streamlit_url:
            # Extract base URL
            import re
            match = re.search(r'https://[^/]+', streamlit_url)
            if match:
                return match.group(0)
        
        # Fallback: use the current host
        import urllib.parse
        current_url = st.secrets.get("_SERVER", {}).get("url", "")
        if current_url:
            return current_url
            
        # Last resort: check if we're in Streamlit Cloud
        if "streamlit.app" in os.environ.get("STREAMLIT_SHARE", ""):
            return "https://4uwduabizub3vubysxc8hz.streamlit.app"
            
        return "http://localhost:8501"
    except:
        return "https://4uwduabizub3vubysxc8hz.streamlit.app"

# Get current URL
CURRENT_URL = get_current_url()

# Your Google OAuth credentials with dynamic redirect URI
GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": "475971385635-l2kdjo14scnp1lllbmhegp2qj47e1q6m.apps.googleusercontent.com",
        "project_id": "citric-hawk-457513-i6",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "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",
        "redirect_uris": [
            "https://4uwduabizub3vubysxc8hz.streamlit.app",  # Primary URL
            "https://4uwduabizub3vubysxc8hz.streamlit.app/",  # With trailing slash
            f"{CURRENT_URL}",  # Dynamic URL
            f"{CURRENT_URL}/",  # With trailing slash
            "http://localhost:8501",  # For local development
            "http://localhost:8501/"  # For local development with trailing slash
        ]
    }
}

GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email', 
    'https://www.googleapis.com/auth/userinfo.profile', 
    'openid'
]

def create_google_flow(redirect_uri=None):
    """Create Google OAuth flow with specified redirect URI"""
    if redirect_uri is None:
        redirect_uri = CURRENT_URL
    
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        GOOGLE_CLIENT_CONFIG,
        scopes=GOOGLE_SCOPES,
        redirect_uri=redirect_uri
    )
    return flow

# Initialize session state for Google auth
if "google_credentials" not in st.session_state:
    st.session_state.google_credentials = None
if "google_user_info" not in st.session_state:
    st.session_state.google_user_info = None

# Rest of your CSS and Earth Engine initialization remains the same...

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
    
    /* Login page styling */
    .login-container {
        max-width: 500px;
        margin: 100px auto;
        text-align: center;
    }
    
    .login-card {
        background: var(--card-black);
        border: 1px solid var(--border-gray);
        border-radius: 10px;
        padding: 40px 30px;
        text-align: center;
    }
    
    .google-btn {
        background: #4285F4 !important;
        color: white !important;
        border: none;
        padding: 12px 24px;
        border-radius: 4px;
        font-size: 16px;
        font-weight: 500;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        width: 100%;
        margin: 20px 0;
        transition: all 0.3s ease;
    }
    
    .google-btn:hover {
        background: #3367D6 !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(66, 133, 244, 0.3);
    }
    
    .error-card {
        background: rgba(255, 0, 0, 0.1);
        border: 1px solid rgba(255, 0, 0, 0.3);
        border-radius: 8px;
        padding: 15px;
        margin: 20px 0;
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

# Handle OAuth callback - check for code in query parameters
query_params = st.query_params.to_dict()
code = query_params.get("code")

if code and not st.session_state.google_credentials:
    with st.spinner("Authenticating with Google..."):
        try:
            # Use the current URL as redirect URI
            flow = create_google_flow(CURRENT_URL)
            flow.fetch_token(code=code)
            credentials = flow.credentials
            st.session_state.google_credentials = credentials
            
            # Get user info
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            st.session_state.google_user_info = user_info
            
            # Clear query parameters
            st.query_params.clear()
            st.rerun()
            
        except Exception as e:
            st.error(f"Authentication failed: {str(e)}")
            st.write("Debug info:", traceback.format_exc())
            # Don't clear query params on error so we can debug

# Show login page if not authenticated
if not st.session_state.google_credentials:
    st.markdown(f"""
    <div class="login-container">
        <div class="login-card">
            <h1 style="text-align: center; margin-bottom: 10px;">🌍 KHISBA GIS</h1>
            <p style="text-align: center; color: #999999; margin-bottom: 30px;">3D Global Vegetation Analytics</p>
            
            <div style="text-align: center; padding: 20px;">
                <p style="color: #00ff88; font-weight: 600; margin-bottom: 20px;">Sign in with Google to access the platform</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            # Display current URL for debugging
            st.markdown(f"""
            <div class="card" style="margin-bottom: 20px;">
                <h4 style="color: #00ff88;">🔧 Current Configuration</h4>
                <p style="color: #cccccc; font-size: 12px; margin: 5px 0;">Detected URL: {CURRENT_URL}</p>
                <p style="color: #cccccc; font-size: 12px; margin: 5px 0;">Client ID: {GOOGLE_CLIENT_CONFIG['web']['client_id'][:30]}...</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Create auth flow with current URL
            flow = create_google_flow(CURRENT_URL)
            auth_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            # Store state in session for verification
            st.session_state.oauth_state = state
            
            # Create Google login button
            st.markdown(f"""
            <a href="{auth_url}" target="_self">
                <button class="google-btn">
                    <svg width="18" height="18" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
                        <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                        <path fill="#4285F4" d="M46.5 24c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                        <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                        <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                        <path fill="none" d="M0 0h48v48H0z"/>
                    </svg>
                    Sign in with Google
                </button>
            </a>
            """, unsafe_allow_html=True)
            
            # Debug info
            with st.expander("🔧 Debug Details"):
                st.write("Current URL:", CURRENT_URL)
                st.write("Redirect URIs configured:", GOOGLE_CLIENT_CONFIG["web"]["redirect_uris"])
                st.write("Auth URL generated:", auth_url)
                st.write("Query params:", query_params)
                
            # Instructions to fix Google OAuth console
            with st.expander("⚠️ IMPORTANT: Fix Google OAuth Configuration"):
                st.markdown("""
                ### Add these Redirect URIs to your Google OAuth Console:
                
                1. Go to [Google Cloud Console](https://console.cloud.google.com/)
                2. Navigate to **APIs & Services** > **Credentials**
                3. Click on your OAuth 2.0 Client ID
                4. Under **Authorized redirect URIs**, ADD these:
                
                ```
                https://4uwduabizub3vubysxc8hz.streamlit.app
                https://4uwduabizub3vubysxc8hz.streamlit.app/
                https://zazo-2-6kvuwllqjvqcgevjsxw9rv.streamlit.app
                https://zazo-2-6kvuwllqjvqcgevjsxw9rv.streamlit.app/
                ```
                
                5. Click **SAVE**
                6. Wait 5-10 minutes for changes to propagate
                
                **Note:** Streamlit Cloud sometimes changes the app URL, so add all variations.
                """)
            
        except Exception as e:
            st.error(f"Error creating auth flow: {str(e)}")
            st.write("Full error:", traceback.format_exc())
            
            # Show manual fix instructions
            st.markdown("""
            <div class="error-card">
                <h4>🚨 Authentication Setup Required</h4>
                <p>Please update your Google OAuth Console with these redirect URIs:</p>
                <ol>
                    <li><code>https://4uwduabizub3vubysxc8hz.streamlit.app</code></li>
                    <li><code>https://4uwduabizub3vubysxc8hz.streamlit.app/</code></li>
                    <li><code>https://zazo-2-6kvuwllqjvqcgevjsxw9rv.streamlit.app</code></li>
                    <li><code>https://zazo-2-6kvuwllqjvqcgevjsxw9rv.streamlit.app/</code></li>
                </ol>
                <p><strong>Current URL detected:</strong> <code>{CURRENT_URL}</code></p>
            </div>
            """, unsafe_allow_html=True)
    
    st.stop()

# ==================== MAIN APPLICATION (After Authentication) ====================
# ... [Rest of your main application code remains the same] ...
