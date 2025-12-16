import streamlit as st
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from google.oauth2 import service_account
from googleapiclient.discovery import build
from PIL import Image
from io import BytesIO
import json
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="BrandScout", page_icon="🍌", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stButton>button { background-color: #4285F4; color: white; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
if "GOOGLE_JSON" in st.secrets:
    try:
        # Load the JSON string
        key_info = json.loads(st.secrets["GOOGLE_JSON"])
        creds = service_account.Credentials.from_service_account_info(key_info)
        
        # Initialize Vertex AI with the new method
        vertexai.init(project=key_info["project_id"], location="us-central1", credentials=creds)
    except Exception as e:
        st.error(f"Google Auth Error: {e}")

# --- 3. FUNCTIONS ---

def google_scout_images(query):
    """Uses Google Custom Search to find Behance references."""
    try:
        service = build("customsearch", "v1", developerKey=st.secrets["SEARCH_KEY"])
        res = service.cse().list(
            q=f"{query} branding packaging",
            cx=st.secrets["SEARCH_ENGINE_ID"],
            searchType="image",
            num=3, 
            imgSize="large", 
            safe="active"
        ).execute()
        return [item['link'] for item in res.get('items', [])]
    except Exception as e:
        st.error(f"Search Error: {e}")
        return []

def generate_mockup(industry, logo_image):
    """Generates the image using Google Vertex AI (Imagen 3)."""
    try:
        # UPDATED: Using the correct class for Imagen 3
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
        
        prompt = f"""
        Award-winning product photography of {industry}.
        The product features a logo centered on the packaging.
        Cinematic lighting, 8k resolution, highly detailed, photorealistic.
        """
        
        # Generate
        response = model.generate_images(prompt=prompt, number_of_images=1, aspect_ratio="16:9")
        return response[0]._pil_image
    except Exception as e:
        st.error(f"Generation Error: {e}")
        return None

def composite_logo(background, logo):
    """Stamps the logo on top as a fallback."""
    bg = background.convert("RGBA")
    logo = logo.convert("RGBA")
    
    # Resize logo to 30% of background width
    target_w = int(bg.width * 0.30)
    ratio = target_w / logo.width
    target_h = int(logo.height * ratio)
    logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    # Center
    x = (bg.width - logo.width) // 2
    y = (bg.height - logo.height) // 2
    bg.paste(logo, (x, y), logo)
    return bg

# --- 4. UI ---
st.sidebar.title("🍌 BrandScout")
st.sidebar.info("Powered by Google Vertex + Search")

industry = st.sidebar.text_input("Brand Vibe", "Minimalist Wine Bar")
logo_file = st.sidebar.file_uploader("Upload Logo", type="png")
go_btn = st.sidebar.button("Auto-Design")

if go_btn and logo_file:
    user_logo = Image.open(logo_file)
    
    # 1. SCOUT
    with st.status("🕵️ Scouting Behance...", expanded=True) as status:
        refs = google_scout_images(industry)
        if refs:
            st.write("Inspiration found:")
            cols = st.columns(3)
            for i, url in enumerate(refs):
                try: cols[i].image(url, use_column_width=True)
                except: pass
        
        # 2. GENERATE
        status.write("🎨 Generating 4K Mockup...")
        bg = generate_mockup(industry, user_logo)
        
        if bg:
            # 3. BUILD
            status.write("🔨 Branding...")
            final = composite_logo(bg, user_logo)
            
            status.update(label="Done!", state="complete", expanded=False)
            st.image(final, caption="Final Design", use_column_width=True)
