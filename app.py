import streamlit as st
from google.cloud import aiplatform
from googleapiclient.discovery import build
from PIL import Image
from io import BytesIO
import json
import os

# --- 1. SETUP ---
st.set_page_config(page_title="BrandScout: All-Google Edition", page_icon="🍌", layout="wide")

# Styling
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stButton>button { background-color: #4285F4; color: white; border: none; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# Authenticate Vertex AI (Image Generator)
# UPDATED: Now looking for 'GOOGLE_KEY' to match your settings
if "GOOGLE_KEY" in st.secrets:
    try:
        key_info = json.loads(st.secrets["GOOGLE_KEY"])
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_info(key_info)
        aiplatform.init(project=key_info["project_id"], location="us-central1", credentials=creds)
    except Exception as e:
        st.error(f"Vertex AI Auth Error: {e}")

# --- 2. FUNCTIONS ---

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
    from google.cloud.aiplatform.gapic.schema import predict
    model = aiplatform.ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
    
    prompt = f"""
    Award-winning product photography of {industry}.
    The product features a logo centered on the packaging.
    Cinematic lighting, 8k resolution, highly detailed, photorealistic.
    """
    
    response = model.generate_images(prompt=prompt, number_of_images=1, aspect_ratio="16:9")
    return response[0]._pil_image

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

# --- 3. UI ---
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
        
        # 3. BUILD
        status.write("🔨 Branding...")
        final = composite_logo(bg, user_logo)
        
        status.update(label="Done!", state="complete", expanded=False)
        st.image(final, caption="Final Design", use_column_width=True)