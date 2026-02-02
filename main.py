import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, timedelta
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
            # Fallback to a minimal config for testing
            client_config = {
                "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
                "project_id": "khisba-gis",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "YOUR_CLIENT_SECRET",
                "redirect_uris": ["http://localhost:8501/"]
            }
        return client_config
    except Exception as e:
        st.error(f"Error loading config: {e}")
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
if "show_welcome" not in st.session_state:
    st.session_state.show_welcome = True
if "session_start_time" not in st.session_state:
    st.session_state.session_start_time = datetime.now()

# ==================== HELPER FUNCTIONS ====================

def get_user_display_name(user_info):
    """Extract display name from user info"""
    if not user_info:
        return "User"
    
    name = user_info.get('name', 'User')
    given_name = user_info.get('given_name', name.split()[0] if ' ' in name else name)
    return given_name

def get_session_duration():
    """Calculate session duration"""
    if 'session_start_time' not in st.session_state:
        st.session_state.session_start_time = datetime.now()
    
    duration = datetime.now() - st.session_state.session_start_time
    hours = duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60
    seconds = duration.seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

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
    
    .stButton > button[data-testid="baseButton-secondary"] {
        background: #222222 !important;
        color: var(--text-white) !important;
        border: 1px solid var(--border-gray) !important;
    }
    
    .stButton > button[data-testid="baseButton-secondary"]:hover {
        background: #333333 !important;
        border-color: var(--primary-green) !important;
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
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .user-badge:hover {
        background: rgba(0, 255, 136, 0.2);
        border-color: var(--primary-green);
        transform: translateY(-1px);
    }
    
    .user-badge img {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        border: 1px solid rgba(0, 255, 136, 0.5);
    }
    
    /* Toast animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

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
if not st.session_state.google_credentials:
    st.markdown("""
    <div class="main-container">
        <div class="content-container" style="max-width: 500px; margin: 100px auto;">
            <div class="card">
                <h1 style="text-align: center; margin-bottom: 10px;">🌍 KHISBA GIS</h1>
                <p style="text-align: center; color: #999999; margin-bottom: 30px;">3D Global Vegetation Analytics</p>
                
                <div style="text-align: center; padding: 20px;">
                    <p style="color: #00ff88; font-weight: 600; margin-bottom: 20px;">Sign in with Google to access the platform</p>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if google_config:
            try:
                flow = create_google_flow(google_config)
                auth_url, _ = flow.authorization_url(prompt='consent')
                st.link_button("🔓 Login with Google", auth_url, type="primary", use_container_width=True)
            except Exception as e:
                st.error(f"Error creating auth flow: {e}")
                # Show demo user info for testing
                st.markdown("""
                <div class="card" style="margin-top: 20px;">
                    <p style="color: #00ff88; font-weight: 600; margin-bottom: 10px;">Demo Mode (Testing Only)</p>
                    <button onclick="window.location.href='?demo=true'" style="width: 100%; background: linear-gradient(90deg, #00ff88, #00cc6a); color: #000; border: none; padding: 12px 20px; border-radius: 8px; font-weight: 600; cursor: pointer;">
                        Enter Demo Mode
                    </button>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.error("Google OAuth configuration not found")
    
    # Demo mode for testing
    if st.query_params.get("demo") == "true":
        st.session_state.google_credentials = "demo_credentials"
        st.session_state.google_user_info = {
            "name": "Demo User",
            "email": "demo@khisba-gis.com",
            "picture": "https://ui-avatars.com/api/?name=Demo+User&background=00ff88&color=000",
            "given_name": "Demo"
        }
        st.query_params.clear()
        st.rerun()
    
    st.stop()

# ==================== MAIN APPLICATION (After Authentication) ====================

# Get user info for display
user_info = st.session_state.google_user_info

# Welcome toast notification
if st.session_state.show_welcome:
    st.markdown(f"""
    <div class="card" style="background: rgba(0, 255, 136, 0.1); border: 1px solid rgba(0, 255, 136, 0.3); margin-bottom: 15px; animation: fadeIn 0.5s;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div class="icon" style="background: rgba(0, 255, 136, 0.2);">👋</div>
                <div>
                    <p style="margin: 0; color: #00ff88; font-weight: 600;">Welcome to KHISBA GIS, {get_user_display_name(user_info)}!</p>
                    <p style="margin: 5px 0 0 0; color: #aaa; font-size: 12px;">Start exploring 3D vegetation analytics. Your session is securely authenticated.</p>
                </div>
            </div>
            <button onclick="this.parentElement.parentElement.style.display='none'" style="background: none; border: none; color: #999; cursor: pointer; font-size: 20px;">×</button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.session_state.show_welcome = False

# Main Dashboard Layout
st.markdown(f"""
<div class="compact-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <div>
        <h1>🌍 KHISBA GIS</h1>
        <p style="color: #999999; margin: 0; font-size: 14px;">Interactive 3D Global Vegetation Analytics</p>
    </div>
    <div style="display: flex; gap: 10px; align-items: center;">
        <div style="text-align: right; padding-right: 10px;">
            <p style="margin: 0; color: #ffffff; font-weight: 600;">Welcome back, {get_user_display_name(user_info)}! 👋</p>
            <p style="margin: 0; font-size: 12px; color: #999999;">{user_info.get('email', '')}</p>
        </div>
        <div class="user-badge" onclick="document.getElementById('logout-modal').style.display='block'">
            <img src="{user_info.get('picture', 'https://ui-avatars.com/api/?name=User&background=00ff88&color=000')}" alt="Profile">
            <span>▼</span>
        </div>
        <span class="status-badge">Connected</span>
        <span class="status-badge">3D Mapbox Globe</span>
        <span class="status-badge">v2.0</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Logout modal
st.markdown("""
<div id="logout-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 9999; align-items: center; justify-content: center;">
    <div class="card" style="max-width: 400px; margin: auto; transform: translateY(50%);">
        <div class="card-title">
            <div class="icon">🚪</div>
            <h3 style="margin: 0;">Logout</h3>
        </div>
        <p style="color: #cccccc; margin-bottom: 20px;">Are you sure you want to logout?</p>
        <div style="display: flex; gap: 10px;">
            <button onclick="window.location.href='?logout=true'" style="flex: 1; background: linear-gradient(90deg, #00ff88, #00cc6a); color: #000; border: none; padding: 10px; border-radius: 6px; font-weight: 600; cursor: pointer;">Yes, Logout</button>
            <button onclick="document.getElementById('logout-modal').style.display='none'" style="flex: 1; background: #222222; color: #fff; border: 1px solid #444; padding: 10px; border-radius: 6px; cursor: pointer;">Cancel</button>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Handle logout
if st.query_params.get("logout") == "true":
    st.session_state.google_credentials = None
    st.session_state.google_user_info = None
    st.session_state.show_welcome = True
    st.query_params.clear()
    st.rerun()

# Sidebar with enhanced user profile
with st.sidebar:
    st.markdown(f"""
    <div class="card">
        <div style="text-align: center; padding: 20px 0;">
            <img src="{user_info.get('picture', 'https://ui-avatars.com/api/?name=User&background=00ff88&color=000')}" style="width: 80px; height: 80px; border-radius: 50%; border: 2px solid #00ff88; margin-bottom: 15px;">
            <h3 style="margin: 10px 0 5px 0; color: #fff;">{user_info.get('name', 'User')}</h3>
            <p style="margin: 0 0 15px 0; color: #999; font-size: 12px;">{user_info.get('email', 'user@example.com')}</p>
            <div style="background: rgba(0, 255, 136, 0.1); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(0, 255, 136, 0.3);">
                <p style="margin: 0; color: #00ff88; font-size: 12px; font-weight: 600;">Welcome to KHISBA GIS</p>
                <p style="margin: 5px 0 0 0; color: #aaa; font-size: 11px;">You have full access to all features</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Logout button with icon
    if st.button("🚪 Logout", type="secondary", use_container_width=True, key="logout_btn"):
        st.session_state.google_credentials = None
        st.session_state.google_user_info = None
        st.session_state.show_welcome = True
        st.query_params.clear()
        st.rerun()
    
    # User session info
    st.markdown(f"""
    <div class="card">
        <div class="card-title">
            <div class="icon">📈</div>
            <h4 style="margin: 0;">Your Session</h4>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
            <span style="color: #999; font-size: 12px;">Duration:</span>
            <span style="color: #00ff88; font-weight: 600;">{get_session_duration()}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
            <span style="color: #999; font-size: 12px;">Access Level:</span>
            <span style="color: #00ff88; font-weight: 600;">Premium</span>
        </div>
        <div style="display: flex; justify-content: space-between;">
            <span style="color: #999; font-size: 12px;">Status:</span>
            <span style="color: #00ff88; font-weight: 600;">● Active</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==================== MAIN CONTENT ====================

# Create main content columns
col1, col2 = st.columns([0.3, 0.7], gap="large")

# Left column - Controls
with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title"><div class="icon">🌍</div><h3 style="margin: 0;">Area Selection</h3></div>', unsafe_allow_html=True)
    
    # Country selection
    countries = ["Select a country", "United States", "Canada", "United Kingdom", "Australia", "Germany", "France", "Japan", "Brazil", "India", "China"]
    selected_country = st.selectbox(
        "Country",
        options=countries,
        index=0,
        help="Choose a country for analysis",
        key="country_select"
    )
    
    if selected_country != "Select a country":
        # State/Province selection
        states = ["Select state/province"] + ["California", "Texas", "New York", "Florida", "Ontario", "Quebec", "England", "Scotland", "New South Wales", "Victoria"]
        selected_state = st.selectbox(
            "State/Province",
            options=states,
            index=0,
            help="Choose a state or province",
            key="state_select"
        )
        
        if selected_state != "Select state/province":
            # Municipality selection
            municipalities = ["Select municipality"] + ["Los Angeles", "San Francisco", "Houston", "Dallas", "Toronto", "Montreal", "London", "Manchester", "Sydney", "Melbourne"]
            selected_municipality = st.selectbox(
                "Municipality",
                options=municipalities,
                index=0,
                help="Choose a municipality",
                key="municipality_select"
            )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Analysis Parameters Card
    if selected_country != "Select a country":
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
            st.success(f"Analysis started for {selected_country}!")
            st.info("This is a demo. In the full version, this would connect to Earth Engine and process satellite data.")
        
        st.markdown('</div>', unsafe_allow_html=True)

# Right column - Map and Results
with col2:
    # Selected Area Info
    if selected_country != "Select a country":
        area_name = selected_country
        if selected_state != "Select state/province":
            area_name = f"{selected_state}, {selected_country}"
        if selected_municipality != "Select municipality":
            area_name = f"{selected_municipality}, {selected_state}, {selected_country}"
        
        st.markdown(f"""
        <div class="card">
            <div class="card-title">
                <div class="icon">📍</div>
                <h3 style="margin: 0;">Selected Area</h3>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <p style="margin: 0; font-size: 18px; font-weight: 600; color: #00ff88;">{area_name}</p>
                    <p style="margin: 5px 0 0 0; color: #999999; font-size: 14px;">Region Selected for Analysis</p>
                </div>
                <span class="status-badge">Ready</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # 3D Globe Map
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title"><div class="icon">🗺️</div><h3 style="margin: 0;">3D Interactive Globe</h3></div>', unsafe_allow_html=True)
    
    # Create a simple map visualization
    st.markdown("""
    <div style="height: 500px; background: linear-gradient(135deg, #0a0a0a 0%, #111111 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; border: 1px solid #222;">
        <div style="text-align: center;">
            <div style="font-size: 64px; margin-bottom: 20px;">🌍</div>
            <h3 style="color: #00ff88; margin-bottom: 10px;">3D Interactive Globe</h3>
            <p style="color: #999; max-width: 400px; margin: 0 auto;">Interactive 3D globe visualization would appear here with Mapbox integration.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Demo Results Section
    if st.session_state.get("run_analysis", False):
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title"><div class="icon">📊</div><h3 style="margin: 0;">Analysis Results (Demo)</h3></div>', unsafe_allow_html=True)
        
        # Create demo data
        demo_data = {
            "NDVI": {"mean": 0.65, "min": 0.42, "max": 0.89, "trend": "↗ Increasing"},
            "EVI": {"mean": 0.52, "min": 0.38, "max": 0.71, "trend": "→ Stable"},
            "NDWI": {"mean": 0.28, "min": 0.15, "max": 0.42, "trend": "↗ Increasing"}
        }
        
        results_df = pd.DataFrame(demo_data).T
        results_df = results_df.reset_index().rename(columns={"index": "Index"})
        
        st.dataframe(results_df, use_container_width=True, hide_index=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown(f"""
<div style="text-align: center; color: #666666; font-size: 12px; padding: 20px 0; margin-top: 30px; border-top: 1px solid #222;">
    <p style="margin: 5px 0;">KHISBA GIS - Interactive 3D Global Vegetation Analytics Platform</p>
    <p style="margin: 5px 0;">Logged in as: {user_info.get('email', 'user@example.com')} | Session: {get_session_duration()}</p>
    <div style="display: flex; justify-content: center; gap: 10px; margin-top: 10px;">
        <span class="status-badge">Demo Mode</span>
        <span class="status-badge">User: {get_user_display_name(user_info)}</span>
        <span class="status-badge">Google Auth</span>
    </div>
</div>
""", unsafe_allow_html=True)
