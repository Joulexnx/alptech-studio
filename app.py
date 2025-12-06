"""
File: app.py
ALPTECH AI Stüdyo — Apple-style full single-file revision
- Mantık: Orijinal akış korunmuştur (Studio + Chat).
- Görünüm: Apple-like (glassmorphism, SF font, rounded cards).
- Gereksinimler:
    pip install streamlit rembg pillow openai requests
- Kullanım:
    - st.secrets["OPENAI_API_KEY"] ekleyin.
    - (Opsiyonel) st.secrets["OPENAI_MODEL"] = "gpt-4o-mini" vb.
"""
from __future__ import annotations

import traceback
from datetime import datetime
from io import BytesIO

import requests
import streamlit as st
from openai import OpenAI
from PIL import Image, ImageOps, ImageFilter
from rembg import remove

# ----------------------------
# GÜVENLİ AYARLAR & KONFIG
# ----------------------------
if "OPENAI_API_KEY" in st.secrets:
    SABIT_API_KEY = st.secrets["OPENAI_API_KEY"]
else:
    st.error("🚨 OPENAI_API_KEY bulunamadı! Lütfen st.secrets içine ekleyin.")
    st.stop()

DEFAULT_MODEL = st.secrets.get("OPENAI_MODEL", "gpt-4o-mini")

st.set_page_config(
    page_title="ALPTECH AI Stüdyo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ----------------------------
# THEME (Light / Dark) — Apple Style Paletleri
# ----------------------------
def get_theme(is_dark: bool):
    if is_dark:
        return {
            "bg": "#0b0b0c",
            "card_bg": "rgba(255,255,255,0.04)",
            "text": "#e8eef6",
            "subtext": "#b9c6d6",
            "accent": "#0a84ff",
            "button_hover": "#0066cc",
            "border": "rgba(255,255,255,0.08)",
            "input_bg": "rgba(255,255,255,0.03)",
        }
    else:
        return {
            "bg": "#f6f7f9",
            "card_bg": "rgba(255,255,255,0.7)",
            "text": "#0b1220",
            "subtext": "#596274",
            "accent": "#007aff",
            "button_hover": "#0061d5",
            "border": "rgba(12,17,25,0.06)",
            "input_bg": "rgba(255,255,255,0.9)",
        }

# ----------------------------
# APPLE STYLE CSS
# ----------------------------
def apply_apple_css(tema: dict):
    st.markdown(
        f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    body, html, .stApp {{
        font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background: {tema['bg']};
        color: {tema['text']};
    }}
    #MainMenu, footer, header, [data-testid="stToolbar"], [data-testid="stSidebar"] {{
        visibility: hidden !important;
    }}
    .block-container {{ padding-top: 1rem; padding-bottom: 4rem; max-width: 1280px; }}
    .image-container {{
        background: {tema['card_bg']};
        backdrop-filter: blur(14px) saturate(120%);
        border-radius: 18px;
        padding: 14px;
        border: 1px solid {tema['border']};
        box-shadow: 0 6px 24px rgba(2,6,23,0.12);
    }}
    .container-header {{ color: {tema['accent']} !important; font-weight: 600; font-size: 1.05rem; margin-bottom: 6px; }}
    .stButton>button {{
        background-color: {tema['accent']} !important;
        color: white !important;
        border-radius: 12px !important;
        padding: 9px 16px !important;
        border: none !important;
        font-weight: 600 !important;
        box-shadow: 0 6px 18px rgba(10,10,20,0.12);
        transition: transform 120ms ease, box-shadow 120ms ease;
    }}
    .stButton>button:hover {{
        background-color: {tema['button_hover']} !important;
        transform: translateY(-2px);
    }}
    .stTextArea textarea, input[type="text"], textarea, .css-1r6slb0, .stTextInput>div>div>input {{
        background: {tema['input_bg']} !important;
        border-radius: 12px !important;
        border: 1px solid {tema['border']} !important;
        padding: 10px !important;
        color: {tema['text']} !important;
    }}
    [data-testid="stChatMessage"] {{
        border-radius: 16px;
        padding: 6px 12px;
        backdrop-filter: blur(12px);
        margin-bottom: 10px;
    }}
    .custom-footer {{
        position: fixed; left: 0; bottom: 0; width: 100%;
        background: rgba(255,255,255,0.02);
        backdrop-filter: blur(10px);
        color: {tema['subtext']}; text-align: center; padding: 10px; font-size: 12px;
        border-top: 1px solid {tema['border']};
    }}
    </style>
    """,
        unsafe_allow_html=True,
    )

# ----------------------------
# SESSION STATE INIT
# ----------------------------
if "sonuc_gorseli" not in st.session_state:
    st.session_state.sonuc_gorseli = None
if "sonuc_format" not in st.session_state:
    st.session_state.sonuc_format = "PNG"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Merhaba! Hangi modu kullanmak istersin?"}
    ]
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "📸 Stüdyo Modu (Görsel Düzenleme)"

# ----------------------------
# TEMA LISTESI (korundu)
# ----------------------------
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
    "🌑 Karanlık Mod (Dark Studio)": "Professional product photography, object placed on a matte black non-reflective surface. Dark studio background, clean, dramatic rim lighting highlighting the object contours, minimal shadows, no reflections.",
}

# ----------------------------
# UTIL FUNCTIONS
# ----------------------------
def turkce_zaman_getir():
    simdi = datetime.now()
    gunler = {
        0: "Pazartesi",
        1: "Salı",
        2: "Çarşamba",
        3: "Perşembe",
        4: "Cuma",
        5: "Cumartesi",
        6: "Pazar",
    }
    aylar = {
        1: "Ocak",
        2: "Şubat",
        3: "Mart",
        4: "Nisan",
        5: "Mayıs",
        6: "Haziran",
        7: "Temmuz",
        8: "Ağustos",
        9: "Eylül",
        10: "Ekim",
        11: "Kasım",
        12: "Aralık",
    }
    return f"{simdi.day} {aylar[simdi.month]} {simdi.year}, {gunler[simdi.weekday()]}, Saat {simdi.strftime('%H:%M')}"

def custom_identity_interceptor(user_message: str) -> str | None:
    """
    Marka kimliği: 'Seni kim yaptı?' vb. sorularda ALPTECH AI cevabını zorlar.
    """
    triggers = [
        "seni kim yaptı",
        "seni kim yarattı",
        "kim geliştirdi",
        "kimsin",
        "sen kimsin",
        "who created you",
        "who made you",
        "who built you",
        "who are you",
    ]
    msg = user_message.lower().strip()
    if any(t in msg for t in triggers):
        return (
            "Beni **ALPTECH AI** ekibi geliştirdi 🚀\n\n"
            "Ben de senin için tasarlanmış, üretkenliğini artıran ve işlerini hızlandıran "
            "akıllı bir asistanım. Beraber neler yapabileceğimizi keşfetmeye hazırım. 😊"
        )
    return None

def build_system_talimati():
    zaman_bilgisi = turkce_zaman_getir()
    system_talimati = f"""
    Senin adın **ALPTECH AI**.
    ALPTECH AI ekibi tarafından geliştirilen, modern ve profesyonel bir yapay zeka asistansın.

    Kimliğin ve marka duruşun:
    - Her zaman kendini "ALPTECH AI" olarak tanıt.
    - Seni kimin geliştirdiği sorulduğunda: "ALPTECH AI ekibi" de.
    - OpenAI veya başka şirket isimlerinden bahsetme; arka plandaki teknolojiyi açıklama.
    - Türkçe varsayılan dilin olsun; kullanıcı farklı dilde yazarsa aynı dilde devam et.

    Konuşma tarzın:
    - Samimi ama profesyonelsin; gereksiz uzatma, net ve anlaşılır ol.
    - Emojileri ölçülü kullan (çok değil, tamamen de sıfır değil).
    - Teknik konularda adım adım, sakin ve açıklayıcı davran.
    - Aynı cümle kalıplarını tekrar etmemeye dikkat et.

    Uzmanlıkların:
    - Metin üretimi (blog, açıklama, açıklayıcı metinler, sosyal medya yazıları).
    - Görsel düzenleme süreçlerinde rehberlik (özellikle ürün fotoğrafçılığı bağlamında).
    - Kullanıcının işini hızlandıracak kısa komutlar, özetler ve pratik çözümler sunmak.

    Sistem notu: Bu yanıtlar {zaman_bilgisi} tarihinde oluşturuluyor.
    """
    return system_talimati

def normal_sohbet(client, chat_history):
    """API'ye iletilen chat geçmişini hazırlar ve çağırır."""
    system_talimati = build_system_talimati()
    max_context = 40
    messages = [{"role": "system", "content": system_talimati}]
    for msg in st.session_state.chat_history[-max_context:]:
        api_role = "user" if msg["role"] == "user" else "assistant"
        messages.append({"role": api_role, "content": msg["content"]})
    model_to_use = st.secrets.get("OPENAI_MODEL", DEFAULT_MODEL)
    try:
        response = client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            temperature=0.2,
            max_tokens=1200,
        )
        try:
            return response.choices[0].message.content
        except Exception:
            return response.choices[0].text
    except Exception as e:
        tb = traceback.format_exc()
        st.error("⚠️ Sohbet API çağrısında hata. Konsolu kontrol ediniz.")
        print("Chat API HATA:", e, tb)
        return "Üzgünüm, sohbet hizmetinde şu an bir sorun var."

# ----------------------------
# GÖRSEL İŞLEME
# ----------------------------
def resmi_hazirla(image: Image.Image):
    kare_resim = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    image.thumbnail((850, 850), Image.Resampling.LANCZOS)
    x = (1024 - image.width) // 2
    y = (1024 - image.height) // 2
    kare_resim.paste(image, (x, y), image if image.mode == "RGBA" else None)
    return kare_resim

def bayt_cevir(image: Image.Image):
    buf = BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def sahne_olustur(client, urun_resmi: Image.Image, prompt_text: str):
    """OpenAI images.edit çağrısı (hata durumunda None döner)."""
    try:
        max_boyut = 1200
        if urun_resmi.width > max_boyut or urun_resmi.height > max_boyut:
            urun_resmi.thumbnail((max_boyut, max_boyut), Image.Resampling.LANCZOS)

        try:
            temiz_urun = remove(
                urun_resmi,
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
            )
        except Exception:
            temiz_urun = urun_resmi.convert("RGBA")

        hazir_urun = resmi_hazirla(temiz_urun)
        if hazir_urun.mode != "RGBA":
            hazir_urun = hazir_urun.convert("RGBA")
        maske_ham = hazir_urun.split()[3]
        maske_yumusak = maske_ham.filter(ImageFilter.GaussianBlur(radius=3))
        final_maske = Image.new("RGBA", hazir_urun.size, (0, 0, 0, 0))
        final_maske.putalpha(maske_yumusak)

        response = client.images.edit(
            image=("image.png", bayt_cevir(hazir_urun), "image/png"),
            mask=("mask.png", bayt_cevir(final_maske), "image/png"),
            prompt=prompt_text,
            n=1,
            size="1024x1024",
        )
        try:
            return response.data[0].url
        except Exception:
            try:
                return response["data"][0]["url"]
            except Exception:
                return None
    except Exception as e:
        print("sahne_olustur hata:", e, traceback.format_exc())
        return None

def yerel_islem(urun_resmi: Image.Image, islem_tipi: str):
    max_boyut = 1200
    if urun_resmi.width > max_boyut or urun_resmi.height > max_boyut:
        urun_resmi.thumbnail((max_boyut, max_boyut), Image.Resampling.LANCZOS)

    try:
        temiz_urun = remove(
            urun_resmi,
            alpha_matting=True,
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10,
        )
    except Exception as e:
        print("rembg hata, orijinal resim kullanılıyor:", e)
        temiz_urun = urun_resmi

    if islem_tipi == "ACTION_TRANSPARENT":
        return temiz_urun
    renkler = {
        "ACTION_WHITE": (255, 255, 255),
        "ACTION_BLACK": (0, 0, 0),
        "ACTION_BEIGE": (245, 245, 220),
    }
    bg_color = renkler.get(islem_tipi, (255, 255, 255))
    bg = Image.new("RGB", temiz_urun.size, bg_color)
    bg.paste(temiz_urun, mask=temiz_urun if temiz_urun.mode in ("RGBA", "LA") else None)
    return bg

# ----------------------------
# UI — Başlık ve mod düğmeleri
# ----------------------------
st.title("ALPTECH AI Stüdyo")
st.write("Ürününü ekle, hayaline göre profesyonel bir şekilde düzenle.")

# Theme toggle + apply CSS (Apple style)
col_bosluk, col_tema = st.columns([10, 1])
with col_tema:
    karanlik_mod = st.toggle("🌙 / ☀️", value=True, key="theme_toggle")
tema = get_theme(karanlik_mod)
apply_apple_css(tema)

# Mode buttons
col_studio, col_chat = st.columns([1, 1], gap="small")

is_studio_active = st.session_state.app_mode == "📸 Stüdyo Modu (Görsel Düzenleme)"
is_chat_active = st.session_state.app_mode == "💬 Sohbet Modu (Genel Asistan)"

with col_studio:
    if st.button(
        "📸 Stüdyo Modu (Görsel Düzenleme)",
        key="btn_studio",
        use_container_width=True,
        type="primary" if is_studio_active else "secondary",
    ):
        st.session_state.app_mode = "📸 Stüdyo Modu (Görsel Düzenleme)"
        st.session_state.sonuc_gorseli = None
        st.rerun()

with col_chat:
    if st.button(
        "💬 Sohbet Modu (Genel Asistan)",
        key="btn_chat",
        use_container_width=True,
        type="primary" if is_chat_active else "secondary",
    ):
        st.session_state.app_mode = "💬 Sohbet Modu (Genel Asistan)"
        st.session_state.sonuc_gorseli = None
        st.rerun()

st.divider()

# ----------------------------
# STUDIO MODE
# ----------------------------
if st.session_state.app_mode == "📸 Stüdyo Modu (Görsel Düzenleme)":
    tab_yukle, tab_kamera = st.tabs(["📁 Dosya Yükle", "📷 Kamera"])
    kaynak_dosya = None
    with tab_yukle:
        uploaded_file = st.file_uploader(
            "Ürün fotoğrafı", type=["png", "jpg", "jpeg"], label_visibility="collapsed"
        )
        if uploaded_file:
            kaynak_dosya = uploaded_file
    with tab_kamera:
        camera_file = st.camera_input("Ürünü Çek")
        if camera_file:
            kaynak_dosya = camera_file

    if kaynak_dosya:
        col_orijinal, col_sag_panel = st.columns([1, 1], gap="medium")

        try:
            raw_image = Image.open(kaynak_dosya)
            raw_image = ImageOps.exif_transpose(raw_image).convert("RGBA")
        except Exception as e:
            st.error("Görsel açılamadı. Lütfen farklı bir dosya deneyin.")
            print("image open error:", e, traceback.format_exc())
            raw_image = None

        if raw_image:
            with col_orijinal:
                st.markdown(
                    '<div class="container-header">📦 Orijinal Fotoğraf</div>',
                    unsafe_allow_html=True,
                )
                with st.container():
                    st.markdown('<div class="image-container">', unsafe_allow_html=True)
                    st.image(raw_image, width=300)
                    st.markdown("</div>", unsafe_allow_html=True)

            with col_sag_panel:
                if st.session_state.sonuc_gorseli is None:
                    st.markdown(
                        '<div class="container-header">✨ Düzenleme Modu</div>',
                        unsafe_allow_html=True,
                    )

                    tab_hazir, tab_serbest = st.tabs(
                        ["🎨 Hazır Temalar", "✏️ Serbest Yazım"]
                    )
                    final_prompt = None
                    islem_tipi_local = None

                    with tab_hazir:
                        secilen_tema_input = st.selectbox(
                            "Ortam Seçiniz:", list(TEMA_LISTESI.keys())
                        )
                        if secilen_tema_input:
                            kod = TEMA_LISTESI[secilen_tema_input]
                            if isinstance(kod, str) and kod.startswith("ACTION_"):
                                islem_tipi_local = kod
                            else:
                                final_prompt = kod

                    with tab_serbest:
                        user_input = st.text_area(
                            "Hayalinizdeki sahneyi yazın:",
                            placeholder="Örn: Volkanik taşların üzerinde...",
                            height=100,
                        )
                        if user_input:
                            final_prompt = (
                                "Professional product photography shot of the object. "
                                f"{user_input}. High quality, realistic lighting, 8k, photorealistic."
                            )

                    st.write("")
                    buton_placeholder = st.empty()
                    if buton_placeholder.button("🚀 İşlemi Başlat", type="primary"):
                        try:
                            if islem_tipi_local:
                                with st.spinner("Hızlı işleniyor..."):
                                    sonuc = yerel_islem(raw_image, islem_tipi_local)
                                    buf = BytesIO()
                                    fmt = (
                                        "PNG"
                                        if islem_tipi_local == "ACTION_TRANSPARENT"
                                        else "JPEG"
                                    )
                                    sonuc.save(buf, format=fmt)
                                    st.session_state.sonuc_gorseli = buf.getvalue()
                                    st.session_state.sonuc_format = fmt
                                    st.rerun()
                            elif final_prompt:
                                client = OpenAI(api_key=SABIT_API_KEY)
                                with st.spinner(
                                    "Stüdyo hazırlanıyor (10-30sn)... 🎨"
                                ):
                                    url = sahne_olustur(
                                        client, raw_image, final_prompt
                                    )
                                    if url:
                                        try:
                                            resp = requests.get(url, timeout=30)
                                            if resp.status_code == 200:
                                                st.session_state.sonuc_gorseli = (
                                                    resp.content
                                                )
                                                st.session_state.sonuc_format = "PNG"
                                                st.rerun()
                                            else:
                                                st.error(
                                                    f"Resim indirilemedi (HTTP {resp.status_code})."
                                                )
                                        except Exception as e:
                                            st.error(
                                                "Sonuç indirilemedi. Lütfen tekrar deneyin."
                                            )
                                            print(
                                                "resim indir hata:",
                                                e,
                                                traceback.format_exc(),
                                            )
                                    else:
                                        st.error(
                                            "AI görsel düzenlemesi başarısız oldu."
                                        )
                            else:
                                st.warning("Lütfen bir tema seçin veya yazı yazın.")
                        except Exception as e:
                            st.error(f"Hata: {e}")
                            print(
                                "İşlem başlat hata:",
                                traceback.format_exc(),
                            )
                            buton_placeholder.button(
                                "🚀 Tekrar Dene", type="primary"
                            )
                else:
                    st.markdown(
                        '<div class="container-header">✨ Sonuç</div>',
                        unsafe_allow_html=True,
                    )
                    with st.container():
                        st.markdown('<div class="image-container">', unsafe_allow_html=True)
                        st.image(st.session_state.sonuc_gorseli, width=350)
                        st.markdown("</div>", unsafe_allow_html=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        with st.expander("👁️ Büyüt"):
                            st.image(
                                st.session_state.sonuc_gorseli, use_container_width=True
                            )
                    with c2:
                        if isinstance(
                            st.session_state.sonuc_gorseli, (bytes, bytearray)
                        ):
                            st.download_button(
                                label=f"📥 İndir ({st.session_state.sonuc_format})",
                                data=st.session_state.sonuc_gorseli,
                                file_name=f"alptech_pro.{st.session_state.sonuc_format.lower()}",
                                mime=f"image/{st.session_state.sonuc_format.lower()}",
                                use_container_width=True,
                            )
                        else:
                            try:
                                resp = requests.get(
                                    st.session_state.sonuc_gorseli, timeout=30
                                )
                                if resp.status_code == 200:
                                    st.download_button(
                                        label="📥 İndir (PNG)",
                                        data=resp.content,
                                        file_name="alptech_pro.png",
                                        mime="image/png",
                                        use_container_width=True,
                                    )
                                else:
                                    st.warning("İndirilebilir sonuç bulunamadı.")
                            except Exception as e:
                                st.warning("İndirilebilir sonuç alınamadı.")
                                print(
                                    "download fallback hata:",
                                    e,
                                    traceback.format_exc(),
                                )

                    st.write("")
                    if st.button("🔄 Yeni İşlem Yap"):
                        st.session_state.sonuc_gorseli = None
                        st.rerun()

# ----------------------------
# CHAT MODE
# ----------------------------
elif st.session_state.app_mode == "💬 Sohbet Modu (Genel Asistan)":
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Mesaj yazın..."):
        # Kullanıcı mesajını önce göster + history'e yaz
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Kimlik interceptor: "Seni kim yaptı?" vb. ise burada cevap ver, API'ye gitme
        override = custom_identity_interceptor(prompt)
        if override is not None:
            with st.chat_message("assistant"):
                st.write(override)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": override}
            )
        else:
            with st.chat_message("assistant"):
                with st.spinner("ALPTECH yazıyor..."):
                    client = OpenAI(api_key=SABIT_API_KEY)
                    cevap = normal_sohbet(client, st.session_state.chat_history)
                    st.write(cevap)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": cevap}
                    )

# ----------------------------
# FOOTER
# ----------------------------
st.markdown(
    "<div class='custom-footer'>ALPTECH AI Stüdyo © 2025 | Developed by Alper</div>",
    unsafe_allow_html=True,
)
