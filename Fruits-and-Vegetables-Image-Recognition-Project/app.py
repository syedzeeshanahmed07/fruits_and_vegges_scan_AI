import streamlit as st
from ultralytics import YOLO
from PIL import Image
import numpy as np
import os
import pandas as pd
import time
import altair as alt
import json
from datetime import datetime
import base64
import hashlib
from io import BytesIO
# Get the directory where app.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_path(filename):
    return os.path.join(BASE_DIR, filename)

st.set_page_config(page_title="Fruit & Veggie Classifier", page_icon="🍎", layout="wide")

# Initialize Session State
if 'scan_history' not in st.session_state:
    st.session_state.scan_history = []
if 'is_authenticated' not in st.session_state:
    st.session_state.is_authenticated = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

USERS_FILE = get_path("users.json")

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

def hash_password(password, salt=None):
    salt = salt or os.urandom(16).hex()
    password_hash = hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()
    return salt, password_hash

def verify_password(password, salt, expected_hash):
    _, password_hash = hash_password(password, salt)
    return password_hash == expected_hash

def render_auth_page():
    st.markdown("""
    <div class="auth-header">
        <div class="auth-kicker">Smart produce recognition</div>
        <h1>Fruit & Veggie Scanner</h1>
        <p>Log in or create an account to start scanning fruits and vegetables.</p>
    </div>
    """, unsafe_allow_html=True)

    left, center, right = st.columns([1, 1.15, 1])
    with center:
        login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

        with login_tab:
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("Email", key="login_email").strip().lower()
                password = st.text_input("Password", type="password", key="login_password")
                submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                users = load_users()
                account = users.get(email)
                if account and verify_password(password, account["salt"], account["password_hash"]):
                    st.session_state.is_authenticated = True
                    st.session_state.current_user = account.get("name", email)
                    st.success("Login successful.")
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

        with signup_tab:
            with st.form("signup_form", clear_on_submit=False):
                name = st.text_input("Full Name", key="signup_name").strip()
                email = st.text_input("Email", key="signup_email").strip().lower()
                password = st.text_input("Password", type="password", key="signup_password")
                confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password")
                submitted = st.form_submit_button("Create Account", use_container_width=True)

            if submitted:
                users = load_users()
                if not name or not email or not password:
                    st.error("Please fill in all fields.")
                elif "@" not in email or "." not in email:
                    st.error("Please enter a valid email address.")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters.")
                elif password != confirm_password:
                    st.error("Passwords do not match.")
                elif email in users:
                    st.error("An account already exists with this email.")
                else:
                    salt, password_hash = hash_password(password)
                    users[email] = {
                        "name": name,
                        "salt": salt,
                        "password_hash": password_hash,
                        "created_at": datetime.now().isoformat(timespec="seconds")
                    }
                    save_users(users)
                    st.session_state.is_authenticated = True
                    st.session_state.current_user = name
                    st.success("Account created successfully.")
                    st.rerun()

    st.stop()

NUTRITION_DATA = {
    'apple': {'calories': 52, 'protein': 0.3, 'carbs': 14, 'fact': 'Apples float in water because they are 25% air!', 'tip': 'Store in the fridge to keep them crisp for longer.', 'season': 'Autumn'},
    'banana': {'calories': 89, 'protein': 1.1, 'carbs': 23, 'fact': 'Bananas are technically berries!', 'tip': 'Keep away from other fruits unless you want them to ripen fast.', 'season': 'Year-round'},
    'beetroot': {'calories': 43, 'protein': 1.6, 'carbs': 10, 'fact': 'Beetroot juice can improve athletic performance.', 'tip': 'Store in a cool, dark place or the vegetable crisper.', 'season': 'Summer/Autumn'},
    'bell pepper': {'calories': 20, 'protein': 0.9, 'carbs': 4.6, 'fact': 'Red bell peppers have more vitamin C than an orange!', 'tip': 'Keep dry in the fridge to prevent mold.', 'season': 'Summer'},
    'cabbage': {'calories': 25, 'protein': 1.3, 'carbs': 5.8, 'fact': 'Cabbage is one of the oldest known vegetables.', 'tip': 'Keep tightly wrapped in the fridge.', 'season': 'Winter'},
    'capsicum': {'calories': 20, 'protein': 0.9, 'carbs': 4.6, 'fact': 'Capsicum is just another name for bell peppers!', 'tip': 'Store in a reusable mesh bag in the fridge.', 'season': 'Summer'},
    'carrot': {'calories': 41, 'protein': 0.9, 'carbs': 9.6, 'fact': 'Carrots were originally purple, not orange!', 'tip': 'Store in water to keep them extra crunchy.', 'season': 'Year-round'},
    'cauliflower': {'calories': 25, 'protein': 1.9, 'carbs': 5.0, 'fact': 'Cauliflower comes in four colors: white, orange, purple, and green.', 'tip': 'Store head-down in the fridge to prevent moisture buildup.', 'season': 'Autumn/Winter'},
    'chilli pepper': {'calories': 40, 'protein': 1.9, 'carbs': 8.8, 'fact': 'The heat of a chili pepper is measured in Scoville Heat Units (SHU).', 'tip': 'Can be frozen for long-term use.', 'season': 'Summer'},
    'corn': {'calories': 86, 'protein': 3.2, 'carbs': 19, 'fact': 'Corn is grown on every continent except Antarctica.', 'tip': 'Keep the husk on until you are ready to cook.', 'season': 'Summer'},
    'cucumber': {'calories': 15, 'protein': 0.6, 'carbs': 3.6, 'fact': 'Cucumbers are 95% water!', 'tip': 'Store at the front of the fridge where it is slightly warmer.', 'season': 'Summer'},
    'eggplant': {'calories': 25, 'protein': 1.0, 'carbs': 6.0, 'fact': 'Eggplants are actually classified as berries.', 'tip': 'Best used within a few days of purchase.', 'season': 'Summer'},
    'garlic': {'calories': 149, 'protein': 6.4, 'carbs': 33, 'fact': 'Garlic was used as medicine in ancient times.', 'tip': 'Store in a cool, dry, well-ventilated spot.', 'season': 'Summer'},
    'ginger': {'calories': 80, 'protein': 1.8, 'carbs': 18, 'fact': 'Ginger is a popular remedy for nausea.', 'tip': 'Can be stored in the freezer and grated while frozen.', 'season': 'Year-round'},
    'grapes': {'calories': 69, 'protein': 0.7, 'carbs': 18, 'fact': 'It takes about 2.5 pounds of grapes to make a bottle of wine.', 'tip': 'Don’t wash them until you’re ready to eat.', 'season': 'Autumn'},
    'jalepeno': {'calories': 29, 'protein': 0.9, 'carbs': 6.5, 'fact': 'Jalapeños were the first peppers to travel into space.', 'tip': 'Remove seeds to reduce the heat level.', 'season': 'Summer'},
    'kiwi': {'calories': 61, 'protein': 1.1, 'carbs': 15, 'fact': 'Kiwis have more vitamin C than oranges!', 'tip': 'Ripen at room temperature, then refrigerate.', 'season': 'Winter/Spring'},
    'lemon': {'calories': 29, 'protein': 1.1, 'carbs': 9.3, 'fact': 'Lemons can be used to generate electricity.', 'tip': 'Store in a sealed bag in the fridge for more juice.', 'season': 'Year-round'},
    'lettuce': {'calories': 15, 'protein': 1.4, 'carbs': 2.9, 'fact': 'Lettuce is part of the sunflower family.', 'tip': 'Wrap in a paper towel to absorb excess moisture.', 'season': 'Spring/Summer'},
    'mango': {'calories': 60, 'protein': 0.8, 'carbs': 15, 'fact': 'Mangoes are the most widely consumed fruit in the world.', 'tip': 'Squeeze gently; if it gives, it is ripe!'},
    'onion': {'calories': 40, 'protein': 1.1, 'carbs': 9.3, 'fact': 'Onions make you cry because they release sulfuric acid.', 'tip': 'Keep away from potatoes; they make onions spoil faster.', 'season': 'Year-round'},
    'orange': {'calories': 47, 'protein': 0.9, 'carbs': 12, 'fact': 'The color orange was named after the fruit, not the other way around!', 'tip': 'Store at room temp for a few days, or fridge for weeks.', 'season': 'Winter'},
    'paprika': {'calories': 282, 'protein': 14.0, 'carbs': 54, 'fact': 'Paprika is made from ground bell peppers and chili peppers.', 'tip': 'Store in a cool, dark place to preserve flavor.', 'season': 'Year-round'},
    'pear': {'calories': 57, 'protein': 0.4, 'carbs': 15, 'fact': 'Pears were once called "butter fruit" due to their soft texture.', 'tip': 'Pears ripen from the inside out; check the neck for ripeness.', 'season': 'Autumn'},
    'peas': {'calories': 81, 'protein': 5.4, 'carbs': 14, 'fact': 'Peas are thought to have originated in the Middle East.', 'tip': 'Best eaten as soon as possible after picking.', 'season': 'Spring'},
    'pineapple': {'calories': 50, 'protein': 0.5, 'carbs': 13, 'fact': 'It takes nearly three years for a single pineapple to reach maturation.', 'tip': 'Store upside down for a day to redistribute sugars.', 'season': 'Year-round'},
    'pomegranate': {'calories': 83, 'protein': 1.7, 'carbs': 19, 'fact': 'A single pomegranate can contain over 1,000 seeds!', 'tip': 'Seeds can be frozen for up to 6 months.', 'season': 'Autumn/Winter'},
    'potato': {'calories': 77, 'protein': 2.0, 'carbs': 17, 'fact': 'Potatoes were the first vegetable to be grown in space.', 'tip': 'Store in a dark place to prevent them from turning green.', 'season': 'Year-round'},
    'raddish': {'calories': 16, 'protein': 0.7, 'carbs': 3.4, 'fact': 'Radishes grow incredibly fast—ready to harvest in just 3-4 weeks.', 'tip': 'Remove green tops before storing in the fridge.', 'season': 'Spring'},
    'soy beans': {'calories': 173, 'protein': 17.0, 'carbs': 10, 'fact': 'Soybeans are a complete protein, containing all essential amino acids.', 'tip': 'Edamame should be kept frozen until ready to use.', 'season': 'Summer'},
    'spinach': {'calories': 23, 'protein': 2.9, 'carbs': 3.6, 'fact': 'Spinach loses half its nutritional value after just 8 days.', 'tip': 'Keep as dry as possible in the fridge.', 'season': 'Year-round'},
    'sweetcorn': {'calories': 86, 'protein': 3.2, 'carbs': 19, 'fact': 'An ear of corn always has an even number of rows.', 'tip': 'Eat immediately for the sweetest flavor.', 'season': 'Summer'},
    'sweetpotato': {'calories': 86, 'protein': 1.6, 'carbs': 20, 'fact': 'George Washington grew sweet potatoes at Mount Vernon.', 'tip': 'Do not refrigerate raw sweet potatoes; it ruins the taste.', 'season': 'Autumn'},
    'tomato': {'calories': 18, 'protein': 0.9, 'carbs': 3.9, 'fact': 'Tomatoes are legally vegetables but botanically fruits.', 'tip': 'Store stem-side down at room temperature.', 'season': 'Summer'},
    'turnip': {'calories': 28, 'protein': 0.9, 'carbs': 6.4, 'fact': 'Before pumpkins, Jack-o\'-lanterns were originally carved from turnips!', 'tip': 'Choose smaller turnips for a sweeter flavor.', 'season': 'Autumn/Winter'},
    'watermelon': {'calories': 30, 'protein': 0.6, 'carbs': 7.6, 'fact': 'Watermelons are 92% water.', 'tip': 'A yellow spot on the bottom means it is ripe!', 'season': 'Summer'}
}

# Cache the model so it doesn't reload on every UI interaction
@st.cache_resource
def load_yolo_model():
    # Use yolov8n.pt (detection) or yolov8n-cls.pt (classification)
    # If custom weights are available (e.g. best.pt), use them here
    model_path = get_path("best.pt") if os.path.exists(get_path("best.pt")) else "yolov8n.pt"
    model = YOLO(model_path)
    return model

# The model will use internal names from YOLO results. 
# Nutrition data will be mapped using these names.

def predict(image):
    # YOLOv8 handles image resizing and normalization internally
    results = model.predict(image, verbose=False)
    result = results[0]
    
    # Check if it's a classification or detection model
    if hasattr(result, 'probs') and result.probs is not None:
        # Classification model
        probs = result.probs
        top1_idx = probs.top1
        label = result.names[top1_idx]
        confidence = float(probs.top1conf)
        
        # Get top 3
        top3_indices = probs.top5[:3]
        top_3 = {result.names[int(i)]: float(probs.data[int(i)]) for i in top3_indices}
        
        return label, confidence, top_3, image
    else:
        # Detection model
        if len(result.boxes) > 0:
            # Sort by confidence
            best_box = result.boxes[0]
            label = result.names[int(best_box.cls)]
            confidence = float(best_box.conf)
            
            # For detection, we can also return the annotated image
            annotated_img_array = result.plot()
            annotated_img = Image.fromarray(annotated_img_array[..., ::-1]) # BGR to RGB
            
            # Get top predictions across all detections
            top_3 = {}
            for box in result.boxes[:3]:
                name = result.names[int(box.cls)]
                conf = float(box.conf)
                if name not in top_3:
                    top_3[name] = conf
            
            return label, confidence, top_3, annotated_img
        else:
            return "unknown", 0.0, {}, image
    
# --- UI Layout & Interactivity ---

# Custom CSS for aesthetics
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    
    html, body, [class*="css"], * {
        font-family: 'Inter', sans-serif;
        color: black !important;
    }
    .stApp {
        background: linear-gradient(135deg, #f0fdf4 0%, #e0f2fe 100%);
    }
    .auth-header {
        max-width: 760px;
        margin: 64px auto 26px;
        text-align: center;
        padding: 0 18px;
    }
    .auth-header h1 {
        margin: 10px 0 8px;
        font-size: 2.65rem;
        font-weight: 800;
        color: #064e3b !important;
        letter-spacing: 0;
    }
    .auth-header p {
        margin: 0 auto;
        max-width: 520px;
        color: #374151 !important;
        font-size: 1.02rem;
        line-height: 1.6;
    }
    .auth-kicker {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 7px 13px;
        border-radius: 999px;
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
        color: #047857 !important;
        font-weight: 800;
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    div[data-testid="stTabs"] [role="tablist"] {
        justify-content: center;
        gap: 10px;
        border-bottom: 0;
    }
    div[data-testid="stTabs"] button[role="tab"] {
        background: #ffffff !important;
        border: 1px solid #d1d5db !important;
        border-radius: 999px !important;
        padding: 7px 18px !important;
        color: #374151 !important;
        font-weight: 700 !important;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        background: #ecfdf5 !important;
        border-color: #10b981 !important;
        color: #047857 !important;
    }
    div[data-testid="stForm"] {
        background: #ffffff;
        border: 1px solid #dbeafe;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 20px 55px rgba(15, 23, 42, 0.10);
    }
    div[data-testid="stForm"] label,
    div[data-testid="stTextInput"] label {
        color: #1f2937 !important;
        font-weight: 700 !important;
        font-size: 0.92rem !important;
    }
    div[data-testid="stForm"] input,
    div[data-testid="stForm"] textarea,
    div[data-testid="stTextInput"] input {
        background-color: #ffffff !important;
        background: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        min-height: 46px !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
    }
    div[data-testid="stForm"] input:focus,
    div[data-testid="stForm"] textarea:focus,
    div[data-testid="stTextInput"] input:focus {
        background-color: #ffffff !important;
        background: #ffffff !important;
        border-color: #10b981 !important;
        box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.16) !important;
    }
    div[data-testid="stForm"] input::placeholder,
    div[data-testid="stForm"] textarea::placeholder {
        color: #6b7280 !important;
        -webkit-text-fill-color: #6b7280 !important;
    }
    div[data-testid="stFormSubmitButton"] > button,
    div[data-testid="stFormSubmitButton"] button,
    div.stFormSubmitButton > button {
        background-color: #ffffff !important;
        background: #ffffff !important;
        color: #064e3b !important;
        -webkit-text-fill-color: #064e3b !important;
        border: 2px solid #10b981 !important;
        border-radius: 12px !important;
        min-height: 46px !important;
        font-weight: 800 !important;
        box-shadow: 0 8px 18px rgba(16, 185, 129, 0.14) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover,
    div[data-testid="stFormSubmitButton"] button:hover,
    div.stFormSubmitButton > button:hover {
        background-color: #f0fdf4 !important;
        background: #f0fdf4 !important;
        color: #047857 !important;
        -webkit-text-fill-color: #047857 !important;
        border-color: #047857 !important;
        transform: translateY(-1px);
        box-shadow: 0 12px 26px rgba(16, 185, 129, 0.18) !important;
    }
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Header Styling */
    .main-header {
    color: black !important;
    -webkit-text-fill-color: black !important;
}
    .main-header {
        background: linear-gradient(90deg, #10b981, #3b82f6);
        -webkit-background-clip: text;
            color: black !important;
        -webkit-text-fill-color: black !important;
        font-weight: 800;
        font-size: 3.5rem !important;
        margin-bottom: 0px;
        text-align: center;
        padding-bottom: 10px;
        letter-spacing: -1px;
    }
    .sub-header {
        text-align: center;
        color: black;
        font-size: 1.2rem;
        margin-bottom: 30px;
        font-weight: 400;
    }

    /* Glassmorphism Cards */
    .prediction-card {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.5);
        padding: 30px;
        border-radius: 20px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
        text-align: center;
        margin-bottom: 15px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .prediction-card:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 15px 45px 0 rgba(31, 38, 135, 0.12);
    }
    
    .big-font {
        font-size: 48px !important;
        font-weight: 800;
        background: linear-gradient(90deg, #059669, #10b981);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-top: 10px;
        margin-bottom: 0px;
        letter-spacing: -1px;
    }
    
    .warning-font {
        font-size: 36px !important;
        font-weight: 800;
        color: #ef4444;
        margin-top: 10px;
    }
    
    /* Custom Metric Cards */
    .metric-container {
        display: flex;
        justify-content: space-between;
        gap: 15px;
        margin-top: 20px;
        margin-bottom: 20px;
    }
    .metric-card {
        flex: 1;
        background: rgba(255, 255, 255, 0.85);
        padding: 20px 15px;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.04);
        text-align: center;
        border-bottom: 4px solid #10b981;
        transition: transform 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-3px);
    }
    .metric-label {
        font-size: 13px;
        color: black;;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        font-weight: 600;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 26px;
        font-weight: 800;
        color: black;
    }
    
    /* Fact Card */
    .fact-card {
        background: linear-gradient(135deg, rgba(224, 242, 254, 0.8) 0%, rgba(219, 234, 254, 0.8) 100%);
        backdrop-filter: blur(5px);
        padding: 20px 25px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.8);
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        margin-top: 25px;
        display: flex;
        align-items: center;
        gap: 20px;
        color:black;
    }
    .fact-icon {
        font-size: 36px;
    }
    .fact-text {
        font-size: 16px;
        color: black;
        line-height: 1.5;
    }

    /* Customizing Streamlit's progress bar */
    .stProgress > div > div > div > div {
        background-color: #10b981;
        color : black;
        background-image: linear-gradient(90deg, #10b981, #34d399);
        border-radius: 10px;
    }
    
    /* Image container hover effect */
    .stImage img {
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    .stImage img:hover {
        transform: scale(1.03);
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.8) !important;
        color:black;
        backdrop-filter: blur(15px);
        border-right: 1px solid rgba(255,255,255,0.5);
    }
    
    /* File Uploader "Dropzone" Styling */
    [data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.5);
        border: 2px dashed #10b981;
        border-radius: 15px;
        padding: 20px;
        transition: all 0.3s ease;
    }
    [data-testid="stFileUploader"]:hover {
        background: rgba(255, 255, 255, 0.8);
        border-color: #3b82f6;
    }
    
    /* Footer Styling */
    .footer {
        text-align: center;
        padding: 40px 0 20px 0;
        color: #94a3b8;
        font-size: 14px;
        font-weight: 500;
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        margin-right: 8px;
        margin-bottom: 8px;
        letter-spacing: 0.5px;
    }
    .badge-low-cal { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
    .badge-protein { background: #fef9c3; color: #854d0e; border: 1px solid #fef08a; }
    .badge-carb { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
    .badge-season { background: #e0f2fe; color: #075985; border: 1px solid #bae6fd; }

    /* Recipe Link */
    .recipe-link {
        display: flex;
        align-items: center;
        gap: 10px;
        background: white;
        padding: 12px 20px;
        border-radius: 12px;
        text-decoration: none !important;
        color: black !important;
        font-weight: 600;
        margin-top: 10px;
        border: 1px solid #e2e8f0;
        transition: all 0.3s ease;
    }
    .recipe-link:hover {
        background: #f8fafc;
        border-color: #3b82f6;
        transform: translateX(5px);
    }
    
    /* Share Button */
    .share-btn {
        background: linear-gradient(90deg, #3b82f6, #2563eb);
        color: white !important;
        padding: 12px 25px;
        border-radius: 12px;
        border: none;
        font-weight: 700;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 10px;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.2);
        margin: 20px auto;
        transition: all 0.3s ease;
    }
    .share-btn:hover {
        transform: scale(1.05);
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.3);
    }

    /* Animations */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes float {
        0% { transform: translateY(0px) rotate(0deg); }
        50% { transform: translateY(-20px) rotate(5deg); }
        100% { transform: translateY(0px) rotate(0deg); }
    }
    
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    
    .animate-in {
        animation: fadeInUp 0.6s ease-out forwards;
    }
    
    /* Background Floating Emojis */
    .bg-emoji {
        position: fixed;
        font-size: 40px;
        opacity: 0.1;
        filter: blur(1px);
        z-index: -1;
        animation: float 6s ease-in-out infinite;
    }

    /* Glassmorphism Refinement with Shimmer */
    .prediction-card {
        background: linear-gradient(110deg, rgba(255,255,255,0.7) 45%, rgba(255,255,255,0.85) 50%, rgba(255,255,255,0.7) 55%);
        background-size: 200% 100%;
        animation: fadeInUp 0.6s ease-out forwards, shimmer 10s linear infinite;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.5);
        padding: 30px;
        border-radius: 24px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
        text-align: center;
        margin-bottom: 15px;
        transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease;
    }
    
    .metric-card {
        animation: fadeInUp 0.8s ease-out forwards;
        background: rgba(255, 255, 255, 0.85);
        padding: 22px 15px;
        border-radius: 18px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.04);
        text-align: center;
        border-bottom: 4px solid #10b981;
        transition: all 0.3s ease;
    }
    /* Sidebar & Top Header Styling - Force White Background */
    header[data-testid="stHeader"],
    [data-testid="stSidebar"], 
    [data-testid="stSidebar"] > div:first-child,
    [data-testid="stSidebarNav"],
    [data-testid="stSidebarContent"],
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        background-image: none !important;
    }
    /* Ensure header and sidebar icons/text are visible on white */
    header[data-testid="stHeader"] *,
    [data-testid="stSidebar"] *, 
    [data-testid="stSidebar"] .stText, 
    [data-testid="stSidebar"] label {
        color: #1f2937 !important;
    }

    /* Hide Deploy Button */
    .stDeployButton {
        display: none !important;
    }
    header[data-testid="stHeader"] button {
        display: none !important;
    }

    /* Feedback Buttons Styling */
    div.stButton > button {
        background-color: white !important;
        background: white !important;
        color: #1f2937 !important;
        border: 2px solid #e5e7eb !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    div.stButton > button:hover {
        border-color: #10b981 !important;
        color: #10b981 !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.1);
    }

    /* Main Banner Background Styling */
    .main-banner-container {
        position: relative;
        width: 100%;
        border-radius: 30px;
        overflow: hidden;
        margin-bottom: 20px;
        padding: 60px 20px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: rgba(255, 255, 255, 0.4);
        backdrop-filter: blur(5px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        border: 1px solid rgba(255,255,255,0.5);
    }

    .main-banner-img {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        opacity: 0.70; /* 70% banner image opacity */
        z-index: 0;
    }

    .main-banner-content {
        position: relative;
        z-index: 1;
        text-align: center;
        width: 100%;
    }

    /* Customize File Uploader */
    [data-testid="stFileUploader"] section, 
    [data-testid="stFileUploader"] section > div {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        border: 2px dashed #10b981 !important;
        border-radius: 15px !important;
        padding: 10px !important;
    }
    [data-testid="stFileUploader"] section div,
    [data-testid="stFileUploader"] section span,
    [data-testid="stFileUploader"] section label {
        color: #1f2937 !important; /* Darker text for white background */
    }

    /* Customize Toasts and Alerts */
    div[data-testid="stToast"], 
    div[role="alert"] {
        background-color: white !important;
        color: #1f2937 !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
    }
    div[data-testid="stToast"] *, 
    div[role="alert"] * {
        color: #1f2937 !important;
    }
    
    /* Top Navigation Links */
    .top-nav {
        position: fixed;
        top: 0;
        right: 30px;
        height: 60px;
        display: flex;
        align-items: center;
        justify-content: space-evenly;
        gap: 35px;
        z-index: 999999;
        font-family: 'Inter', sans-serif;
    }
    .top-nav a {
        color: #111827 !important; /* Darker, almost black */
        text-decoration: none !important;
        font-size: 15px;
        font-weight: 700; /* Bold */
        transition: all 0.3s ease;
        padding: 5px 10px;
        border-radius: 8px;
    }
    .top-nav a:hover {
        color: #10b981 !important;
        background: rgba(16, 185, 129, 0.05);
    }
</style>

<div class="top-nav">
    <a href="#">Home</a>
    <a href="#">History</a>
    <a href="#">Help</a>
    <a href="#">Contact</a>
</div>

<!-- Floating Background Elements -->
<div class="bg-emoji" style="top: 10%; left: 5%; animation-delay: 0s;">🍎</div>
<div class="bg-emoji" style="top: 40%; left: 85%; animation-delay: 1s;">🥕</div>
<div class="bg-emoji" style="top: 70%; left: 15%; animation-delay: 2s;">🥦</div>
<div class="bg-emoji" style="top: 85%; left: 80%; animation-delay: 3s;">🍇</div>
<div class="bg-emoji" style="top: 20%; left: 60%; animation-delay: 4s;">🍅</div>
""", unsafe_allow_html=True)

# (Session State initialized at top)

# Load banner image as PIL object to avoid file:// security issues
try:
    BANNER_IMAGE = Image.open(get_path("app_banner_new_1777616357683.png"))
except Exception:
    BANNER_IMAGE = None

if not st.session_state.is_authenticated:
    render_auth_page()

model = load_yolo_model()

# --- Business Logic & Processing ---

# Image Upload
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"], help="Upload a clear image for better results.")

input_image = None
if uploaded_file is not None:
    input_image = Image.open(uploaded_file)

def is_image_valid(img):
    # Check if image is too dark or a solid color
    grayscale = img.convert("L")
    variance = np.std(np.array(grayscale))
    return variance > 10.0  # Threshold for "blankness"

# Pre-process image and update history before UI rendering
analysis_result = None
if input_image is not None and is_image_valid(input_image):
    label, confidence, top_3, annotated_img = predict(input_image)
    analysis_result = {
        'label': label,
        'confidence': confidence,
        'top_3': top_3,
        'annotated_img': annotated_img
    }
    
    # Add to scan history
    current_time = time.strftime("%H:%M")
    if not st.session_state.scan_history or st.session_state.scan_history[-1]['label'] != label:
        st.session_state.scan_history.append({
            'label': label,
            'conf': f"{confidence*100:.1f}",
            'time': current_time
        })
        st.balloons() # Added balloon effect for new scan

# Sidebar
with st.sidebar:
    if BANNER_IMAGE:
        st.image(BANNER_IMAGE, use_container_width=True)
    st.success(f"Signed in as {st.session_state.current_user}")
    if st.button("Logout", use_container_width=True):
        st.session_state.is_authenticated = False
        st.session_state.current_user = None
        st.rerun()
    st.write("---")
    st.title("About the Model")
    st.info(
        "This AI uses YOLOv8 (You Only Look Once) to identify and locate 36 different fruits and vegetables in images."
    )
    st.write("---")
    
    # Navigation Dummy Buttons
    st.markdown("### 🧭 Navigation")
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        st.button("🏠 Home", use_container_width=True, key="nav_home")
        st.button("📜 History", use_container_width=True, key="nav_hist")
    with col_nav2:
        st.button("⚙️ Settings", use_container_width=True, key="nav_set")
        st.button("❓ Help", use_container_width=True, key="nav_help")
    
    st.write("---")
    
    st.subheader("🕒 Recent Scans")
    if not st.session_state.scan_history:
        st.caption("No scans yet. Start uploading!")
    else:
        for scan in reversed(st.session_state.scan_history[-5:]):
            st.markdown(f"""
            <div class="history-item">
                <strong>{scan['label'].capitalize()}</strong><br>
                <span style="color:#64748b; font-size:12px;">{scan['time']} • {scan['conf']}%</span>
            </div>
            """, unsafe_allow_html=True)
            
    st.write("---")
    st.markdown("<p style='color: #4b5563; font-size: 12px; opacity: 0.8;'>Developed using Ultralytics & Streamlit</p>", unsafe_allow_html=True)

# Main Header
hour = time.localtime().tm_hour
if hour < 12: greeting = "Good Morning! 🌅"
elif hour < 17: greeting = "Good Afternoon! ☀️"
else: greeting = "Good Evening! 🌙"

if BANNER_IMAGE:
    buffered = BytesIO()
    BANNER_IMAGE.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    st.markdown(f"""
    <div class="main-banner-container">
        <img src="data:image/png;base64,{img_str}" class="main-banner-img">
        <div class="main-banner-content">
            <p style='color: black; font-weight: 600; margin-bottom: 5px;'>{greeting}</p>
            <h1 class='main-header' style='margin-bottom: 10px;'>Smart Fruit & Veggie Scanner</h1>
            <p class='sub-header' style='margin-bottom: 0px;'>Upload a picture, and our AI will identify it and provide nutritional facts!</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"<p style='text-align: center; color: black; font-weight: 600; margin-bottom: -10px;'>{greeting}</p>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-header'>Smart Fruit & Veggie Scanner</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Upload a picture, and our AI will identify it and provide nutritional facts!</p>", unsafe_allow_html=True)

st.write("---")

# --- UI Rendering ---

if input_image is not None:
    # Use columns for a side-by-side layout
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown("### 🖼️ Input Image")
        if analysis_result:
            st.image(analysis_result['annotated_img'], use_container_width=True)
        else:
            st.image(input_image, use_container_width=True)
            
    with col2:
        st.markdown("### 🤖 AI Analysis")
        
        if not is_image_valid(input_image):
            st.error("⚠️ **Image Too Dark or Invalid!**")
            st.info("The image appears to be a solid color or too dark. Please ensure the image is clear and well-lit.")
        elif analysis_result:
            label = analysis_result['label']
            confidence = analysis_result['confidence']
            top_3 = analysis_result['top_3']
                
            # Error handling / Thresholding
            if confidence < 0.40:
                st.warning("⚠️ Low Confidence Alert")
                st.markdown(f"""
                <div class="prediction-card">
                    <p style='color: #6c757d; font-size: 16px; margin-bottom: 0px;'>Best Guess</p>
                    <p class="warning-font">{label.capitalize()}?</p>
                    <p style='font-size: 14px;'>I'm not entirely sure! This might not be a fruit/vegetable, or the image isn't clear.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                if hasattr(st, "toast"):
                    st.toast(f"Analysis complete! Looks like a {label.capitalize()}.", icon="✨")
                else:
                    st.success(f"Analysis complete! Looks like a {label.capitalize()}.")
                
                # Voice Announcement
                st.markdown(f"""
                    <script>
                        var msg = new SpeechSynthesisUtterance();
                        msg.text = "This looks like a {label}";
                        window.speechSynthesis.speak(msg);
                    </script>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div class="prediction-card">
                    <p style='color: black; font-size: 16px; margin-bottom: 0px; color:black;'>Top Prediction</p>
                    <p class="big-font">{label.capitalize()}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Add gamified animations for high confidence
                if confidence >= 0.8:
                    season = NUTRITION_DATA.get(label, {}).get('season', '')
                    if 'Winter' in season:
                        st.snow()
                    else:
                        st.balloons()

            # Confidence Metric
            confidence_color = "#f20a0a" if confidence >= 0.7 else ('#f59e0b' if confidence >= 0.4 else '#ef4444')
            st.markdown(f"""
            <div style="text-align: center; margin-top: 5px; margin-bottom: 25px; background: rgba(255,255,255,0.6); padding: 10px; border-radius: 12px; display: inline-block; width: 100%;">
                <span style="font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">AI Confidence Score</span><br>
                <span style="font-size: 24px; font-weight: 800; color: {confidence_color};">
                    {confidence * 100:.1f}%
                </span>
            </div>
            """, unsafe_allow_html=True)
            
            # Display Nutrition Facts
            if label in NUTRITION_DATA and confidence >= 0.40:
                info = NUTRITION_DATA[label]
                st.markdown(f"#### 🥗 {label.capitalize()} Nutrition (per 100g)")
                
                # Nutritional Badges logic
                badges_html = ""
                if info['calories'] < 50:
                    badges_html += '<span class="badge badge-low-cal">🍃 Low Calorie</span>'
                if info['protein'] > 1.5:
                    badges_html += '<span class="badge badge-protein">💪 Protein Rich</span>'
                if info['carbs'] > 15:
                    badges_html += '<span class="badge badge-carb">⚡ Energy Boost</span>'
                if 'season' in info:
                    badges_html += f'<span class="badge badge-season">📅 {info["season"]}</span>'
                
                if badges_html:
                    st.markdown(f"<div style='margin-bottom: 15px;'>{badges_html}</div>", unsafe_allow_html=True)

                # Display nutritional metrics using custom HTML cards
                st.markdown(f"""
                <div class="metric-container">
                    <div class="metric-card">
                        <div class="metric-label">Calories</div>
                        <div class="metric-value">{info['calories']} <span style='font-size:14px; font-weight:600; color:#94a3b8;'>kcal</span></div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Protein</div>
                        <div class="metric-value">{info['protein']} <span style='font-size:14px; font-weight:600; color:#94a3b8;'>g</span></div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Carbs</div>
                        <div class="metric-value">{info['carbs']} <span style='font-size:14px; font-weight:600; color:#94a3b8;'>g</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Recipe Inspiration
                st.markdown("#### 👨‍🍳 Recipe Inspiration")
                recipe_query = label.replace(" ", "+")
                st.markdown(f"""
                <a href="https://www.allrecipes.com/search?q={recipe_query}" target="_blank" class="recipe-link">
                    <span>🍳 Explore {label.capitalize()} Recipes on AllRecipes</span>
                    <span style="margin-left: auto;">↗️</span>
                </a>
                <a href="https://www.youtube.com/results?search_query={recipe_query}+recipes" target="_blank" class="recipe-link">
                    <span>🎥 Watch {label.capitalize()} Cooking Guides</span>
                    <span style="margin-left: auto;">↗️</span>
                </a>
                """, unsafe_allow_html=True)
                
                # Fun Fact & Storage Tip
                st.markdown(f"""
                <div class="fact-card" style="margin-top: 20px;">
                    <div class="fact-icon">💡</div>
                    <div class="fact-text"><strong>Did you know?</strong><br>{info['fact']}</div>
                </div>
                <div class="fact-card" style="margin-top: 15px; background: linear-gradient(135deg, #fefce8 0%, #fef9c3 100%); border-left: 5px solid #facc15;">
                    <div class="fact-icon">🧺</div>
                    <div class="fact-text"><strong>Storage Tip:</strong><br>{info['tip']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Share Button
                st.markdown(f"""
                <button onclick="
                    if (navigator.share) {{
                        navigator.share({{
                            title: 'Smart Fruit & Veggie Scanner',
                            text: 'I just scanned a {label.capitalize()}! It has {info['calories']} kcal and is {info['season']}. Check it out!',
                            url: window.location.href
                        }});
                    }} else {{
                        navigator.clipboard.writeText('I just scanned a {label.capitalize()}! Results: {info['calories']} kcal. Scan yours at FruitScanner.com');
                        alert('Link copied to clipboard!');
                    }}
                " class="share-btn">
                    📤 Share Result
                </button>
                """, unsafe_allow_html=True)

                # Feedback Loop
                st.write("---")
                st.markdown("<p style='color: white; font-size: 14px; margin-bottom: 5px;'>Help us improve: Is this prediction correct?</p>", unsafe_allow_html=True)
                fcol1, fcol2 = st.columns(2)
                if fcol1.button("✅ Yes, Correct"):
                    st.balloons() # Added balloon effect for positive feedback
                    st.success("Thanks for the feedback!")
                    # Log feedback locally
                    with open(get_path("feedback.json"), "a") as f:
                        json.dump({"time": str(datetime.now()), "label": label, "correct": True}, f)
                        f.write("\n")
                if fcol2.button("❌ No, Incorrect"):
                    st.error("Sorry! We will use this to improve.")
                    with open(get_path("feedback.json"), "a") as f:
                        json.dump({"time": str(datetime.now()), "label": label, "correct": False}, f)
                        f.write("\n")
                
            # Expandable Data Viz
            with st.expander("📊 View Probability Distribution", expanded=False):
                st.write("How confident is the AI about these possibilities?")
                
                # Create DataFrame for Altair
                chart_data = pd.DataFrame({
                    'Class': [k.capitalize() for k in top_3.keys()],
                    'Probability': [v * 100 for v in top_3.values()]
                })
                
                # Altair Horizontal Bar Chart
                chart = alt.Chart(chart_data).mark_bar(
                    cornerRadiusTopRight=10,
                    cornerRadiusBottomRight=10
                ).encode(
                    x=alt.X('Probability:Q', title='Probability (%)', scale=alt.Scale(domain=[0, 100])),
                    y=alt.Y('Class:N', title=None, sort='-x'),
                    color=alt.Color('Probability:Q', scale=alt.Scale(scheme='greens'), legend=None),
                    tooltip=['Class', 'Probability']
                ).properties(height=150)
                
                st.altair_chart(chart, use_container_width=True)

# Footer
st.markdown("---")
col_f1, col_f2 = st.columns(2)
with col_f1:
    st.markdown("### ❓ Frequently Asked Questions")
    with st.expander("How accurate is the model?"):
        st.write("The model was trained on thousands of images and achieves high accuracy on clear, well-lit photos of single items.")
    with st.expander("Can it identify cooked food?"):
        st.write("It is optimized for raw fruits and vegetables. Identification of cooked or processed dishes may be less accurate.")

with col_f2:
    st.markdown("### 🛠️ Technical Details")
    st.write("- **Architecture:** YOLOv8 (You Only Look Once)")
    st.write("- **Frameworks:** Ultralytics, PyTorch, Streamlit")
    st.write("- **Capability:** Object Detection & Classification")

st.markdown("""
<div class="footer">
    🍎 Smart Fruit & Veggie Scanner • v3.0 • Premium Experience ❤️
</div>
""", unsafe_allow_html=True)
