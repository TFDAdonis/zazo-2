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
import numpy as np

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
if 'vegetation_data' not in st.session_state:
    st.session_state.vegetation_data = None
if 'time_series_data' not in st.session_state:
    st.session_state.time_series_data = None

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
                
                st.markdown(f"""
                <div class="card" style="margin-top: 20px;">
                    <p style="text-align: center; color: #666666; font-size: 12px;">
                        Configured redirect: <code>{google_config['redirect_uris'][0]}</code>
                    </p>
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error creating auth flow: {e}")
        else:
            st.error("Google OAuth configuration not found")
    
    st.stop()

# ==================== EARTH ENGINE HELPER FUNCTIONS ====================

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

def get_satellite_collection(collection_name, start_date, end_date, geometry):
    """Get satellite data collection based on selection"""
    try:
        if collection_name == "Sentinel-2":
            collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                .filterDate(start_date, end_date) \
                .filterBounds(geometry) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        
        elif collection_name == "Landsat 8":
            collection = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2') \
                .filterDate(start_date, end_date) \
                .filterBounds(geometry) \
                .filter(ee.Filter.lt('CLOUD_COVER', 20))
        
        elif collection_name == "MODIS":
            collection = ee.ImageCollection('MODIS/061/MOD13Q1') \
                .filterDate(start_date, end_date) \
                .filterBounds(geometry)
        
        else:
            collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                .filterDate(start_date, end_date) \
                .filterBounds(geometry) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        
        return collection
    except Exception as e:
        st.error(f"Error loading satellite collection: {str(e)}")
        return None

def calculate_ndvi(image):
    """Calculate NDVI from satellite image"""
    if 'B8' in image.bandNames().getInfo() and 'B4' in image.bandNames().getInfo():  # Sentinel-2
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
    elif 'SR_B5' in image.bandNames().getInfo() and 'SR_B4' in image.bandNames().getInfo():  # Landsat 8
        ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
    elif 'NDVI' in image.bandNames().getInfo():  # MODIS
        ndvi = image.select('NDVI')
    else:
        ndvi = image.select([0]).multiply(0)  # Return empty if no bands found
    return ndvi

def calculate_evi(image):
    """Calculate EVI from satellite image"""
    try:
        if 'B8' in image.bandNames().getInfo() and 'B4' in image.bandNames().getInfo() and 'B2' in image.bandNames().getInfo():  # Sentinel-2
            evi = image.expression(
                '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
                {
                    'NIR': image.select('B8'),
                    'RED': image.select('B4'),
                    'BLUE': image.select('B2')
                }
            ).rename('EVI')
        elif 'SR_B5' in image.bandNames().getInfo() and 'SR_B4' in image.bandNames().getInfo() and 'SR_B2' in image.bandNames().getInfo():  # Landsat 8
            evi = image.expression(
                '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
                {
                    'NIR': image.select('SR_B5'),
                    'RED': image.select('SR_B4'),
                    'BLUE': image.select('SR_B2')
                }
            ).rename('EVI')
        else:
            evi = image.select([0]).multiply(0)  # Return empty if no bands found
        return evi
    except:
        return None

def calculate_savi(image, L=0.5):
    """Calculate SAVI from satellite image"""
    try:
        if 'B8' in image.bandNames().getInfo() and 'B4' in image.bandNames().getInfo():  # Sentinel-2
            savi = image.expression(
                '((NIR - RED) / (NIR + RED + L)) * (1 + L)',
                {
                    'NIR': image.select('B8'),
                    'RED': image.select('B4'),
                    'L': L
                }
            ).rename('SAVI')
        elif 'SR_B5' in image.bandNames().getInfo() and 'SR_B4' in image.bandNames().getInfo():  # Landsat 8
            savi = image.expression(
                '((NIR - RED) / (NIR + RED + L)) * (1 + L)',
                {
                    'NIR': image.select('SR_B5'),
                    'RED': image.select('SR_B4'),
                    'L': L
                }
            ).rename('SAVI')
        else:
            savi = image.select([0]).multiply(0)
        return savi
    except:
        return None

def calculate_ndwi(image):
    """Calculate NDWI from satellite image"""
    try:
        if 'B8' in image.bandNames().getInfo() and 'B3' in image.bandNames().getInfo():  # Sentinel-2
            ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI')
        elif 'SR_B3' in image.bandNames().getInfo() and 'SR_B5' in image.bandNames().getInfo():  # Landsat 8
            ndwi = image.normalizedDifference(['SR_B3', 'SR_B5']).rename('NDWI')
        else:
            ndwi = image.select([0]).multiply(0)
        return ndwi
    except:
        return None

def analyze_vegetation(geometry, start_date, end_date, collection_name, indices):
    """Perform vegetation analysis on selected area"""
    try:
        with st.spinner("Fetching satellite data..."):
            # Get satellite collection
            collection = get_satellite_collection(collection_name, start_date, end_date, geometry)
            
            if collection is None:
                st.error("Failed to get satellite data")
                return None
            
            # Get the number of images
            count = collection.size().getInfo()
            st.info(f"Found {count} images for the selected period")
            
            if count == 0:
                st.warning("No satellite images found for the selected area and date range")
                return None
            
            # Create composite
            composite = collection.median().clip(geometry)
            
            # Calculate selected indices
            results = {}
            
            if 'NDVI' in indices:
                with st.spinner("Calculating NDVI..."):
                    ndvi = calculate_ndvi(composite)
                    ndvi_stats = ndvi.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=geometry,
                        scale=100,
                        maxPixels=1e9
                    )
                    ndvi_mean = ndvi_stats.get('NDVI').getInfo()
                    results['NDVI'] = {
                        'value': ndvi_mean if ndvi_mean else 0,
                        'description': 'Normalized Difference Vegetation Index',
                        'range': '-1 to 1',
                        'healthy_range': '0.3 to 0.8'
                    }
            
            if 'EVI' in indices:
                with st.spinner("Calculating EVI..."):
                    evi = calculate_evi(composite)
                    if evi:
                        evi_stats = evi.reduceRegion(
                            reducer=ee.Reducer.mean(),
                            geometry=geometry,
                            scale=100,
                            maxPixels=1e9
                        )
                        evi_mean = evi_stats.get('EVI').getInfo()
                        results['EVI'] = {
                            'value': evi_mean if evi_mean else 0,
                            'description': 'Enhanced Vegetation Index',
                            'range': '-1 to 1',
                            'healthy_range': '0.2 to 0.8'
                        }
            
            if 'SAVI' in indices:
                with st.spinner("Calculating SAVI..."):
                    savi = calculate_savi(composite)
                    if savi:
                        savi_stats = savi.reduceRegion(
                            reducer=ee.Reducer.mean(),
                            geometry=geometry,
                            scale=100,
                            maxPixels=1e9
                        )
                        savi_mean = savi_stats.get('SAVI').getInfo()
                        results['SAVI'] = {
                            'value': savi_mean if savi_mean else 0,
                            'description': 'Soil Adjusted Vegetation Index',
                            'range': '-1 to 1',
                            'healthy_range': '0.1 to 0.7'
                        }
            
            if 'NDWI' in indices:
                with st.spinner("Calculating NDWI..."):
                    ndwi = calculate_ndwi(composite)
                    if ndwi:
                        ndwi_stats = ndwi.reduceRegion(
                            reducer=ee.Reducer.mean(),
                            geometry=geometry,
                            scale=100,
                            maxPixels=1e9
                        )
                        ndwi_mean = ndwi_stats.get('NDWI').getInfo()
                        results['NDWI'] = {
                            'value': ndwi_mean if ndwi_mean else 0,
                            'description': 'Normalized Difference Water Index',
                            'range': '-1 to 1',
                            'healthy_range': '> 0.2 for water presence'
                        }
            
            # Generate time series data
            time_series_data = generate_time_series(collection, geometry, indices)
            
            return {
                'results': results,
                'time_series': time_series_data,
                'composite_image': composite,
                'image_count': count
            }
            
    except Exception as e:
        st.error(f"Error in vegetation analysis: {str(e)}")
        traceback.print_exc()
        return None

def generate_time_series(collection, geometry, indices):
    """Generate time series data for selected indices"""
    try:
        time_series = {}
        
        # Get image dates
        dates = collection.aggregate_array('system:time_start').getInfo()
        date_list = [datetime.fromtimestamp(date/1000) for date in dates]
        
        # Calculate NDVI time series
        if 'NDVI' in indices:
            ndvi_series = []
            for i in range(min(10, len(date_list))):  # Limit to 10 points for performance
                try:
                    img = ee.Image(collection.toList(collection.size()).get(i))
                    ndvi = calculate_ndvi(img)
                    if ndvi:
                        stats = ndvi.reduceRegion(
                            reducer=ee.Reducer.mean(),
                            geometry=geometry,
                            scale=100,
                            maxPixels=1e9
                        )
                        val = stats.get('NDVI').getInfo()
                        ndvi_series.append({
                            'date': date_list[i],
                            'value': val if val else 0
                        })
                except:
                    continue
            
            time_series['NDVI'] = ndvi_series
        
        return time_series
        
    except Exception as e:
        st.error(f"Error generating time series: {str(e)}")
        return {}

def create_vegetation_map(composite_image, geometry, index='NDVI'):
    """Create vegetation visualization map"""
    try:
        # Calculate the selected index
        if index == 'NDVI':
            vis_image = calculate_ndvi(composite_image)
        elif index == 'EVI':
            vis_image = calculate_evi(composite_image)
        elif index == 'SAVI':
            vis_image = calculate_savi(composite_image)
        elif index == 'NDWI':
            vis_image = calculate_ndwi(composite_image)
        else:
            vis_image = calculate_ndvi(composite_image)
        
        # Get visualization parameters
        vis_params = {
            'min': -1,
            'max': 1,
            'palette': ['red', 'yellow', 'green']
        }
        
        # Get map center
        coords_info = get_geometry_coordinates(geometry)
        
        # Create map
        map_obj = folium.Map(location=coords_info['center'][::-1], zoom_start=coords_info['zoom'])
        
        # Add the image layer
        map_id_dict = vis_image.getMapId(vis_params)
        
        folium.TileLayer(
            tiles=map_id_dict['tile_fetcher'].url_format,
            attr='Google Earth Engine',
            overlay=True,
            name=f'{index} Map'
        ).add_to(map_obj)
        
        # Add geometry boundary
        bounds = coords_info['bounds']
        if bounds:
            folium.Rectangle(
                bounds=[[bounds[0][0], bounds[0][1]], [bounds[1][0], bounds[1][1]]],
                color='#00ff88',
                fill=False,
                weight=3
            ).add_to(map_obj)
        
        folium.LayerControl().add_to(map_obj)
        
        return map_obj
        
    except Exception as e:
        st.error(f"Error creating vegetation map: {str(e)}")
        return None

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
            options=["NDVI", "EVI", "SAVI", "NDWI"],
            default=["NDVI"],
            help="Select vegetation indices to calculate",
            key="index_select"
        )
        
        # Add analysis type selection
        analysis_type = st.selectbox(
            "Analysis Type",
            options=["Single Date Analysis", "Time Series Analysis"],
            index=0,
            help="Choose analysis type",
            key="analysis_type"
        )
        
        if st.button("🚀 Run Analysis", type="primary", use_container_width=True, key="run_analysis"):
            if not index_options:
                st.warning("Please select at least one vegetation index")
            else:
                with st.spinner("Running vegetation analysis..."):
                    try:
                        # Convert dates to strings
                        start_str = start_date.strftime('%Y-%m-%d')
                        end_str = end_date.strftime('%Y-%m-%d')
                        
                        # Perform analysis
                        analysis_results = analyze_vegetation(
                            st.session_state.selected_geometry,
                            start_str,
                            end_str,
                            collection_choice,
                            index_options
                        )
                        
                        if analysis_results:
                            st.session_state.vegetation_data = analysis_results
                            st.session_state.analysis_results = analysis_results['results']
                            st.session_state.time_series_data = analysis_results['time_series']
                            st.success("Analysis completed successfully!")
                        else:
                            st.error("Analysis failed. Please try different parameters.")
                            
                    except Exception as e:
                        st.error(f"Error during analysis: {str(e)}")
        
        # Add download button for results
        if st.session_state.vegetation_data:
            if st.button("📥 Download Results", type="secondary", use_container_width=True):
                try:
                    # Create results DataFrame
                    results_list = []
                    for index, data in st.session_state.analysis_results.items():
                        results_list.append({
                            'Index': index,
                            'Value': round(data['value'], 4),
                            'Description': data['description'],
                            'Range': data['range'],
                            'Healthy Range': data['healthy_range']
                        })
                    
                    results_df = pd.DataFrame(results_list)
                    
                    # Convert to CSV
                    csv = results_df.to_csv(index=False)
                    
                    # Create download button
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"vegetation_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Error creating download: {str(e)}")
        
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
    if st.session_state.vegetation_data:
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Display analysis results
        st.markdown('<div class="compact-header"><h3>Vegetation Analysis Results</h3><span class="status-badge">Complete</span></div>', unsafe_allow_html=True)
        
        # Results Cards
        results = st.session_state.analysis_results
        if results:
            cols = st.columns(len(results))
            for idx, (index, data) in enumerate(results.items()):
                with cols[idx]:
                    value = data['value']
                    
                    # Determine color based on value
                    if value < 0:
                        color = "#ff4444"  # Red for negative
                    elif value < 0.3:
                        color = "#ffaa44"  # Orange for low
                    elif value < 0.6:
                        color = "#44ff88"  # Light green for moderate
                    else:
                        color = "#00ff88"  # Green for high
                    
                    st.markdown(f"""
                    <div class="card" style="text-align: center;">
                        <h4 style="margin: 0 0 10px 0; color: {color};">{index}</h4>
                        <p style="font-size: 24px; font-weight: 600; margin: 0; color: {color};">{value:.4f}</p>
                        <p style="font-size: 12px; color: #999999; margin: 5px 0 0 0;">{data['description']}</p>
                        <p style="font-size: 10px; color: #666666; margin: 5px 0 0 0;">Range: {data['range']}</p>
                        <p style="font-size: 10px; color: #666666; margin: 5px 0 0 0;">Healthy: {data['healthy_range']}</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Time Series Charts
        if st.session_state.time_series_data and 'NDVI' in st.session_state.time_series_data:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title"><div class="icon">📈</div><h3 style="margin: 0;">NDVI Time Series</h3></div>', unsafe_allow_html=True)
            
            ts_data = st.session_state.time_series_data['NDVI']
            if ts_data:
                df = pd.DataFrame(ts_data)
                df['date'] = pd.to_datetime(df['date'])
                
                fig = px.line(df, x='date', y='value', 
                             title='NDVI Time Series',
                             labels={'value': 'NDVI Value', 'date': 'Date'},
                             color_discrete_sequence=['#00ff88'])
                
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='#ffffff',
                    xaxis=dict(showgrid=True, gridcolor='#222222'),
                    yaxis=dict(showgrid=True, gridcolor='#222222'),
                    title_font_color='#00ff88'
                )
                
                st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Vegetation Map
        if 'composite_image' in st.session_state.vegetation_data:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title"><div class="icon">🗺️</div><h3 style="margin: 0;">Vegetation Index Map</h3></div>', unsafe_allow_html=True)
            
            map_index = st.selectbox(
                "Select Index for Map",
                options=list(results.keys()),
                index=0,
                help="Choose index to visualize on map"
            )
            
            try:
                vegetation_map = create_vegetation_map(
                    st.session_state.vegetation_data['composite_image'],
                    st.session_state.selected_geometry,
                    map_index
                )
                
                if vegetation_map:
                    st_folium(vegetation_map, width=800, height=400)
                else:
                    st.info("Map visualization not available for this index")
            except Exception as e:
                st.error(f"Error displaying vegetation map: {str(e)}")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Detailed Statistics
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title"><div class="icon">📊</div><h3 style="margin: 0;">Detailed Statistics</h3></div>', unsafe_allow_html=True)
        
        stats_data = []
        for index, data in results.items():
            value = data['value']
            
            # Health assessment
            if value < 0:
                health_status = "Poor (Bare Soil/Water)"
                health_color = "#ff4444"
            elif value < 0.3:
                health_status = "Low Vegetation"
                health_color = "#ffaa44"
            elif value < 0.6:
                health_status = "Moderate Vegetation"
                health_color = "#44ff88"
            else:
                health_status = "Healthy/Dense Vegetation"
                health_color = "#00ff88"
            
            stats_data.append({
                'Vegetation Index': index,
                'Value': round(value, 4),
                'Health Status': health_status,
                'Description': data['description']
            })
        
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Interpretation Guide
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title"><div class="icon">📖</div><h3 style="margin: 0;">Interpretation Guide</h3></div>', unsafe_allow_html=True)
        
        guide_data = {
            "NDVI": {
                "Negative values": "Water bodies, snow, ice, or clouds",
                "0 to 0.2": "Bare soil, rocks, or urban areas",
                "0.2 to 0.5": "Sparse vegetation, grasslands, or agricultural areas",
                "0.5 to 0.8": "Moderate to dense vegetation",
                "Above 0.8": "Very dense, healthy vegetation"
            },
            "EVI": {
                "Negative to 0.2": "Bare soil or water",
                "0.2 to 0.5": "Sparse vegetation",
                "0.5 to 0.8": "Moderate to dense vegetation",
                "Above 0.8": "Very dense vegetation"
            }
        }
        
        for index, ranges in guide_data.items():
            if index in results:
                st.markdown(f"**{index} Ranges:**")
                for range_desc, meaning in ranges.items():
                    st.markdown(f"- **{range_desc}**: {meaning}")
                st.markdown("---")
        
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
        <span class="status-badge">Real-time Analysis</span>
    </div>
</div>
""", unsafe_allow_html=True)
