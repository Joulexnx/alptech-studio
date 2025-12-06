import streamlit as st
from rembg import remove
from PIL import Image, ImageOps, ImageFilter
from io import BytesIO
from openai import OpenAI
import requests
import os
from datetime import datetime
import json
import base64

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
st.set_page_config(page_title="ALPTECH AI Stüdyo", page_icon="🤖", layout="wide", initial_sidebar_state="collapsed")

# --- TEMA MANTIĞI ---
col_bosluk, col_tema = st.columns([10, 1]) 
with col_tema:
    karanlik_mod = st.toggle("🌙 / ☀️", value=True, key="theme_toggle") 

if karanlik_mod:
    tema = {
        "bg": "#0e1117", "text": "#ffffff", "subtext": "#b0b0b0", "card_bg": "#161616", "border": "#333333",
        "accent": "#00BFFF", "button_hover": "#009ACD", "input_bg": "#262730"
    }
else:
    tema = {
        "bg": "#f0f2f6", "text": "#262730", "subtext": "#555555", "card_bg": "#ffffff", "border": "#cccccc",
        "accent": "#0078D4", "button_hover": "#0062A3", "input_bg": "#ffffff"
    }

# --- TASARIM (DİNAMİK CSS) ---
st.markdown(f"""
    <style>
    /* --- GENEL SAYFA VE GİZLEME --- */
    .stApp {{ background-color: {tema['bg']}; }}
    .block-container {{ padding-top: 1.5rem; padding-bottom: 5rem; padding-left: 1rem; padding-right: 1rem; }}
    #MainMenu, footer, header, [data-testid="stToolbar"], [data-testid="stSidebar"] {{visibility: hidden !important;}}
    h1, h2, h3, h4, p, li, span, div, label, .stMarkdown, .stText {{ color: {tema['text']} !important; }}
    .stButton>button {{ background-color: {tema['accent']} !important; color: white !important;}}
    .stTextArea textarea {{ background-color: {tema['input_bg']} !important; color: {tema['text']} !important; border: 1px solid {tema['border']} !important; }}
    div[data-baseweb="select"] > div {{ background-color: {tema['input_bg']} !important; color: {tema['text']} !important; border-color: {tema['border']} !important; }}
    div[data-baseweb="popover"] div[role="listbox"] div[role="option"] {{ color: {tema['text']} !important; }}
    
    /* CHAT ORTALAMA (SOL HİZALI) */
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p, [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] div {{
        text-align: left !important;
        width: 100%;
    }}

    .image-container {{ border: 1px solid {tema['border']}; border-radius: 12px; padding: 10px; background-color: {tema['card_bg']} !important; }}
    .container-header {{ color: {tema['accent']} !important; }}
    
    /* --- FOOTER --- */
    .custom-footer {{ 
        position: fixed; left: 0; bottom: 0; width: 100%; 
        background-color: {tema['bg']}; color: {tema['subtext']}; 
        text-align: center; padding: 10px; font-size: 12px; 
        border-top: 1px solid {tema['border']}; z-index: 999;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- OTURUM YÖNETİMİ ---
if 'sonuc_gorseli' not in st.session_state: st.session_state.sonuc_gorseli = None
if 'sonuc_format' not in st.session_state: st.session_state.sonuc_format = "PNG"
if 'chat_history' not in st.session_state: 
    st.session_state.chat_history = [{"role": "assistant", "content": "Merhaba! Hangi modu kullanmak istersin?"}]
if 'app_mode' not in st.session_state: st.session_state.app_mode = "📸 Stüdyo Modu (Görsel Düzenleme)"

# --- İŞLEM HARİTASI (Kısaltıldı) ---
TEMA_LISTESI = {
    "🧹 Arka Planı Kaldır (Şeffaf)": "ACTION_TRANSPARENT", "⬛ Düz Siyah Fon (Mat)": "ACTION_BLACK", "⬜ Düz Beyaz Fon": "ACTION_WHITE", "🍦 Krem / Bej Fon": "ACTION_BEIGE",
    "🏛️ Mermer Zemin (Lüks)": "Professional product photography, close-up shot of the object placed on a polished white carrara marble podium. Soft cinematic lighting, realistic shadows, depth of field, 8k resolution, luxury aesthetic.",
    "🪵 Ahşap Zemin (Doğal)": "Professional product photography, object placed on a textured rustic oak wooden table. Warm sunlight coming from the side, dappled shadows, blurred nature background, cozy atmosphere, photorealistic.",
    "🧱 Beton Zemin (Modern)": "Professional product photography, object placed on a raw grey concrete surface. Hard dramatic lighting, high contrast, sharp shadows, urban minimalist style, 8k.",
    "🛋️ İpek Kumaş (Zarif)": "Professional product photography, object resting on flowing champagne-colored silk fabric. Softbox lighting, elegant reflections, fashion magazine style, macro details.",
    "💡 Profesyonel Stüdyo": "High-end commercial product photography, object placed on an infinity curve background. Three-point lighting setup, rim light to separate object from background, ultra sharp focus.",
    "🌑 Karanlık Mod (Dark Studio)": "Professional product photography, object placed on a matte black non-reflective surface. Dark studio background, clean, dramatic rim lighting highlighting the object contours, minimal shadows, no reflections."
}

# --- FONKSİYONLAR (GÜÇLENDİRİLDİ) ---
def turkce_zaman_getir():
    simdi = datetime.now()
    gunler = {0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"}
    aylar = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}
    return f"{simdi.day} {aylar[simdi.month]} {simdi.year}, {gunler[simdi.weekday()]}, Saat {simdi.strftime('%H:%M')}"

def normal_sohbet(client, chat_history):
    """Chat geçmişini kullanarak daha insancıl ve kapsamlı cevaplar verir."""
    zaman_bilgisi = turkce_zaman_getir()
    
    # 🌟 GÜNCELLENEN SİSTEM TALİMATI (Kapsamlı hale getirildi)
    system_talimati = f"""
    SENİN ROLÜN: ALPTECH AI'ın yüksek seviyeli, Türkçe konuşan, esprili ve son derece yetenekli ana asistanısın. Müşterinin tüm yaratıcı, profesyonel ve bilgiye dayalı ihtiyaçlarını karşıla.
    
    KAPSAMLI YETENEKLER:
    1.  Yaratıcı Üretim: Şarkı, şiir, makale taslağı ve profesyonel e-posta gibi uzun metinleri istenilen formatta ve yapıda (Verse, Nakarat vb.) detaylıca yaz.
    2.  Dil Uzmanlığı: Kullanıcının sunduğu herhangi bir metni (cümle, paragraf, mail taslağı) dilbilgisi, yazım hataları ve akıcılık açısından kontrol et ve düzelt.
    3.  Derinlemesine Bilgi: Karmaşık sorulara kısa cevaplar yerine doyurucu açıklamalar sun.

    KONUŞMA KURALLARI:
    1.  Samimiyet: Cana yakın, pozitif ve doğal bir sohbet akışı yakala. Emoji kullan.
    2.  Tekrarı Önleme: 'Size nasıl yardımcı olabilirim?' gibi robotik ifadeler KULLANMA.
    3.  Selamlama: Selamlara kısa ve samimi karşılık ver (Örn: "Selam! 👋" veya "Merhaba! 😊"), sohbeti kullanıcıya bırak.
    4.  Zaman Bilgisi: Sistemi zaman bilgisi: {zaman_bilgisi}. Bu bilgiyi sadece kullanıcı sorduğunda kullan.
    
    Cevaplarının uzunluğunu ve detayını, isteğin kapsamına göre ayarla (Mail/Şarkı istenirse uzun, soru istenirse net ol).
    """
    
    messages = [{"role": "system", "content": system_talimati}]
    
    for msg in chat_history[-10:]:
        api_role = "user" if msg["role"] == "user" else "assistant"
        messages.append({"role": api_role, "content": msg["content"]})
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        return "Üzgünüm, şu an bağlantımda bir sorun var veya çok fazla deneme yaptınız."

# GÖRSEL İŞLEM FONKSİYONLARI (kısaltıldı)
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


# --- ANA KOD GÖVDESİ ---

with col_baslik:
    st.markdown(f'<h1 class="app-title">ALPTECH AI Stüdyo</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="app-subtitle">Ürününü ekle, hayaline göre profesyonel bir şekilde düzenle.</p>', unsafe_allow_html=True)

with col_toggle:
    st.markdown('<div style="padding-top: 15px;"></div>', unsafe_allow_html=True)
    st.toggle("🌙 / ☀️", value=True, key="theme_toggle")

st.write("") 

# --- MOD SEÇİMİ (Butonlu Yöntem) ---
col_studio, col_chat = st.columns([1, 1], gap="small")

is_studio_active = st.session_state.app_mode == "📸 Stüdyo Modu (Görsel Düzenleme)"
is_chat_active = st.session_state.app_mode == "💬 Sohbet Modu (Genel Asistan)"

with col_studio:
    if st.button(
        "📸 Stüdyo Modu (Görsel Düzenleme)", 
        key="btn_studio", 
        use_container_width=True, 
        type="primary" if is_studio_active else "secondary"
    ):
        st.session_state.app_mode = "📸 Stüdyo Modu (Görsel Düzenleme)"
        st.session_state.sonuc_gorseli = None
        st.rerun()

with col_chat:
    if st.button(
        "💬 Sohbet Modu (Genel Asistan)", 
        key="btn_chat", 
        use_container_width=True, 
        type="primary" if is_chat_active else "secondary"
    ):
        st.session_state.app_mode = "💬 Sohbet Modu (Genel Asistan)"
        st.session_state.sonuc_gorseli = None
        st.rerun()

st.divider()

if st.session_state.app_mode == "📸 Stüdyo Modu (Görsel Düzenleme)":
    # --- STÜDYO MODU KODLARI ---
    tab_yukle, tab_kamera = st.tabs(["📁 Dosya Yükle", "📷 Kamera"])
    kaynak_dosya = None
    with tab_yukle:
        uploaded_file = st.file_uploader("Ürün fotoğrafı", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
        if uploaded_file: kaynak_dosya = uploaded_file
    with tab_kamera:
        camera_file = st.camera_input("Ürünü Çek")
        if camera_file: kaynak_dosya = camera_file

    if kaynak_dosya:
        col_orijinal, col_sag_panel = st.columns([1, 1], gap="medium")
        
        raw_image = Image.open(kaynak_dosya).convert("RGBA")
        raw_image = ImageOps.exif_transpose(raw_image)
        
        with col_orijinal:
            st.markdown('<div class="container-header">📦 Orijinal Fotoğraf</div>', unsafe_allow_html=True)
            with st.container():
                st.markdown('<div class="image-container">', unsafe_allow_html=True)
                st.image(raw_image, width=300)
                st.markdown('</div>', unsafe_allow_html=True)

        with col_sag_panel:
            if st.session_state.sonuc_gorseli is None:
                st.markdown('<div class="container-header">✨ Düzenleme Modu</div>', unsafe_allow_html=True)
                
                tab_hazir, tab_serbest = st.tabs(["🎨 Hazır Temalar", "✏️ Serbest Yazım"])
                final_prompt = None
                islem_tipi_local = None 
                
                with tab_hazir:
                    secilen_tema_input = st.selectbox("Ortam Seçiniz:", list(TEMA_LISTESI.keys()))
                    if secilen_tema_input:
                        kod = TEMA_LISTESI[secilen_tema_input]
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

elif st.session_state.app_mode == "💬 Sohbet Modu (Genel Asistan)":
    # --- CHAT MODU KODLARI ---
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Mesaj yazın..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("ALPTECH yazıyor..."):
                client = OpenAI(api_key=SABIT_API_KEY)
                cevap = normal_sohbet(client, st.session_state.chat_history)
                st.write(cevap)
                st.session_state.chat_history.append({"role": "assistant", "content": cevap})

# Footer
st.markdown("<div class='custom-footer'>ALPTECH AI Stüdyo © 2025 | Developed by Alper</div>", unsafe_allow_html=True)
