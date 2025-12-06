import streamlit as st
from rembg import remove
from PIL import Image, ImageOps, ImageFilter
from io import BytesIO
from openai import OpenAI
import requests
import os

# ==========================================
# 🔐 GÜVENLİ AYARLAR
# ==========================================
if "OPENAI_API_KEY" in st.secrets:
    SABIT_API_KEY = st.secrets["OPENAI_API_KEY"]
else:
    st.error("🚨 API Anahtarı bulunamadı!")
    st.stop()
# ==========================================

# --- SAYFA AYARLARI ---
icon_path = "ALPTECHAI.png" if os.path.exists("ALPTECHAI.png") else "📸"
st.set_page_config(page_title="ALPTECH AI Stüdyo", page_icon=icon_path, layout="wide", initial_sidebar_state="collapsed")

# --- TEMA MANTIĞI ---
# Sayfanın en tepesine, sağa yaslı bir toggle koyuyoruz
col_bosluk, col_tema = st.columns([10, 1]) 
with col_tema:
    # Güneş/Ay ikonu ile geçiş
    karanlik_mod = st.toggle("🌙 / ☀️", value=True)

# Seçilen temaya göre renkleri belirle
if karanlik_mod:
    # --- KARANLIK MOD RENKLERİ ---
    tema = {
        "bg": "#0e1117",
        "text": "white",
        "subtext": "#b0b0b0",
        "card_bg": "#161616",
        "border": "#333",
        "input_bg": "#1c1c1c",
        "input_text": "white",
        "uploader_border": "#00BFFF"
    }
else:
    # --- AYDINLIK MOD RENKLERİ ---
    tema = {
        "bg": "#ffffff",
        "text": "#000000",
        "subtext": "#555555",
        "card_bg": "#f8f9fa",
        "border": "#e0e0e0",
        "input_bg": "#ffffff",
        "input_text": "black",
        "uploader_border": "#007acc"
    }

# --- TASARIM (CSS) ---
# CSS'i dinamik hale getirdik (f-string ile renkleri basıyoruz)
st.markdown(f"""
    <style>
    /* Ana arka plan ve metin rengi */
    .main {{ background-color: {tema['bg']}; }}
    h1, h2, h3, h4, p, label, .stMarkdown {{ font-family: 'Helvetica', sans-serif; color: {tema['text']} !important; }}
    
    /* Sağ üst menüleri gizle */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    [data-testid="stToolbar"] {{visibility: hidden !important;}}
    [data-testid="stSidebar"] {{ display: none; }}

    /* Butonlar */
    .stButton>button {{ 
        width: 100%; 
        border-radius: 8px; 
        font-weight: bold; 
        height: 50px; 
        background-color: #00BFFF; 
        color: white; 
        border: none;
    }}
    .stButton>button:hover {{ background-color: #009ACD; }}

    /* Seçim Kutuları ve Inputlar */
    .stSelectbox, .stTextInput {{ border-radius: 8px; }}
    .stTextArea textarea {{ 
        border-radius: 8px; 
        border: 1px solid {tema['border']}; 
        background-color: {tema['input_bg']}; 
        color: {tema['input_text']}; 
    }}
    /* Dropdown menü içi */
    div[data-baseweb="select"] > div {{
        background-color: {tema['input_bg']};
        color: {tema['input_text']};
        border-color: {tema['border']};
    }}
    
    /* Dosya Yükleyici */
    .stFileUploader {{ 
        border: 2px dashed {tema['uploader_border']}; 
        border-radius: 12px; 
        padding: 30px; 
        text-align: center; 
        background-color: {tema['card_bg']};
    }}
    .stFileUploader label {{ color: {tema['text']} !important; }}
    
    /* Sekme Tasarımı */
    .stTabs [data-baseweb="tab-list"] {{ justify-content: center; gap: 15px; margin-bottom: 20px; }}
    .stTabs [data-baseweb="tab"] {{ 
        font-size: 16px; 
        font-weight: bold; 
        color: #888; 
        background-color: transparent; 
        border: 1px solid {tema['border']};
        border-radius: 20px;
        padding: 8px 20px;
    }}
    .stTabs [aria-selected="true"] {{ 
        color: white !important; 
        background-color: #00BFFF; 
        border-color: #00BFFF;
    }}

    /* Görsel Konteyner */
    .image-container {{
        border: 1px solid {tema['border']};
        border-radius: 12px;
        padding: 10px;
        background-color: {tema['card_bg']};
        text-align: center;
        margin-bottom: 15px;
        display: flex;
        justify-content: center;
        align-items: center;
    }}
    
    /* Başlık ve Logo Alanı */
    .logo-header {{
        text-align: center;
        padding: 20px 0;
        margin-bottom: 20px;
    }}
    .logo-img {{
        max-width: 200px;
        margin-bottom: 10px;
    }}
    .app-title {{
        color: #00BFFF !important;
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }}
    .app-subtitle {{
        color: {tema['subtext']} !important;
        font-size: 1.1rem;
        font-weight: 300;
        margin-top: 5px;
    }}

    .footer {{ 
        position: fixed; 
        left: 0; 
        bottom: 0; 
        width: 100%; 
        background-color: {tema['bg']}; 
        color: {tema['subtext']}; 
        text-align: center; 
        padding: 10px; 
        font-size: 12px; 
        border-top: 1px solid {tema['border']}; 
        z-index: 999; 
    }}
    </style>
    """, unsafe_allow_html=True)

# --- OTURUM YÖNETİMİ ---
if 'sonuc_gorseli' not in st.session_state: st.session_state.sonuc_gorseli = None
if 'sonuc_format' not in st.session_state: st.session_state.sonuc_format = "PNG"

# --- İŞLEM HARİTASI ---
TEMA_LISTESI = {
    "🧹 Arka Planı Kaldır (Şeffaf)": "ACTION_TRANSPARENT",
    "⬛ Düz Siyah Fon (Mat)": "ACTION_BLACK",
    "⬜ Düz Beyaz Fon": "ACTION_WHITE",
    "🍦 Krem / Bej Fon": "ACTION_BEIGE",
    "🏛️ Mermer Zemin (Lüks)": "Professional product photography, close-up shot of the object placed on a polished white carrara marble podium. Soft cinematic lighting, realistic shadows, depth of field, 8k resolution, luxury aesthetic.",
    "🪵 Ahşap Zemin (Doğal)": "Professional product photography, object placed on a textured rustic oak wooden table. Warm sunlight coming from the side, dappled shadows, blurred nature background, cozy atmosphere, photorealistic.",
    "🧱 Beton Zemin (Modern)": "Professional product photography, object placed on a raw grey concrete surface. Hard dramatic lighting, high contrast, sharp shadows, urban minimalist style, 8k.",
    "🛋️ İpek Kumaş (Zarif)": "Professional product photography, object resting on flowing champagne-colored silk fabric. Softbox lighting, elegant reflections, fashion magazine style, macro details.",
    "💡 Profesyonel Stüdyo": "High-end commercial product photography, object placed on an infinity curve background. Three-point lighting setup, rim light to separate object from background, ultra sharp focus.",
    "🌑 Karanlık Mod (Dark Studio)": "Professional product photography, object placed on a matte black non-reflective surface. Dark studio background, clean, dramatic rim lighting highlighting the object contours, minimal shadows, no reflections."
}

# --- FONKSİYONLAR ---
def resmi_hazirla(image):
    kare_resim = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    image.thumbnail((850, 850), Image.Resampling.LANCZOS) 
    x = (1024 - image.width) // 2
    y = (1024 - image.height) // 2
    kare_resim.paste(image, (x, y))
    return kare_resim

def bayt_cevir(image):
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()

def sahne_olustur(client, urun_resmi, prompt_text):
    # Hafıza dostu temizleme
    max_boyut = 1200
    if urun_resmi.width > max_boyut or urun_resmi.height > max_boyut:
        urun_resmi.thumbnail((max_boyut, max_boyut), Image.Resampling.LANCZOS)
    
    temiz_urun = remove(urun_resmi, alpha_matting=True, alpha_matting_foreground_threshold=240, alpha_matting_background_threshold=10)
    hazir_urun = resmi_hazirla(temiz_urun)
    maske_ham = hazir_urun.split()[3]
    maske_yumusak = maske_ham.filter(ImageFilter.GaussianBlur(radius=3))
    final_maske = Image.new("RGBA", hazir_urun.size, (0, 0, 0, 0))
    final_maske.putalpha(maske_yumusak)

    response = client.images.edit(
        image=("image.png", bayt_cevir(hazir_urun), "image/png"),
        mask=("mask.png", bayt_cevir(final_maske), "image/png"),
        prompt=prompt_text,
        n=1,
        size="1024x1024"
    )
    return response.data[0].url

def yerel_islem(urun_resmi, islem_tipi):
    max_boyut = 1200
    if urun_resmi.width > max_boyut or urun_resmi.height > max_boyut:
        urun_resmi.thumbnail((max_boyut, max_boyut), Image.Resampling.LANCZOS)

    temiz_urun = remove(urun_resmi, alpha_matting=True, alpha_matting_foreground_threshold=240, alpha_matting_background_threshold=10)
    if islem_tipi == "ACTION_TRANSPARENT": return temiz_urun
    renkler = {"ACTION_WHITE": (255, 255, 255), "ACTION_BLACK": (0, 0, 0), "ACTION_BEIGE": (245, 245, 220)}
    bg_color = renkler.get(islem_tipi, (255, 255, 255))
    bg = Image.new("RGB", temiz_urun.size, bg_color)
    bg.paste(temiz_urun, mask=temiz_urun)
    return bg

# --- ÖZEL BAŞLIK ALANI (Logo) ---
logo_html = ""
if os.path.exists("ALPTECHAI.png"):
    import base64
    with open("ALPTECHAI.png", "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
        logo_html = f'<img src="data:image/png;base64,{data}" class="logo-img">'

st.markdown(f"""
    <div class="logo-header">
        {logo_html}
        <h1 class="app-title">ALPTECH AI Stüdyo</h1>
        <p class="app-subtitle">Ürününü ekle, hayaline göre profesyonel bir şekilde düzenle.</p>
    </div>
    """, unsafe_allow_html=True)

# --- GİRİŞ SEKMELERİ ---
tab_yukle, tab_kamera = st.tabs(["📁 Dosya Yükle", "📷 Kamera"])
kaynak_dosya = None

with tab_yukle:
    uploaded_file = st.file_uploader("Ürün fotoğrafı", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
    if uploaded_file: kaynak_dosya = uploaded_file

with tab_kamera:
    camera_file = st.camera_input("Ürünü Çek")
    if camera_file: kaynak_dosya = camera_file

# --- İŞLEM ALANI ---
if kaynak_dosya:
    st.divider()
    col_orijinal, col_sag_panel = st.columns([1, 1], gap="medium")
    
    raw_image = Image.open(kaynak_dosya).convert("RGBA")
    raw_image = ImageOps.exif_transpose(raw_image)
    
    # SOL: ORİJİNAL
    with col_orijinal:
        st.markdown('<div class="container-header">📦 Orijinal Fotoğraf</div>', unsafe_allow_html=True)
        with st.container():
            st.markdown('<div class="image-container">', unsafe_allow_html=True)
            st.image(raw_image, width=300)
            st.markdown('</div>', unsafe_allow_html=True)

    # SAĞ: PANEL
    with col_sag_panel:
        if st.session_state.sonuc_gorseli is None:
            st.markdown('<div class="container-header">✨ Düzenleme Modu</div>', unsafe_allow_html=True)
            
            tab_hazir, tab_serbest = st.tabs(["🎨 Hazır Temalar", "✏️ Serbest Yazım"])
            final_prompt = None
            islem_tipi_local = None 
            
            with tab_hazir:
                secilen_tema = st.selectbox("Ortam Seçiniz:", list(TEMA_LISTESI.keys()))
                if secilen_tema:
                    kod = TEMA_LISTESI[secilen_tema]
                    if kod.startswith("ACTION_"): islem_tipi_local = kod
                    else: final_prompt = kod

            with tab_serbest:
                user_input = st.text_area("Hayalinizdeki sahneyi yazın:", placeholder="Örn: Volkanik taşların üzerinde...", height=100)
                if user_input:
                    final_prompt = f"Professional product photography shot of the object. {user_input}. High quality, realistic lighting, 8k."
            
            st.write("")
            buton_placeholder = st.empty()
            if buton_placeholder.button("🚀 İşlemi Başlat", type="primary"):
                try:
                    if islem_tipi_local:
                        with st.spinner("Hızlı işleniyor..."):
                            sonuc = yerel_islem(raw_image, islem_tipi_local)
                            buf = BytesIO()
                            fmt = "PNG" if islem_tipi_local == "ACTION_TRANSPARENT" else "JPEG"
                            sonuc.save(buf, format=fmt)
                            st.session_state.sonuc_gorseli = buf.getvalue()
                            st.session_state.sonuc_format = fmt
                            st.rerun()
                    elif final_prompt:
                        client = OpenAI(api_key=SABIT_API_KEY)
                        with st.spinner("Stüdyo hazırlanıyor (10-15sn)... 🎨"):
                            url = sahne_olustur(client, raw_image, final_prompt)
                            resp = requests.get(url)
                            st.session_state.sonuc_gorseli = resp.content
                            st.session_state.sonuc_format = "PNG"
                            st.rerun()
                    else:
                        st.warning("Lütfen bir tema seçin veya yazı yazın.")
                except Exception as e:
                    st.error(f"Hata: {e}")
                    buton_placeholder.button("🚀 Tekrar Dene", type="primary")

        else:
            st.markdown('<div class="container-header">✨ Sonuç</div>', unsafe_allow_html=True)
            with st.container():
                st.markdown('<div class="image-container">', unsafe_allow_html=True)
                st.image(st.session_state.sonuc_gorseli, width=350)
                st.markdown('</div>', unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                with st.expander("👁️ Büyüt"):
                    st.image(st.session_state.sonuc_gorseli, use_container_width=True)
            with c2:
                st.download_button(
                    label=f"📥 İndir ({st.session_state.sonuc_format})",
                    data=st.session_state.sonuc_gorseli,
                    file_name=f"alptech_pro.{st.session_state.sonuc_format.lower()}",
                    mime=f"image/{st.session_state.sonuc_format.lower()}",
                    type="primary",
                    use_container_width=True
                )
            
            st.write("")
            if st.button("🔄 Yeni İşlem Yap"):
                st.session_state.sonuc_gorseli = None
                st.rerun()

# Footer
st.markdown("<div class='footer'>ALPTECH AI Stüdyo © 2025 | Developed by Alper</div>", unsafe_allow_html=True)
