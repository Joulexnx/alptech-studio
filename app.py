# ==========================================================
# QELYON AI STÜDYO — v5.0
# Gemini Vision • Gemini 1.5 Flash/Pro • GPT-4o Hibrit Sistem
# ==========================================================

from __future__ import annotations

import base64
import io
import traceback
import re
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Literal, Optional

import streamlit as st
from PIL import Image, ImageOps
from google import generativeai as genai
from openai import OpenAI

from __future__ import annotations

import os
import io
import re
import base64
import traceback
from datetime import datetime
from io import BytesIO
from typing import Literal
from zoneinfo import ZoneInfo

import requests
import streamlit as st
from PIL import Image, ImageOps, ImageFilter, ImageChops, ImageDraw

# ==========================================================
# 🔐 SECRETS & API KEYS
# ==========================================================
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", None)

if not OPENAI_API_KEY:
    st.error("⚠️ OPENAI_API_KEY eksik. GPT tabanlı modlar çalışmayacaktır.")

if not GEMINI_API_KEY:
    st.error("⚠️ GEMINI_API_KEY eksik. Gemini tabanlı modlar çalışmayacaktır.")

# Varsayılan GPT modeli
GPT_MODEL = st.secrets.get("OPENAI_MODEL", "gpt-4o")

# Gemini modelleri
GEMINI_TEXT_MODEL = "gemini-1.5-pro"
GEMINI_VISION_MODEL = "gemini-1.5-flash"

# ==========================================================
# 🌍 WEATHER API
# ==========================================================
WEATHER_API_KEY = st.secrets.get(
    "WEATHER_API_KEY", "5f9ee20a060a62ba9cb79d4a048395d9"
)
DEFAULT_CITY = "İstanbul"

# ==========================================================
# 🎨 LOGO & FAVICON
# ==========================================================
LOGO_LIGHT = "QelyonAIblack.png"
LOGO_DARK = "QelyonAIwhite.png"
FAVICON = "favicn.png"

st.set_page_config(
    page_title="Qelyon AI Stüdyo",
    page_icon=FAVICON,
    layout="wide",
)

# ==========================================================
# 🎨 THEME ENGINE
# ==========================================================
def get_theme(is_dark: bool):
    accent = "#6C47FF"
    if is_dark:
        return {
            "bg": "#050509",
            "text": "#FFFFFF",
            "sub": "#A8A8A8",
            "input": "#111",
            "card": "rgba(255,255,255,0.05)",
            "border": "rgba(255,255,255,0.1)",
            "accent": accent,
        }
    else:
        return {
            "bg": "#F5F5FB",
            "text": "#0F172A",
            "sub": "#444",
            "input": "#fff",
            "card": "rgba(255,255,255,0.85)",
            "border": "rgba(0,0,0,0.1)",
            "accent": accent,
        }

def apply_theme_css(t):
    st.markdown(
        f"""
        <style>
        body, .stApp {{
            background: {t['bg']} !important;
            color: {t['text']} !important;
        }}
        .stTextInput>div>div>input,
        textarea {{
            background: {t['input']} !important;
            color: {t['text']} !important;
            border-radius: 12px !important;
            border: 1px solid {t['border']} !important;
        }}
        [data-testid="stChatMessage"] {{
            background: {t['card']};
            border: 1px solid {t['border']};
            border-radius: 14px;
            padding: 8px 12px;
            margin-bottom: 10px;
        }}
        .stButton>button {{
            background: {t['accent']} !important;
            border-radius: 999px !important;
            color: white !important;
            font-weight: 600 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# ==========================================================
# 🌙 / ☀️ Tema Seçici
# ==========================================================
col_t1, col_t2 = st.columns([10,1])
with col_t2:
    dark = st.toggle("🌙 / ☀️", value=True)

THEME = get_theme(dark)
apply_theme_css(THEME)

# ==========================================================
# 📌 Global Session Vars
# ==========================================================
if "mode" not in st.session_state:
    st.session_state.mode = "📸 Stüdyo Modu"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "uploaded_chat_image" not in st.session_state:
    st.session_state.uploaded_chat_image = None

if "studio_result" not in st.session_state:
    st.session_state.studio_result = None

# END OF A1
# ==========================================================
# A2 — API CLIENTS • GEMINI + GPT • UTILITY FONKSİYONLARI
# ==========================================================

# ---------------------------
# 🔥 Gemini Client (Google AI)
# ---------------------------
import google.generativeai as genai

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    genai.configure(api_key="")

def gemini_text(prompt: str):
    """Gemini 1.5 Pro ile metin üretimi"""
    try:
        model = genai.GenerativeModel(GEMINI_TEXT_MODEL)
        resp = model.generate_content(prompt)
        return resp.text
    except Exception as e:
        print("Gemini text error:", e)
        return "Gemini şu anda yanıt veremiyor."

def gemini_vision(prompt: str, image_bytes: bytes):
    """Gemini Vision ile görsel analizi"""
    try:
        img = {"mime_type": "image/png", "data": image_bytes}
        model = genai.GenerativeModel(GEMINI_VISION_MODEL)
        resp = model.generate_content([prompt, img])
        return resp.text
    except Exception as e:
        print("Gemini vision error:", e)
        return "Görsel analizinde bir hata oluştu."

def gemini_generate_image(prompt: str):
    """Gemini Image Flash ile görsel oluşturma"""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        img = model.generate_image(prompt=prompt, size="1024x1024")
        return img._image  # bytes
    except Exception as e:
        print("Gemini image error:", e)
        return None

# ---------------------------
# 🤖 GPT-4o Client
# ---------------------------
from openai import OpenAI
GPT = OpenAI(api_key=OPENAI_API_KEY)

def gpt_chat(messages: list[dict], model: str = GPT_MODEL):
    """GPT-4o tabanlı sohbet motoru"""
    try:
        res = GPT.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.25,
            max_tokens=1500,
        )
        return res.choices[0].message.content
    except Exception as e:
        print("GPT error:", e)
        return "Şu anda GPT ile bağlantı sağlanamıyor."

# ---------------------------
# ⚡ MODEL ROUTER
# ---------------------------
def model_router(mode: str):
    """
    Genel Chat = Gemini
    E-ticaret = GPT-4o
    Danışmanlık = GPT-4o
    """
    if mode == "general":
        return "gemini"
    if mode == "ecom":
        return "gpt"
    if mode == "consult":
        return "gpt"
    return "gemini"

# ==========================================================
# 📅 ZAMAN FONKSİYONLARI
# ==========================================================
def get_tr_time():
    try:
        r = requests.get("http://worldtimeapi.org/api/timezone/Europe/Istanbul")
        dt = r.json()["datetime"]
        return datetime.fromisoformat(dt)
    except:
        return datetime.now(ZoneInfo("Europe/Istanbul"))

def time_answer():
    now = get_tr_time()
    return f"Bugünün tarihi: {now.strftime('%d.%m.%Y')}, Saat: {now.strftime('%H:%M')}"

# ==========================================================
# 🌦 HAVA DURUMU SERVİSİ
# ==========================================================
def get_coords(city: str):
    try:
        url = (
            f"http://api.openweathermap.org/geo/1.0/direct?"
            f"q={city},TR&limit=1&appid={WEATHER_API_KEY}"
        )
        r = requests.get(url)
        data = r.json()
        if not data: return None
        return data[0]["lat"], data[0]["lon"]
    except:
        return None

def get_weather(city: str):
    coords = get_coords(city)
    if not coords:
        return f"{city} için konum bulunamadı."

    lat, lon = coords
    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather?"
            f"lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric&lang=tr"
        )
        r = requests.get(url)
        d = r.json()

        desc = d["weather"][0]["description"].capitalize()
        temp = d["main"]["temp"]
        hum = d["main"]["humidity"]
        wind = d["wind"]["speed"]

        return (
            f"📍 **{city.title()}**\n"
            f"🌡️ Sıcaklık: **{temp:.1f}°C**\n"
            f"☁️ Hava: **{desc}**\n"
            f"💧 Nem: **%{hum}**\n"
            f"🍃 Rüzgar: **{wind} m/s**"
        )
    except:
        return "Hava durumu alınamadı."

# ==========================================================
# 🛡 GÜVENLİK FİLTRESİ
# ==========================================================
BAD_WORDS = [
    r"(?i)orospu", r"(?i)siktir", r"(?i)amk",
    r"(?i)tecavüz", r"(?i)intihar", r"(?i)bomba yap",
]

def moderate_text(msg: str) -> str | None:
    for pat in BAD_WORDS:
        if re.search(pat, msg):
            return "Bu isteğe güvenlik nedeniyle yanıt veremiyorum. 🙏"
    return None
# ==========================================================
# A3 — STÜDYO MODU • GÖRSEL İŞLEME (GEMINI + LOCAL)
# ==========================================================

# ---------------------------------------
# 🧼 1) LOKAL ARKA PLAN KALDIRMA (HQ)
# ---------------------------------------
def remove_bg_local(image: Image.Image) -> Image.Image:
    """
    Lokal yüksek kalite maskeleme.
    Gemini Vision şu anda 'edit image' desteklemediği için
    keskin ve güvenilir bir yöntem kullanıyoruz.
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    # Alfa maskesi üret
    gray = image.convert("L")
    mask = gray.point(lambda p: 255 if p > 240 else 0)

    result = Image.new("RGBA", image.size)
    result.paste(image, (0, 0), mask)
    return result


# ---------------------------------------
# 🎛 2) ÜRÜNÜ KARE TUVALE YERLEŞTİRME
# ---------------------------------------
def center_on_canvas(img: Image.Image, size=1024) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img = img.copy()
    img.thumbnail((size * 0.85, size * 0.85), Image.Resampling.LANCZOS)

    x = (size - img.width) // 2
    y = (size - img.height) // 2
    canvas.paste(img, (x, y), img)
    return canvas


# ---------------------------------------
# 🌓 3) PROFESYONEL TEMAS GÖLGESİ
# ---------------------------------------
def make_contact_shadow(alpha: Image.Image, intensity=140):
    a = alpha.convert("L")
    box = a.getbbox()
    if not box:
        return Image.new("L", a.size, 0)

    w = box[2] - box[0]
    h = int((box[3] - box[1]) * 0.22)

    shadow = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(shadow)
    draw.ellipse([0, 0, w, h], fill=intensity)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=h // 2))

    mask = Image.new("L", a.size, 0)
    mask.paste(shadow, (box[0], box[3] - h // 2))
    return mask


# ---------------------------------------
# 🌫 4) HAFİF STÜDYO YANSIMA
# ---------------------------------------
def make_reflection(img: Image.Image, fade=220):
    a = img.split()[3]
    box = a.getbbox()
    if not box:
        return Image.new("RGBA", img.size, (0, 0, 0, 0))

    crop = img.crop(box)
    flip = ImageOps.flip(crop)

    grad = Image.linear_gradient("L").resize((1, flip.height))
    grad = grad.point(lambda p: int(p * (fade / 255)))
    grad = grad.resize(flip.size)

    flip.putalpha(grad)

    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(flip, (box[0], box[3] + 4), flip)
    return out


# ---------------------------------------
# 🎨 5) TEMA KOMPOZİT MOTORU
# ---------------------------------------
def compose_scene(cut: Image.Image, bg_color: str, reflection=True, shadow=True):
    side = 1024
    obj = center_on_canvas(cut, side)
    alpha = obj.split()[3]

    # Arka plan
    bg_colors = {
        "white": (255, 255, 255, 255),
        "black": (0, 0, 0, 255),
        "beige": (245, 240, 225, 255),
    }

    bg = Image.new("RGBA", (side, side), bg_colors.get(bg_color, (255, 255, 255, 255)))
    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.alpha_composite(bg)

    # Gölge
    if shadow:
        sh_mask = make_contact_shadow(alpha)
        sh = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        sh.putalpha(sh_mask)
        out.alpha_composite(sh)

    # Yansıma
    if reflection:
        ref = make_reflection(obj)
        out.alpha_composite(ref)

    # Ürün
    out.alpha_composite(obj)
    return out


# ---------------------------------------
# ✨ 6) GEMINI SAHNE OLUŞTURMA (AI)
# ---------------------------------------
def gemini_edit_scene(prompt: str, product_image: bytes):
    """
    Stüdyo modunda serbest sahne oluşturma:
    - Gemini Flash Image kullanır.
    - Ürün korunur, yalnızca arka plan AI tarafından yeniden çizilir.
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        img_dict = {
            "mime_type": "image/png",
            "data": product_image,
        }

        full_prompt = (
            "You are a professional product photographer. "
            "Replace only the background with a clean, elegant, commercial-grade scene. "
            "Do NOT modify the product shape, color or geometry. "
            f"Scene prompt: {prompt}"
        )

        result = model.generate_image(
            prompt=full_prompt,
            image=img_dict,
            size="1024x1024",
        )

        return result._image  # raw PNG bytes
    except Exception as e:
        print("Gemini Edit Scene Error:", e)
        return None


# ---------------------------------------
# 🏗 7) TEMALAR
# ---------------------------------------
PRESETS = {
    "🧹 Şeffaf Arka Plan": "transparent",
    "⬜ Beyaz Arka Plan": "white",
    "⬛ Siyah Arka Plan": "black",
    "🍦 Bej Arka Plan": "beige",
    "✨ Profesyonel Stüdyo": "pro",
}

def apply_preset(img: Image.Image, preset_name: str):
    """Hazır temayı uygular."""
    cut = remove_bg_local(img)

    if preset_name == "transparent":
        return cut

    if preset_name == "white":
        return compose_scene(cut, "white", reflection=False)

    if preset_name == "black":
        return compose_scene(cut, "black", reflection=False)

    if preset_name == "beige":
        return compose_scene(cut, "beige", reflection=False)

    if preset_name == "pro":
        return compose_scene(cut, "white", reflection=True)

    return cut
# ==========================================================
# A4 — GENEL CHAT MOTORU (GEMINI 1.5 PRO)
# ==========================================================

# ✔ Metin destekli
# ✔ Görsel destekli
# ✔ Görsel oluşturma yetenekleri
# ✔ GPT’den tamamen bağımsız çalışır (sadece Genel Chat için)

def gemini_general_chat(user_message: str, user_image: bytes | None):
    """
    Genel Chat Modu (💬) için Gemini 1.5 Pro tabanlı yanıt üretici.
    - Tek mesajlık değil, çoklu geçmişle birlikte çalışabilir.
    - Görsel analizi otomatik algılar.
    """

    try:
        history = []
        # Sohbet geçmişini Gemini formatına dönüştür
        for msg in st.session_state.chat_history[-20:]:
            if msg["role"] == "user":
                history.append({
                    "role": "user",
                    "parts": [msg["content"]]
                })
            else:
                history.append({
                    "role": "model",
                    "parts": [msg["content"]]
                })

        # Kullanıcının yeni mesajı & görseli
        user_parts = [{"text": user_message}]

        if user_image:
            user_parts.append({
                "inline_data": {
                    "mime_type": "image/png",
                    "data": base64.b64encode(user_image).decode("utf-8")
                }
            })

        # Gemini sohbet modeli
        model = genai.GenerativeModel("gemini-1.5-pro")

        chat_turn = {
            "role": "user",
            "parts": user_parts
        }

        full_messages = history + [chat_turn]

        response = model.generate_content(full_messages)

        if hasattr(response, "text"):
            return response.text
        return "Bir yanıt üretemedim."
    except Exception as e:
        print("Gemini Chat Error:", e)
        return "Üzgünüm, şu anda bir sorun oluştu. Daha sonra tekrar dene."


# ==========================================================
# A4 — GÖRSEL OLUŞTURMA MOTORU (Gemini Flash Image)
# ==========================================================

def gemini_generate_image(prompt: str, size: str = "1024x1024"):
    """
    Gemini Flash ile yüksek kaliteli görsel oluşturma.
    Genel Chat içinde:
        ➤ “Bir logo üret”
        ➤ “Bu ürünü plajda göster”
        ➤ “Minimalist arka plan resmi çiz”
    gibi istekleri karşılar.
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        result = model.generate_image(
            prompt=prompt,
            size=size,
        )

        return result._image  # PNG raw bytes
    except Exception as e:
        print("Gemini Generate Image Error:", e)
        return None


# ==========================================================
# A4 — GENEL CHATTE OTOMATİK ALGILAMA
# ==========================================================

def handle_general_chat(user_message: str):
    """
    Genel chat işleyici:
    - Kullanıcının görsel oluşturmak istediğini otomatik algılar.
    - Metin isteklerini Gemini 1.5 Pro’ya yönlendirir.
    """

    # Kullanıcı görsel oluşturmak istiyor mu?
    GEN_TRIGGER = [
        "görsel oluştur",
        "resim oluştur",
        "image create",
        "bir görsel çiz",
        "bana bir tasarım yap",
        "foto üret",
        "generate image"
    ]

    # 1) Eğer görsel üretim tetikleniyorsa → Gemini Flash çalışır
    if any(t in user_message.lower() for t in GEN_TRIGGER):
        with st.chat_message("assistant"):
            st.write("🎨 Görsel oluşturuluyor...")

        img_bytes = gemini_generate_image(user_message)

        if img_bytes:
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": "(Görsel oluşturuldu)"
            })

            st.image(img_bytes, caption="Gemini 1.5 Flash tarafından üretildi", width=350)
            return

        st.write("Görsel oluşturma başarısız oldu, lütfen tekrar dene.")
        return

    # 2) Normal metin/görsel analiz sohbeti
    output = gemini_general_chat(
        user_message,
        st.session_state.chat_image
    )

    with st.chat_message("assistant"):
        st.write(output)

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": output
    })
# ==========================================================
# A5 — GPT TABANLI E-TİCARET VE DANIŞMANLIK MOTORU
# ==========================================================

def gpt_assistant(profile: Literal["ecom", "consult"]):
    """
    GPT-4o tabanlı E-Ticaret ve Danışmanlık asistanı.
    Bu motor Genel Chat motorundan tamamen ayrı çalışır.
    """

    # ----- Sistem mesajı oluştur -----
    system_message = build_system_talimati(profile)

    # ----- Sohbet geçmişi -----
    history = []
    for msg in st.session_state.chat_history[-30:]:
        history.append({
            "role": "user" if msg["role"] == "user" else "assistant",
            "content": msg["content"]
        })

    # ----- GPT isteği -----
    try:
        client = OpenAI(api_key=SABIT_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                *history
            ],
            temperature=0.25,
            max_tokens=1400,
        )

        return response.choices[0].message.content

    except Exception as e:
        print("GPT-4o error:", e)

        # ----- Fallback: GPT-4o-mini -----
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    *history
                ],
                temperature=0.25,
                max_tokens=1200,
            )
            return response.choices[0].message.content

        except Exception as err:
            print("GPT fallback error:", err)
            return "Şu anda bir problem oluştu. Lütfen tekrar dener misin?"



# ==========================================================
# A5 — GPT ASİSTANI HANDLE (UI Bağlayıcı)
# ==========================================================

def handle_gpt_assistant(profile: Literal["ecom", "consult"], user_message: str):
    """
    UI → GPT Asistanı bağlayıcısı.
    Bu fonksiyon:
        - Upload'ı ekler
        - Güvenlik filtresini uygular
        - Sistem intercept'leri yürütür
        - GPT yanıtını UI'da gösterir
    """

    # 1️⃣ Güvenlik filtresi
    mod = moderate_content(user_message)
    if mod:
        with st.chat_message("assistant"):
            st.write(mod)
        st.session_state.chat_history.append({"role": "assistant", "content": mod})
        return

    # 2️⃣ Sistem intercept (zaman, kimlik, hava durumu)
    util = custom_utility_interceptor(user_message)
    ident = custom_identity_interceptor(user_message)

    if ident or util:
        result = ident or util
        with st.chat_message("assistant"):
            st.write(result)
        st.session_state.chat_history.append({"role": "assistant", "content": result})
        return

    # 3️⃣ Normal GPT Asistan İşlemi
    with st.chat_message("assistant"):
        with st.spinner("Qelyon AI düşünüyor..."):
            answer = gpt_assistant(profile)
            st.write(answer)

    st.session_state.chat_history.append({"role": "assistant", "content": answer})
# ==========================================================
# A6 — ÜÇ MOD ARAYÜZÜ VE MOTOR SEÇİMİ (Gemini + GPT)
# ==========================================================

def render_main_modes():

    st.markdown("### 🤖 Mod Seçimi")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("💬 Genel Chat (Gemini)", use_container_width=True,
                     type="primary" if st.session_state.app_mode == "GENERAL_CHAT" else "secondary"):
            st.session_state.app_mode = "GENERAL_CHAT"
            st.session_state.chat_history = [
                {"role": "assistant", "content": "Merhaba! Gemini tabanlı Genel Chat'e hoş geldin. Nasıl yardımcı olabilirim?"}
            ]
            st.session_state.chat_image = None
            st.rerun()

    with col2:
        if st.button("🛒 E-Ticaret Asistanı (GPT-4o)", use_container_width=True,
                     type="primary" if st.session_state.app_mode == "ECOM" else "secondary"):
            st.session_state.app_mode = "ECOM"
            st.session_state.chat_history = [
                {"role": "assistant", "content": "E-Ticaret Asistanı aktif! Ürün bilgilerini yazmaya hazırım."}
            ]
            st.session_state.chat_image = None
            st.rerun()

    with col3:
        if st.button("💼 Danışmanlık Asistanı (GPT-4o)", use_container_width=True,
                     type="primary" if st.session_state.app_mode == "CONSULT" else "secondary"):
            st.session_state.app_mode = "CONSULT"
            st.session_state.chat_history = [
                {"role": "assistant", "content": "Danışmanlık Asistanı aktif! İşini bana anlat, birlikte geliştirelim."}
            ]
            st.session_state.chat_image = None
            st.rerun()

    st.divider()



# ==========================================================
# A6 — GENEL CHAT (GEMINI MOTORU)
# ==========================================================

def general_chat_ui():
    st.markdown("### 💬 Gemini — Genel Chat")
    st.caption("Metin, görsel analizi ve görsel oluşturma için hazır!")

    # Mesaj geçmişi
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Upload bölümü
    upload = st.file_uploader(
        "Görsel / PDF / Dosya ekle",
        type=["png", "jpg", "jpeg", "webp", "pdf"],
        key="general_upload"
    )

    if upload:
        st.session_state.chat_image = upload.read()
        st.success("Dosya yüklendi!")

    prompt = st.chat_input("Bir mesaj yaz...")

    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # ---- Gemini çağrısı ----
        from google import generativeai as gen

        gen.configure(api_key=st.secrets["GEMINI_API_KEY"])

        model = gen.GenerativeModel("gemini-1.5-pro")

        parts = [prompt]

        # Görsel ekli ise vision input ekle
        if st.session_state.chat_image:
            import mimetypes
            mime = mimetypes.guess_type("x")[0] or "image/png"
            parts.append({
                "mime_type": mime,
                "data": st.session_state.chat_image
            })

        with st.chat_message("assistant"):
            with st.spinner("Gemini düşünüyor..."):
                response = model.generate_content(parts)
                answer = response.text
                st.write(answer)

        st.session_state.chat_history.append({"role": "assistant", "content": answer})



# ==========================================================
# A6 — ROUTER (Hangi mod açılacak?)
# ==========================================================

def run_assistant_router():

    # 1️⃣ Mod butonlarını çiz
    render_main_modes()

    # 2️⃣ Mod’a göre motor çalıştır
    if st.session_state.app_mode == "GENERAL_CHAT":
        general_chat_ui()

    elif st.session_state.app_mode == "ECOM":
        handle_gpt_assistant("ecom", st.chat_input("Mesaj yazın..."))

    elif st.session_state.app_mode == "CONSULT":
        handle_gpt_assistant("consult", st.chat_input("Mesaj yazın..."))
# ============================
# QELYON AI STÜDYO — FINAL v7
# Hybrid Multi-Model System
# Gemini Vision + GPT-4o
# ============================

# =======================================================
# CONFIG & SECRETS
# =======================================================

# ---- API Keys ----
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", None)
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)
WEATHER_API_KEY = st.secrets.get("WEATHER_API_KEY", None)

if not GEMINI_API_KEY:
    st.error("❌ Gemini API anahtarı bulunamadı. 'secrets.toml' içine eklemelisiniz.")
if not OPENAI_API_KEY:
    st.error("❌ OpenAI API anahtarı bulunamadı. GPT tabanlı modlar çalışmayacaktır.")

# ---- Google Gemini Setup ----
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ---- OpenAI Setup ----
openai_client = None
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ---- Model Names ----
GEMINI_FLASH = "gemini-1.5-flash"
GEMINI_PRO   = "gemini-1.5-pro"
OPENAI_GPT   = st.secrets.get("OPENAI_MODEL", "gpt-4o")


# =======================================================
# PAGE CONFIG
# =======================================================

st.set_page_config(
    page_title="Qelyon AI Stüdyo",
    page_icon="favicn.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =======================================================
# THEME COLORS
# =======================================================

def get_theme(is_dark: bool):
    return {
        "bg": "#050509" if is_dark else "#F7F8FE",
        "text": "#FFFFFF" if is_dark else "#0A0A0C",
        "subtext": "#A0AEC0" if is_dark else "#555",
        "card": "rgba(255,255,255,0.04)" if is_dark else "rgba(255,255,255,0.70)",
        "border": "rgba(255,255,255,0.1)" if is_dark else "rgba(0,0,0,0.1)",
        "accent": "#6C47FF",
        "accent_hover": "#5830E0",
        "input": "rgba(255,255,255,0.08)" if is_dark else "#FFFFFF",
    }

def inject_css(theme):
    st.markdown(f"""
<style>

body, .stApp {{
    background: {theme['bg']} !important;
    color: {theme['text']};
    font-family: 'Inter', sans-serif;
}}

.stTextInput input, textarea {{
    background: {theme['input']} !important;
    color: {theme['text']} !important;
    border-radius: 12px !important;
    border: 1px solid {theme['border']} !important;
}}

[data-testid="stChatInput"] textarea {{
    background: {theme['input']} !important;
    color: {theme['text']} !important;
    border-radius: 999px !important;
}}

.stButton>button {{
    background-color: {theme['accent']} !important;
    border-radius: 999px !important;
    color: white;
    border: none;
    font-weight: 600;
    padding: 8px 18px;
}}

.stButton>button:hover {{
    background-color: {theme['accent_hover']} !important;
}}

.image-card {{
    background: {theme['card']};
    backdrop-filter: blur(18px);
    border-radius: 16px;
    padding: 14px;
    border: 1px solid {theme['border']};
}}

</style>
    """, unsafe_allow_html=True)


# ==============================================================  
# Voice-to-Text — Web Speech API
# ==============================================================

def inject_voice_js():
    st.markdown("""
<script>
(function() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return;

  function mount() {
    const root = window.parent.document.querySelector('[data-testid="stChatInput"]');
    if (!root) return;
    if (root.querySelector('#qelyon-mic')) return;

    const textarea = root.querySelector('textarea');
    if (!textarea) return;

    const btn = document.createElement('button');
    btn.id = 'qelyon-mic';
    btn.innerHTML = '🎤';
    btn.style.marginLeft = '8px';
    btn.style.background = '#6C47FF';
    btn.style.color = 'white';
    btn.style.borderRadius = '999px';
    btn.style.border = 'none';
    btn.style.padding = '5px 10px';
    btn.style.cursor = 'pointer';

    const rec = new SpeechRecognition();
    rec.lang = 'tr-TR';
    rec.onresult = (e) => {
        textarea.value = textarea.value + " " + e.results[0][0].transcript;
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
    };

    btn.onclick = () => rec.start();
    root.appendChild(btn);
  }

  setInterval(mount, 1200);
})();
</script>
    """, unsafe_allow_html=True)
# ============================================================
# A7-2 — GÖRSEL İŞLEME MOTORU (GEMINI 1.5 VISION)
# ============================================================

# PDF dönüşümü için
from pdf2image import convert_from_bytes


# -----------------------------
# PDF → PNG dönüşümü
# -----------------------------
def pdf_to_png(pdf_bytes: bytes) -> Image.Image:
    """
    Kullanıcı PDF yüklediğinde ilk sayfayı görüntüye dönüştürür.
    (Gemini PDF destekler ama görüntü işlemede PNG daha stabil.)
    """
    try:
        pages = convert_from_bytes(pdf_bytes, dpi=200)
        return pages[0].convert("RGBA")
    except Exception as e:
        print("PDF dönüştürme hatası:", e)
        return None


# -----------------------------
# Gemini Vision model seçici
# -----------------------------
def get_gemini_model(vision: bool = True):
    if vision:
        return genai.GenerativeModel(GEMINI_FLASH)  # hızlı + görsel desteği
    return genai.GenerativeModel(GEMINI_PRO)


# -----------------------------
# Görseli daha kaliteli işlemek için
# 1024x1024 kare tuvale yerleştir
# -----------------------------
def prepare_image_square(image: Image.Image, side: int = 1024) -> Image.Image:
    img = image.copy()
    img.thumbnail((side - 100, side - 100))

    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    x = (side - img.width) // 2
    y = (side - img.height) // 2
    canvas.paste(img, (x, y), img if img.mode == "RGBA" else None)
    return canvas


# -----------------------------
# Gemini Vision — Arka Plan Kaldırma
# -----------------------------
def gemini_remove_background(image: Image.Image) -> Image.Image:
    """
    Gemini Vision ile gelişmiş HQ arka plan kaldırma.
    İnce zincir, saç, örgü dokularını yüksek doğrulukla korur.
    """
    try:
        # Gemini Vision'a gönderilecek veri
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        img_bytes = img_bytes.getvalue()

        model = get_gemini_model(vision=True)

        response = model.generate_content(
            [
                {
                    "mime_type": "image/png",
                    "data": img_bytes
                },
                "Remove the entire background. Preserve object edges, metallic reflections, chains, fibers, and small details. Output alpha-transparent PNG."
            ],
            generation_config={
                "temperature": 0.1
            }
        )

        # Çıktı görüntüsünü decode et
        img_data = response._result.candidates[0].content.parts[0].raw_bytes
        return Image.open(io.BytesIO(img_data)).convert("RGBA")

    except Exception as e:
        print("Gemini remove_bg hata:", e)
        return image


# -----------------------------
# Gemini Vision — Image Edit / Scene Generation
# -----------------------------
def gemini_edit_scene(image: Image.Image, prompt: str) -> Optional[bytes]:
    """
    Kullanıcının serbest yazım sahne açıklamasına göre AI ile görsel oluşturur.
    Ürün değiştirilmez, sadece sahne tasarlanır.
    """
    try:
        model = get_gemini_model(vision=True)

        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        img_bytes = img_bytes.getvalue()

        response = model.generate_content(
            [
                {
                    "mime_type": "image/png",
                    "data": img_bytes
                },
                (
                    "Preserve the original product EXACTLY. "
                    "Do NOT modify shape, color, brand, or geometry. "
                    "Replace the background based on the following scene instructions: "
                    + prompt
                )
            ],
            generation_config={
                "temperature": 0.15,
                "max_output_tokens": 2048,
            }
        )

        img_data = response._result.candidates[0].content.parts[0].raw_bytes
        return img_data

    except Exception as e:
        print("Gemini edit hata:", e)
        return None


# -----------------------------
# Kullanıcı görselini normalize et
# -----------------------------
def load_user_image(uploaded_file):
    """
    PDF → PNG
    JPG/PNG → RGBA
    Orientation fix
    """
    try:
        if uploaded_file.type == "application/pdf":
            return pdf_to_png(uploaded_file.read())

        img = Image.open(uploaded_file)
        img = ImageOps.exif_transpose(img)
        return img.convert("RGBA")

    except Exception as e:
        print("Görsel yükleme hatası:", e)
        return None
# ============================================================
# A7-3 — GENEL CHAT MOTORU (GEMINI PRO + GEMINI VISION)
# ============================================================

# -------------------------------------------
# Gemini ile Görsel Analizi
# -------------------------------------------
def gemini_analyze_image(img_bytes: bytes, prompt: str = "") -> str:
    """
    Genel chat içinde görsel varsa analiz etmek için.
    """
    try:
        model = get_gemini_model(vision=True)

        response = model.generate_content(
            [
                {"mime_type": "image/png", "data": img_bytes},
                (
                    "Analyze the uploaded image in detail. "
                    "Describe its content, objects, colors, textures, style, and scene. "
                    + prompt
                )
            ],
            generation_config={"temperature": 0.2}
        )

        return response.text

    except Exception as e:
        print("Gemini görsel analiz hatası:", e)
        return "Görseli işlerken bir hata oluştu."


# -------------------------------------------
# Gemini ile Görsel Oluşturma (Text → Image)
# -------------------------------------------
def gemini_generate_image(prompt: str) -> Optional[bytes]:
    """
    Genel chat içinde: “Bu promptla görsel üret” gibi isteklerde.
    """
    try:
        model = get_gemini_model(vision=False)

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": 2048
            }
        )

        img_data = response._result.candidates[0].content.parts[0].raw_bytes
        return img_data

    except Exception as e:
        print("Gemini görsel oluşturma hatası:", e)
        return None


# -------------------------------------------
# Kimlik Yanıtı (Qelyon AI)
# -------------------------------------------
def chat_identity_intercept(message: str) -> Optional[str]:
    msg = message.lower().strip()

    triggers = [
        "kimsin", "sen kimsin", "kim geliştirdi", "seni kim yaptı", "who are you",
        "who created you", "kim yarattı"
    ]

    if any(t in msg for t in triggers):
        return (
            "Ben **Qelyon AI**.\n"
            "Profesyonel üretkenlik, görsel işleme ve danışmanlık çözümleri sunan gelişmiş bir yapay zekayım. "
            "Görselleri işler, içerik üretir ve iş stratejisi geliştirmen için destek sağlarım. 🚀"
        )
    return None


# -------------------------------------------
# Saat / Tarih / Hava Durumu intercept
# -------------------------------------------
def chat_utility_intercept(message: str) -> Optional[str]:
    text = message.lower()

    # Saat & tarih (tarihçesi olmasın)
    if "saat" in text or "tarih" in text:
        if "tarihi" not in text and "tarihçesi" not in text:
            return get_time_answer()

    # 7 günlük
    if "7 günlük hava" in text or "haftalık hava" in text:
        city = extract_city_from_message(message)
        return get_weather_forecast_answer(city)

    # tek gün hava durumu
    if "hava" in text or "hava durumu" in text:
        city = extract_city_from_message(message)
        return get_weather_answer(city)

    return None


# -------------------------------------------
# Güvenlik filtresi
# -------------------------------------------
def chat_moderate(message: str) -> Optional[str]:
    return moderate_content(message)


# -------------------------------------------
# Genel Chat — Gemini Pro Cevap Motoru
# -------------------------------------------
def general_chat_gemini(message: str, image_bytes: Optional[bytes] = None) -> str:
    """
    Genel Chat → Gemini 1.5 Pro kullanır.
    Görsel eklendi ise otomatik analiz eder.
    """
    # Güvenlik
    sec = chat_moderate(message)
    if sec:
        return sec

    # Kimlik & saat & hava intercept
    ident = chat_identity_intercept(message)
    if ident:
        return ident

    util = chat_utility_intercept(message)
    if util:
        return util

    # Görsel yüklendiyse analiz
    if image_bytes is not None:
        return gemini_analyze_image(
            image_bytes,
            prompt=(
                "Görseli analiz et. Eğer kullanıcı e-ticaret açıklaması isterse "
                "ürünün malzemesi, renk tonu, kullanım alanı, kategori ve stilini belirt."
            )
        )

    # Normal metin → Gemini Pro
    try:
        model = get_gemini_model(vision=False)

        response = model.generate_content(
            message,
            generation_config={"temperature": 0.25, "max_output_tokens": 2000},
        )
        return response.text

    except Exception as e:
        print("Genel chat API hatası:", e)
        return "Şu an Gemini ile bağlantı kuramıyorum. Birkaç saniye sonra tekrar deneyebilirsin."


# -------------------------------------------
# Genel Chat Görsel Üretim Komutu Algılayıcı
# -------------------------------------------
def detect_generate_image_command(message: str) -> Optional[str]:
    """
    Kullanıcı: 'bana şöyle bir görsel üret' dediğinde tetiklenir.
    """
    triggers = [
        "görsel üret",
        "resim oluştur",
        "image generate",
        "fotoğraf oluştur",
        "bir görsel yap"
    ]

    msg = message.lower()
    if any(t in msg for t in triggers):
        return message  # prompt olarak kullanılır

    return None
# ============================================================
# A7-4 — E-TİCARET & DANIŞMANLIK YAPAY ZEKA MOTORU (GPT-4o)
# ============================================================

# ------------------------------------------------------------
# GPT-4o istemci oluşturucu
# ------------------------------------------------------------
def get_gpt_client():
    if not SABIT_API_KEY:
        return None
    try:
        return OpenAI(api_key=SABIT_API_KEY)
    except:
        return None


# ------------------------------------------------------------
# E-Ticaret System Prompt
# ------------------------------------------------------------
def system_prompt_ecommerce():
    now = turkce_zaman_getir()
    return f"""
Sen Qelyon AI'sın.
Uzmanlık alanın: e-ticaret satış optimizasyonu, ürün açıklamaları, varyant analizi,
kampanya içerikleri ve pazaryeri SEO’su.

Yazım stilin:
- Profesyonel
- Ürün faydasını hızlı anlatan
- Madde madde net ifadeler
- Gereksiz süsleme yok

Zorunlu format:

1) Kısa giriş paragrafı  
2) Öne çıkan 5 fayda  
3) Kutu içeriği  
4) Hedef kitle  
5) Kullanım önerileri  
6) Satın almaya yönlendiren CTA  

Ek görevler:  
- Kullanıcı isterse Trendyol etiketleri üret  
- Ürün başlığı için A/B test versiyonları çıkar  
- Ürünün olası varyantlarını (renk/boyut/kapasite) analiz et  
- Müşteri yorumu verilirse memnuniyet & şikayet temaları çıkar  
- Sosyal medya reklam metni üretebilirsin  

Bu yanıt {now} tarihinde oluşturulmuştur.
"""


# ------------------------------------------------------------
# Danışmanlık System Prompt
# ------------------------------------------------------------
def system_prompt_consulting():
    now = turkce_zaman_getir()
    return f"""
Sen Qelyon AI'sın.
Profesyonel iş ve yönetim danışmanısın.

Uzmanlık alanların:
- Şirket büyüme stratejileri
- OKR & KPI geliştirme
- Pazarlama hunisi optimizasyonu
- İş modeli analizleri
- Finansal varsayım ile planlama
- Segmentasyon & müşteri analizi

Yanıt stilin:
- Net, uygulanabilir
- Gerektiğinde maddeli açıklamalar
- Belirsizlik varsa varsayım belirt
- Stratejik içgörü üret

Bu yanıt {now} tarihinde oluşturulmuştur.
"""


# ------------------------------------------------------------
# E-Ticaret Prompt İşleyici
# ------------------------------------------------------------
def ecommerce_process_prompt(user_msg: str, img_bytes: Optional[bytes]) -> str:
    client = get_gpt_client()
    if not client:
        return "GPT hizmeti şu anda kullanılamıyor."

    messages = [
        {"role": "system", "content": system_prompt_ecommerce()},
    ]

    # Eğer görsel varsa GPT’ye açıklamada yardımcı olması için metin ekleriz
    if img_bytes is not None:
        encoded = base64.b64encode(img_bytes).decode("utf-8")
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "Ürün görseli analiz et ve e-ticaret açıklaması oluştur."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}}
            ]
        })

    messages.append({"role": "user", "content": user_msg})

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.25,
            max_tokens=1800,
        )
        return resp.choices[0].message.content

    except Exception as e:
        print("E-ticaret GPT hatası:", e)
        return "E-Ticaret yanıtı oluşturulamadı."


# ------------------------------------------------------------
# Danışmanlık Prompt İşleyici
# ------------------------------------------------------------
def consult_process_prompt(user_msg: str, img_bytes: Optional[bytes]) -> str:
    client = get_gpt_client()
    if not client:
        return "GPT hizmeti şu anda kullanılamıyor."

    messages = [
        {"role": "system", "content": system_prompt_consulting()},
        {"role": "user", "content": user_msg},
    ]

    # Danışmanlık modunda görsel işleme genelde gerekmez,
    # ama kullanıcı 'bu tabloyu analiz et' derse destek olur.
    if img_bytes is not None:
        try:
            encoded = base64.b64encode(img_bytes).decode("utf-8")
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Bu görselde analiz edilecek veri olabilir. İçgörü çıkar."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}}
                    ]
                }
            )
        except:
            pass

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.2,
            max_tokens=2000,
        )
        return resp.choices[0].message.content

    except Exception as e:
        print("Danışmanlık GPT hatası:", e)
        return "Danışmanlık analizi yapılamadı."


# ------------------------------------------------------------
# Router — Hangi model kullanılacak?
# ------------------------------------------------------------
def run_specialized_chat(mode: str, message: str, img_bytes: Optional[bytes]) -> str:
    """
    mode:
      - 'ecom'
      - 'consult'
    """
    if mode == "ecom":
        return ecommerce_process_prompt(message, img_bytes)

    if mode == "consult":
        return consult_process_prompt(message, img_bytes)

    return "Geçersiz mod."
# ============================================================
# A7-5 — ANA UI ROUTER (Gemini + GPT-4o entegrasyonu)
# ============================================================

def run_general_chat_gemini(user_msg: str, img_bytes: Optional[bytes]):
    """Genel Chat → Gemini 1.5 Pro / Flash"""
    if not GEMINI_API_KEY:
        return "Gemini API anahtarı bulunamadı."

    model_name = "gemini-1.5-pro"   # en gelişmişi
    payload = {
        "contents": [
            {
                "parts": [{"text": user_msg}]
            }
        ]
    }

    # Görsel eklendiyse
    if img_bytes:
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        payload["contents"][0]["parts"].append(
            {"inline_data": {"mime_type": "image/png", "data": b64}}
        )

    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}",
            json=payload,
            timeout=20,
        )
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("Gemini hata:", e)
        return "Gemini yanıt üretirken sorun oluştu."


# ============================================================
# A7-5 — CHAT UI + YÖNLENDİRME BLOĞU
# ============================================================

def chat_interface(mode: str):
    """
    mode:
      - "general"   → Gemini
      - "ecom"      → GPT-4o
      - "consult"   → GPT-4o
    """
    inject_voice_js()

    # Başlık
    if mode == "general":
        st.markdown("### 💬 Genel Chat (Gemini 1.5 Pro)")
    elif mode == "ecom":
        st.markdown("### 🛒 Qelyon AI — E-Ticaret Asistanı (GPT-4o)")
    else:
        st.markdown("### 💼 Qelyon AI — Danışmanlık Asistanı (GPT-4o)")

    st.caption("Mesaj yazabilir, sesle giriş yapabilir veya görsel ekleyebilirsin.")

    # Konuşma geçmişi
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # ------------------------------------------------------------
    # '+' BUTONU → DOSYA EKLE PANELİ
    # ------------------------------------------------------------
    uibar = st.container()
    with uibar:
        col_a, col_b = st.columns([0.12, 0.88])

        with col_a:
            if st.button("➕", key="add_file2", help="Dosya / görsel ekle"):
                st.session_state.show_upload_panel = not st.session_state.show_upload_panel

        with col_b:
            if st.session_state.chat_image:
                st.caption("📎 Görsel yüklendi, analiz edebilirim.")
            else:
                st.caption("Dosya ekleyebilirsin.")

    # Upload paneli
    if st.session_state.show_upload_panel:
        up = st.file_uploader(
            "Görsel / Dosya Ekle", type=["png", "jpg", "jpeg", "webp", "pdf"]
        )
        if up:
            if up.type == "application/pdf":
                st.warning("PDF içerik desteği yakında eklenecek (şimdilik yalnızca görsel).")
            else:
                st.session_state.chat_image = up.read()
                st.success("Görsel başarıyla eklendi.")
            st.session_state.show_upload_panel = False

    # ------------------------------------------------------------
    # CHAT INPUT
    # ------------------------------------------------------------
    user_msg = st.chat_input("Mesaj yazın…")
    if not user_msg:
        return

    # Geçmişe ekle
    st.session_state.chat_history.append({"role": "user", "content": user_msg})
    with st.chat_message("user"):
        st.write(user_msg)

    # Güvenlik filtresi
    unsafe = moderate_content(user_msg)
    if unsafe:
        st.session_state.chat_history.append({"role": "assistant", "content": unsafe})
        with st.chat_message("assistant"):
            st.write(unsafe)
        return

    # Kimlik ve util intercept (genel chat hariç)
    if mode in ["ecom", "consult"]:
        ident = custom_identity_interceptor(user_msg)
        util = custom_utility_interceptor(user_msg)

        if ident:
            st.session_state.chat_history.append({"role": "assistant", "content": ident})
            with st.chat_message("assistant"):
                st.write(ident)
            return

        if util:
            st.session_state.chat_history.append({"role": "assistant", "content": util})
            with st.chat_message("assistant"):
                st.write(util)
            return

    # ------------------------------------------------------------
    # MODEL MOTORUNA GÖNDER
    # ------------------------------------------------------------
    img_bytes = st.session_state.chat_image

    if mode == "general":
        response = run_general_chat_gemini(user_msg, img_bytes)

    elif mode == "ecom":
        response = run_specialized_chat("ecom", user_msg, img_bytes)

    elif mode == "consult":
        response = run_specialized_chat("consult", user_msg, img_bytes)

    else:
        response = "Mod bulunamadı."

    # ------------------------------------------------------------
    # YANITI YAZDIR + GEÇMİŞE EKLE
    # ------------------------------------------------------------
    with st.chat_message("assistant"):
        st.write(response)

    st.session_state.chat_history.append({"role": "assistant", "content": response})
# ============================================================
# A8 — ANA ÇALIŞTIRMA BLOĞU (UI ROUTER)
# ============================================================

def main_app():
    inject_favicon()

    # ------------------------------
    # Tema seçimi
    # ------------------------------
    col_t1, col_t2 = st.columns([10, 1])
    with col_t2:
        dark_mode = st.toggle("🌙 / ☀️", value=True, key="theme_toggle")

    tema = get_theme(dark_mode)
    apply_apple_css(tema)

    # ------------------------------
    # Sidebar (konuşma geçmişi + hazır promptlar)
    # ------------------------------
    sidebar_ui()

    # ------------------------------
    # Logo + Başlık alanı
    # ------------------------------
    col_logo, col_title = st.columns([0.15, 0.85])
    with col_logo:
        logo_file = LOGO_DARK_PATH if dark_mode else LOGO_LIGHT_PATH
        try:
            st.image(logo_file, width=110)
        except:
            st.markdown("### Qelyon AI")

    with col_title:
        st.markdown(
            """
            <h1 style="margin-bottom:4px;">Qelyon AI Stüdyo</h1>
            <p style="margin-top:0; font-size:0.95rem;">
                Görsel düzenleme, e-ticaret metinleri ve profesyonel danışmanlık
                süreçlerinde en güçlü asistanın.
            </p>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    # ------------------------------
    # 3 Mod (Stüdyo / E-Ticaret / Danışmanlık / Genel Chat)
    # ------------------------------
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)

    mode = st.session_state.app_mode

    with col_m1:
        if st.button("📸 Stüdyo Modu", use_container_width=True,
                     type="primary" if mode=="studio" else "secondary"):
            st.session_state.app_mode = "studio"
            st.session_state.sonuc_gorseli = None
            st.rerun()

    with col_m2:
        if st.button("🛒 E-Ticaret Asistanı", use_container_width=True,
                     type="primary" if mode=="ecom" else "secondary"):
            st.session_state.app_mode = "ecom"
            st.session_state.chat_image = None
            st.rerun()

    with col_m3:
        if st.button("💼 Danışmanlık Asistanı", use_container_width=True,
                     type="primary" if mode=="consult" else "secondary"):
            st.session_state.app_mode = "consult"
            st.session_state.chat_image = None
            st.rerun()

    with col_m4:
        if st.button("💬 Genel Chat (Gemini)", use_container_width=True,
                     type="primary" if mode=="general" else "secondary"):
            st.session_state.app_mode = "general"
            st.session_state.chat_image = None
            st.rerun()

    st.divider()

    # ------------------------------
    # MOD YÖNLENDİRME
    # ------------------------------
    if st.session_state.app_mode == "studio":
        run_studio_mode()            # Gemini Vision ile sahne düzenleme

    elif st.session_state.app_mode == "general":
        chat_interface("general")    # Gemini 1.5 Pro

    elif st.session_state.app_mode == "ecom":
        chat_interface("ecom")       # GPT-4o

    elif st.session_state.app_mode == "consult":
        chat_interface("consult")    # GPT-4o

    else:
        st.error("Bilinmeyen mod seçildi.")

    # ------------------------------
    # Footer
    # ------------------------------
    st.markdown(
        "<div class='custom-footer'>Qelyon AI Stüdyo © 2025 | Developed by Alper</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# Uygulamayı çalıştır
# ============================================================

try:
    main_app()
except Exception as e:
    print("MAIN ERROR:", traceback.format_exc())
    st.error("⚠️ Beklenmeyen bir hata oluştu. Sayfayı yenileyebilirsiniz.")
# ============================================================
# A9 — STÜDYO MODU (Gemini Vision ile Görsel İşleme)
# ============================================================

import google.generativeai as genai
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def run_studio_mode():
    st.markdown("### 📤 Ürün görselini yükle")

    uploaded = st.file_uploader(
        "Görsel seçin",
        type=["png", "jpg", "jpeg", "webp"],
        label_visibility="collapsed",
    )

    if not uploaded:
        st.info("Bir ürün görseli yükleyin.")
        return

    # Görseli oku
    try:
        raw = Image.open(uploaded)
        raw = ImageOps.exif_transpose(raw).convert("RGBA")
    except:
        st.error("⚠ Görsel okunamadı.")
        return

    # Önizleme
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("### 📌 Orijinal")
        st.image(raw, width=360)

    with col2:
        st.markdown("### 🎨 Tema / Düzenleme")

        tab_preset, tab_free = st.tabs(["🎛 Hazır Temalar", "✏️ Serbest Prompt"])

        # ----------------------------
        # PRESET
        # ----------------------------
        with tab_preset:
            tema = st.selectbox(
                "Tema seç:",
                [
                    "🧹 Şeffaf Arka Plan",
                    "⬜ Beyaz Arka Plan",
                    "⬛ Siyah Arka Plan",
                    "🍦 Bej Arka Plan",
                    "✨ Profesyonel Stüdyo",
                ],
            )

        # ----------------------------
        # SERBEST PROMPT
        # ----------------------------
        with tab_free:
            serbest = st.text_area(
                "Serbest sahne açıklaması:",
                placeholder="Örn: Ürünü merkezde bırak, yumuşak gölge ve açık gri degrade arka plan."
            )

        # ----------------------------
        # İŞLEM BAŞLAT
        # ----------------------------
        if st.button("🚀 Oluştur", type="primary"):
            with st.spinner("Gemini Vision sahneyi oluşturuyor..."):

                try:
                    # Görseli bytes olarak hazırla
                    img_bytes = BytesIO()
                    raw.save(img_bytes, format="PNG")
                    img_bytes.seek(0)

                    # --------------------------------------------
                    # PRESET PROMPT OLUŞTURUCU
                    # --------------------------------------------
                    if serbest.strip() == "":
                        if tema == "🧹 Şeffaf Arka Plan":
                            prompt = """
                            Remove background COMPLETELY.
                            Preserve object edges, chains, textures.
                            No shadow, no artifacts. Transparent PNG output.
                            """

                        elif tema == "⬜ Beyaz Arka Plan":
                            prompt = """
                            Replace background with PURE white (#ffffff).
                            Add soft professional shadow under product.
                            Keep product geometry unchanged.
                            """

                        elif tema == "⬛ Siyah Arka Plan":
                            prompt = """
                            Replace background with deep black (#000000).
                            Add soft realistic shadow.
                            High contrast professional studio style.
                            """

                        elif tema == "🍦 Bej Arka Plan":
                            prompt = """
                            Replace background with soft beige (#f5eedd).
                            Add smooth studio shadow.
                            """

                        elif tema == "✨ Profesyonel Stüdyo":
                            prompt = """
                            Create premium infinite studio background.
                            Soft white gradient, studio lighting, contact shadow + slight reflection.
                            Preserve product exactly.
                            """

                    else:
                        # SERBEST PROMPT
                        prompt = (
                            "Do not modify product shape, color or material. "
                            "High-end studio look. " + serbest
                        )

                    # --------------------------------------------
                    # GEMINI VISION İSTEĞİ
                    # --------------------------------------------
                    model = genai.GenerativeModel("gemini-1.5-flash")

                    out = model.generate_images(
                        prompt=prompt,
                        images=[img_bytes.getvalue()],
                        size="1024x1024"
                    )

                    # Gemini çıktıyı al
                    result_bytes = out.images[0]

                    # Sonuç kaydet
                    st.session_state.sonuc_gorseli = result_bytes

                except Exception as e:
                    st.error("⚠ Görsel oluşturulurken bir hata oluştu.")
                    st.write(e)
                    return

                st.rerun()

    # ----------------------------
    # SONUÇ EKRANI
    # ----------------------------
    if st.session_state.sonuc_gorseli:
        st.markdown("### ✅ Sonuç")
        st.image(st.session_state.sonuc_gorseli, width=380)

        colA, colB = st.columns(2)
        with colA:
            if st.button("🔄 Yeni işlem"):
                st.session_state.sonuc_gorseli = None
                st.rerun()
        with colB:
            st.download_button(
                "📥 PNG indir",
                data=st.session_state.sonuc_gorseli,
                file_name="qelyon_studio.png",
                mime="image/png",
            )
# ============================================================
# A10 — GENEL CHAT (Gemini 1.5 Pro + Flash)
# ============================================================

import google.generativeai as genai
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def run_general_chat():
    st.markdown("### 💬 Qelyon AI — Genel Chat")
    st.caption("Her konuda soru sorabilir, görsel yükleyebilir veya yeni görsel oluşturmasını isteyebilirsin.")

    # Oturum setup
    if "general_chat" not in st.session_state:
        st.session_state.general_chat = [
            {"role": "assistant", "content": "Merhaba! Ben Qelyon AI. Nasıl yardımcı olabilirim?"}
        ]
    if "general_image" not in st.session_state:
        st.session_state.general_image = None
    if "general_upload_panel" not in st.session_state:
        st.session_state.general_upload_panel = False

    # ---------------------------
    # Geçmiş mesajları göster
    # ---------------------------
    for msg in st.session_state.general_chat:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # ---------------------------
    # '+' — Dosya yükleme butonu
    # ---------------------------
    bar = st.container()
    with bar:
        c1, c2 = st.columns([0.15, 0.85])
        with c1:
            if st.button("➕", key="general_add_file", help="Dosya veya görsel ekle"):
                st.session_state.general_upload_panel = not st.session_state.general_upload_panel

        with c2:
            if st.session_state.general_image:
                st.caption("📎 Bir görsel yüklü. Analiz isteyebilirsin.")

        # Yükleme paneli açıldıysa:
        if st.session_state.general_upload_panel:
            up = st.file_uploader("Görsel yükle", type=["png", "jpg", "jpeg", "webp"])
            if up:
                st.session_state.general_image = up.read()
                st.session_state.general_upload_panel = False
                st.success("Görsel yüklendi! Şimdi analiz isteyebilirsin.")
                st.rerun()

    # ---------------------------
    # Mesaj Input
    # ---------------------------
    message = st.chat_input("Mesaj yazın...")

    if not message:
        return

    # Kullanıcı mesajı ekle
    st.session_state.general_chat.append({"role": "user", "content": message})
    with st.chat_message("user"):
        st.write(message)

    # ---------------------------
    # 1 — Kullanıcı görsel oluşturmayı istiyor mu?
    # ---------------------------
    wants_image = any(w in message.lower() for w in [
        "görsel oluştur",
        "resim oluştur",
        "image generate",
        "bir görsel yap",
        "fotoğraf üret",
        "ai görsel oluştur"
    ])

    # ---------------------------
    # 2 — Kullanıcı görsel yüklemiş mi?
    # ---------------------------
    has_user_image = st.session_state.general_image is not None

    # ---------------------------
    # GEMINI MODELLERİ
    # ---------------------------
    gemini_flash = genai.GenerativeModel("gemini-1.5-flash")
    gemini_pro = genai.GenerativeModel("gemini-1.5-pro")

    # ========================================================
    #   DURUM 1 → GÖRSEL OLUŞTURMA
    # ========================================================
    if wants_image:
        with st.chat_message("assistant"):
            st.write("🎨 Yüksek kaliteli bir görsel oluşturuyorum...")

        try:
            out = gemini_pro.generate_images(
                prompt=message,
                size="1024x1024"
            )

            img_bytes = out.images[0]

            with st.chat_message("assistant"):
                st.image(img_bytes, caption="Oluşturulan Görsel")
                st.session_state.general_chat.append({
                    "role": "assistant",
                    "content": "İşte oluşturduğun görsel!"
                })

            return

        except Exception as e:
            with st.chat_message("assistant"):
                st.error("⚠ Görsel oluşturulamadı.")
                st.write(e)
            return

    # ========================================================
    #   DURUM 2 → GÖRSEL ÜZERİNDEN ANALİZ / AÇIKLAMA
    # ========================================================
    if has_user_image:
        try:
            img = st.session_state.general_image

            out = gemini_pro.generate_content(
                contents=[
                    {"mime_type": "image/png", "data": img},
                    {"text": f"Bu görseli analiz et ve kullanıcı mesajına göre cevap üret: {message}"}
                ]
            )

            answer = out.text

        except Exception as e:
            answer = "⚠ Görsel analizinde bir hata oluştu."
            print(e)

        with st.chat_message("assistant"):
            st.write(answer)

        st.session_state.general_chat.append({"role": "assistant", "content": answer})
        return

    # ========================================================
    #   DURUM 3 → NORMAL SOHBET (GEMINI 1.5 PRO)
    # ========================================================
    try:
        response = gemini_pro.generate_text(message)
        answer = response.text
    except:
        answer = "⚠ Yanıt üretilemedi (Gemini)."

    with st.chat_message("assistant"):
        st.write(answer)

    st.session_state.general_chat.append({"role": "assistant", "content": answer})
