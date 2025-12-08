# ==========================================================
# QELYON AI STÜDYO — FINAL v8
# Gemini Vision • Gemini Flash • Gemini 1.5 Pro • GPT-4o Hibrit Sistem
# ==========================================================

from __future__ import annotations

import os
import io
import re
import base64
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Literal

import requests
import streamlit as st
from PIL import Image, ImageOps, ImageFilter, ImageChops, ImageDraw

# ==========================================================
# 🔐 API KEYS
# ==========================================================
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", None)
WEATHER_API_KEY = st.secrets.get("WEATHER_API_KEY", None)

GPT_MODEL = st.secrets.get("OPENAI_MODEL", "gpt-4o")
GEMINI_TEXT_MODEL = "gemini-1.5-pro"
GEMINI_VISION_MODEL = "gemini-1.5-flash"

if not OPENAI_API_KEY:
    st.error("⚠️ OPENAI_API_KEY eksik. GPT modları çalışmaz.")

if not GEMINI_API_KEY:
    st.error("⚠️ GEMINI_API_KEY eksik. Gemini modları çalışmaz.")

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
            "input": "#111111",
            "card": "rgba(255,255,255,0.05)",
            "border": "rgba(255,255,255,0.1)",
            "accent": accent,
        }
    else:
        return {
            "bg": "#F5F5FB",
            "text": "#0F172A",
            "sub": "#444444",
            "input": "#FFFFFF",
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
            padding: 10px 14px;
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
# 🌙 Tema
# ==========================================================
col_a, col_b = st.columns([10,1])
with col_b:
    dark = st.toggle("🌙 / ☀️", value=True)

THEME = get_theme(dark)
apply_theme_css(THEME)

# ==========================================================
# 🧠 GLOBAL SESSION SETUP
# ==========================================================
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "📸 Stüdyo Modu"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "chat_image" not in st.session_state:
    st.session_state.chat_image = None

if "studio_result" not in st.session_state:
    st.session_state.studio_result = None
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
    genai.configure(api_key="")  # boş da olsa initialize eder

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
    """Gemini Vision (Flash) ile görsel analiz"""
    try:
        model = genai.GenerativeModel(GEMINI_VISION_MODEL)
        img_data = {"mime_type": "image/png", "data": image_bytes}
        resp = model.generate_content([prompt, img_data])
        return resp.text
    except Exception as e:
        print("Gemini vision error:", e)
        return "Görsel analizinde bir hata oluştu."

def gemini_generate_image(prompt: str, size="1024x1024"):
    """
    Gemini Flash Image ile görsel üretimi.
    Genel Chat modunda: logo, fotoğraf, sahne vs. üretmek için kullanılır.
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        result = model.generate_image(prompt=prompt, size=size)
        return result._image  # bytes
    except Exception as e:
        print("Gemini image error:", e)
        return None


# ---------------------------
# 🤖 GPT-4o Client
# ---------------------------
from openai import OpenAI
GPT = OpenAI(api_key=OPENAI_API_KEY)

def gpt_chat(messages: list[dict], model: str = GPT_MODEL):
    """
    GPT-4o tabanlı sohbet motoru (E-ticaret & Danışmanlık için)
    """
    try:
        res = GPT.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=1500,
        )
        return res.choices[0].message.content
    except Exception as e:
        print("GPT error:", e)
        return "GPT sistemi şu anda cevap veremiyor."


# ---------------------------
# ⚡ MODEL ROUTER (Mod seçimine göre motor)
# ---------------------------
def model_router(mode: str):
    """
    MODE → MODEL
    💬 Genel Chat =====> Gemini 1.5 Pro
    🛒 E-Ticaret ======> GPT-4o
    💼 Danışmanlık =====> GPT-4o
    """
    if mode == "GENERAL_CHAT":
        return "gemini"
    if mode == "ECOM":
        return "gpt"
    if mode == "CONSULT":
        return "gpt"
    return "gemini"


# ==========================================================
# 📅 ZAMAN / TARİH SERVİSLERİ
# ==========================================================
def get_tr_time():
    try:
        r = requests.get("http://worldtimeapi.org/api/timezone/Europe/Istanbul")
        dt = r.json().get("datetime")
        return datetime.fromisoformat(dt)
    except:
        return datetime.now(ZoneInfo("Europe/Istanbul"))

def time_answer():
    now = get_tr_time()
    return f"Bugün {now.strftime('%d.%m.%Y')} — Saat {now.strftime('%H:%M')}"


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
        if not data:
            return None
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
        r = requests.get(url).json()

        desc = r["weather"][0]["description"].capitalize()
        temp = r["main"]["temp"]
        hum = r["main"]["humidity"]
        wind = r["wind"]["speed"]

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
    """Mesaj uygunsuzsa engelle."""
    for pat in BAD_WORDS:
        if re.search(pat, msg):
            return "Bu isteğe güvenlik nedeniyle yanıt veremiyorum. 🙏"
    return None
# ==========================================================
# A3 — STÜDYO MODU • GÖRSEL İŞLEME (GEMINI + LOCAL)
# ==========================================================

from PIL import Image, ImageOps, ImageFilter, ImageDraw, ImageChops


# ---------------------------------------
# 🧼 1) LOKAL ARKA PLAN KALDIRMA (HQ MASKING)
# ---------------------------------------
def remove_bg_local(image: Image.Image) -> Image.Image:
    """
    Ürünü fotoğraftan lokal threshold + mask algoritması ile ayırır.
    Gemini Vision henüz 'image edit' yapamadığı için
    en stabil ve hızlı yöntem budur.
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    gray = image.convert("L")

    # Yüksek threshold → parlak arka plan silinir
    mask = gray.point(lambda p: 255 if p > 240 else 0)

    result = Image.new("RGBA", image.size)
    result.paste(image, (0, 0), mask)
    return result


# ---------------------------------------
# 🎛 2) ÜRÜNÜ KARE TUVALE MERKEZE YERLEŞTİRME
# ---------------------------------------
def center_on_canvas(img: Image.Image, size=1024) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    obj = img.copy()
    obj.thumbnail((size * 0.84, size * 0.84), Image.Resampling.LANCZOS)

    x = (size - obj.width) // 2
    y = (size - obj.height) // 2

    canvas.paste(obj, (x, y), obj)
    return canvas


# ---------------------------------------
# 🌓 3) PROFESYONEL TEMAS GÖLGESİ
# ---------------------------------------
def make_contact_shadow(alpha: Image.Image, intensity=150):
    """Ürünün altına ticari stüdyo tarzı soft shadow üretir."""
    a = alpha.convert("L")
    box = a.getbbox()
    if not box:
        return Image.new("L", a.size, 0)

    w = box[2] - box[0]
    h = int((box[3] - box[1]) * 0.22)

    shadow = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(shadow)
    draw.ellipse((0, 0, w, h), fill=intensity)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=int(h * 0.45)))

    mask = Image.new("L", a.size, 0)
    mask.paste(shadow, (box[0], box[3] - h // 2))
    return mask


# ---------------------------------------
# 🌫 4) STÜDYO REFLECTION (Soft Reflection)
# ---------------------------------------
def make_reflection(img: Image.Image, fade=230):
    """Alt kısımda premium stüdyo refleks efekti üretir."""
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
    out.paste(flip, (box[0], box[3] + 6), flip)
    return out


# ---------------------------------------
# 🎨 5) TEMA KOMPOZİT MOTORU
# ---------------------------------------
def compose_scene(cut: Image.Image, bg_color: str, reflection=True, shadow=True):
    size = 1024
    obj = center_on_canvas(cut, size)
    alpha = obj.split()[3]

    colors = {
        "white": (255, 255, 255, 255),
        "black": (0, 0, 0, 255),
        "beige": (245, 240, 222, 255),
    }

    bg = Image.new("RGBA", (size, size), colors.get(bg_color, (255, 255, 255, 255)))
    final = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    final.alpha_composite(bg)

    if shadow:
        sh_mask = make_contact_shadow(alpha)
        sh = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        sh.putalpha(sh_mask)
        final.alpha_composite(sh)

    if reflection:
        ref = make_reflection(obj)
        final.alpha_composite(ref)

    final.alpha_composite(obj)
    return final


# ---------------------------------------
# ✨ 6) GEMINI — AI SAHNE OLUŞTURMA
# ---------------------------------------
def gemini_edit_scene(prompt: str, product_image_bytes: bytes):
    """
    Ürünü bozmadan; sadece arka planı AI ile profesyonel olarak yeniden tasarlar.
    Gemini Flash Image modeli ile çalışır.
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        img_dict = {
            "mime_type": "image/png",
            "data": product_image_bytes,
        }

        full_prompt = (
            "You are a professional commercial product photographer. "
            "Replace ONLY the background. "
            "Do NOT modify the product (color, texture, geometry). "
            "Generate a clean, studio-grade, elegant scene.\n"
            f"Background style: {prompt}"
        )

        result = model.generate_image(
            prompt=full_prompt,
            image=img_dict,
            size="1024x1024",
        )

        return result._image  # PNG bytes

    except Exception as e:
        print("Gemini Edit Scene Error:", e)
        return None


# ---------------------------------------
# 🏗 7) HAZIR TEMA PRESETLERİ
# ---------------------------------------
PRESETS = {
    "🧹 Şeffaf Arka Plan": "transparent",
    "⬜ Beyaz Arka Plan": "white",
    "⬛ Siyah Arka Plan": "black",
    "🍦 Bej Arka Plan": "beige",
    "✨ Profesyonel Stüdyo": "pro",
}

def apply_preset(img: Image.Image, preset: str):
    """
    Kullanıcının seçtiği hazır temayı uygular.
    """
    cut = remove_bg_local(img)

    if preset == "transparent":
        return cut

    if preset == "white":
        return compose_scene(cut, "white", reflection=False)

    if preset == "black":
        return compose_scene(cut, "black", reflection=False)

    if preset == "beige":
        return compose_scene(cut, "beige", reflection=False)

    if preset == "pro":
        return compose_scene(cut, "white", reflection=True)

    return cut
# ==========================================================
# A4 — GENEL CHAT MOTORU (GEMINI 1.5 PRO)
# ==========================================================

def gemini_general_chat(user_message: str, user_image: bytes | None):
    """
    Genel Chat (💬) için tam sohbet motoru:
    - Gemini 1.5 Pro metin modeli
    - Vision input destekli
    - PDF / Görsel / Dosya analizi
    - Çoklu sohbet geçmişi desteği
    """

    try:
        # --- 1) Sohbet geçmişini Gemini formatına dönüştür ---
        history = []
        for msg in st.session_state.chat_history[-25:]:
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

        # --- 2) Kullanıcının yeni mesajı ---
        new_parts = [{"text": user_message}]

        # --- 3) Eğer görsel yüklüyse ekle ---
        if user_image:
            new_parts.append({
                "inline_data": {
                    "mime_type": "image/png",
                    "data": base64.b64encode(user_image).decode("utf-8")
                }
            })

        user_turn = {
            "role": "user",
            "parts": new_parts
        }

        full_prompt = history + [user_turn]

        # --- 4) Gemini model ---
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(full_prompt)

        if hasattr(response, "text"):
            return response.text

        return "Bir yanıt üretemedim."

    except Exception as e:
        print("General Chat Error:", e)
        return "💥 Üzgünüm, şu anda genel chat yanıt veremiyor."


# ==========================================================
# A4 — GÖRSEL OLUŞTURMA MOTORU (Gemini Flash Image)
# ==========================================================

def gemini_generate_image(prompt: str, size: str = "1024x1024"):
    """
    Gemini Flash image generator
    - DALL·E benzeri yüksek kaliteli üretim
    - Genel Chat içinde otomatik tetiklenir
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        result = model.generate_image(
            prompt=prompt,
            size=size,
        )
        return result._image  # PNG bytes
    except Exception as e:
        print("Gemini Image Error:", e)
        return None


# ==========================================================
# A4 — GÖRSEL OLUŞTURMA İSTEĞİ ALGILAYICI (AUTO DETECT)
# ==========================================================

IMAGE_TRIGGER_WORDS = [
    "görsel oluştur", "resim oluştur", "foto üret",
    "bir görsel çiz", "image create", "generate image",
    "bana bir tasarım yap", "logo yap", "arka plan üret",
]


def is_image_generation_request(msg: str) -> bool:
    msg = msg.lower()
    return any(t in msg for t in IMAGE_TRIGGER_WORDS)


# ==========================================================
# A4 — GENEL CHAT ANA HANDLER
# ==========================================================

def handle_general_chat(user_message: str):
    """
    Genel Chat UI → Motor bağlayıcı.
    Bu fonksiyon şunları yapar:
        ✔ Görsel üretim isteği algılar (Flash)
        ✔ Normal sohbeti Gemini 1.5 Pro’ya yollar
        ✔ Görsel analiz destekler
        ✔ Sohbet geçmişini yönetir
    """

    # 1) Kullanıcı mesajını geçmişe kaydet
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_message
    })

    with st.chat_message("user"):
        st.write(user_message)

    # 2) Kullanıcı görsel üretmek mi istiyor?
    if is_image_generation_request(user_message):
        with st.chat_message("assistant"):
            st.write("🎨 Görsel oluşturuluyor...")

        img_bytes = gemini_generate_image(user_message)

        if img_bytes:
            st.image(img_bytes, caption="✨ Gemini 1.5 Flash tarafından üretildi", width=350)
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": "(Görsel üretildi)"
            })
            return
        else:
            with st.chat_message("assistant"):
                st.write("⚠️ Görsel oluşturulamadı, lütfen tekrar deneyin.")
            return

    # 3) Normal metin + görsel analizi sohbeti
    ai_answer = gemini_general_chat(
        user_message,
        st.session_state.chat_image
    )

    with st.chat_message("assistant"):
        st.write(ai_answer)

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": ai_answer
    })
# ==========================================================
# A5 — GPT SYSTEM TALİMATI (E-Ticaret + Danışmanlık Persona)
# ==========================================================

def build_system_talimati(profile: Literal["ecom", "consult"]) -> str:

    if profile == "ecom":
        return """
Sen Qelyon AI'nın E-Ticaret Uzmanı modundasın.
Görevlerin:

1) Ürün açıklaması (SEO uyumlu, profesyonel, ikna edici)
2) Ürünün öne çıkan 5 faydasını yaz
3) Kutu içeriği oluştur
4) Hedef kitle analizi yap
5) Kullanım önerileri üret
6) Ürüne özel CTA (satın almaya yönlendiren)
7) Ürün görseli varsa analiz et, metne entegre et
8) Ürün için A/B testli başlık varyantları oluştur
9) Trendyol için akıllı etiket algoritması çalıştır
10) Fiyat psikolojisi optimizasyonu önerileri ver
11) Ürün varyantlarını belirle (renk, beden, kapasite, model)
12) Müşteri yorumlarını analiz edip memnuniyet/şikayet temalarını çıkar
13) Sosyal medya reklam metinleri üret (Meta, TikTok, Instagram)
14) Marka hikâyesi yaz
15) İçerikleri Türkçe ve profesyonel bir tonda oluştur

DİKKAT:
- Gereksiz uzunluk yok, doğrudan ticari fayda odaklı yaz.
- Ürün görseli varsa mutlaka analiz ederek davran.
- PDF veya doküman varsa içeriğini işine dahil et.
- Qelyon AI kimliğinden sapma: YASAK.
"""
    
    # ------------------------------------------------------

    if profile == "consult":
        return """
Sen Qelyon AI'nın Danışmanlık Uzmanı modundasın.
Uzmanlık alanların:
- İş geliştirme
- Marka konumlandırma
- Finansal iyileştirme
- Operasyonel verimlilik
- Pazarlama stratejisi
- Dijital dönüşüm
- SWOT + rakip analizi
- KPI çıkarımı
- Yol haritası oluşturma

Görevlerin:
1) Kullanıcının iş modelini analiz et
2) Sektöre özel strateji öner
3) KPI ve hedef sistemi çıkar
4) SWOT analizi yap
5) Adım adım gelişim planı oluştur
6) Gerektiğinde gelir modeli öner
7) İş fikri validasyonu yap
8) PDF veya doküman varsa analiz et, çıktıya dahil et
9) Görsel varsa içgörü üret (ör: mağaza fotoğrafı, ürün, afiş)

Kimlik:
“Qelyon AI olarak, profesyonel danışmanlık ve veri destekli içgörülerle iş hedeflerine ulaşmanı hızlandırıyorum.”

Tarz:
- Kesin
- Analitik
- Stratejik
- Gereksiz hikâye yok, tamamen iş odaklı.
"""

    return "Qelyon AI sistem talimatı uygulanamadı."
# ==========================================================
# A5 — IDENTITY INTERCEPTOR (Qelyon AI KİMLİK SİSTEMİ)
# ==========================================================

def custom_identity_interceptor(msg: str) -> Optional[str]:
    msg_low = msg.lower()

    if any(x in msg_low for x in ["kimsin", "sen neysin", "kim yapt", "kim geliştirdi"]):
        return "Ben Qelyon AI'yım. Hibrit bir mimari kullanıyorum: Gemini Vision + GPT-4o. Qelyon AI ekibi tarafından geliştirildim."

    if "openai" in msg_low:
        return "Hayır, ben OpenAI değilim. GPT-4o teknolojisini kullanıyorum ama Qelyon AI'ya özel yeteneklerle genişletildim."

    if "ne iş yaparsın" in msg_low or "görevin ne" in msg_low:
        return "Qelyon AI olarak, profesyonel danışmanlık ve veri destekli içgörülerle iş hedeflerine ulaşmanı hızlandırıyorum."

    return None
# ==========================================================
# A5 — UTILITY INTERCEPTOR (Zaman + Hava + PDF + Görsel)
# ==========================================================

def custom_utility_interceptor(msg: str) -> Optional[str]:
    m = msg.lower()

    # Saat
    if "saat" in m or "kaç" in m:
        return time_answer()

    # Hava durumu
    if "hava" in m or "hava durumu" in m:
        city = DEFAULT_CITY
        return get_weather(city)

    # PDF otomatik algı
    if st.session_state.chat_image and msg.strip() in ["pdf", "pdf analizi", "analiz et"]:
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=st.session_state.chat_image, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()

            return f"📄 PDF Analizi:\n{text[:2000]}..."
        except:
            return "PDF içerği okunamadı."

    return None
# ==========================================================
# A5 — GPT-4o ANA ASİSTAN MOTORU
# ==========================================================

def gpt_assistant(profile: Literal["ecom", "consult"]) -> str:
    try:
        system_msg = build_system_talimati(profile)

        msgs = [{"role": "system", "content": system_msg}]
        for m in st.session_state.chat_history[-20:]:
            msgs.append({
                "role": m["role"],
                "content": m["content"]
            })

        client = OpenAI(api_key=OPENAI_API_KEY)

        res = client.chat.completions.create(
            model="gpt-4o",
            messages=msgs,
            temperature=0.3,
            max_tokens=1800,
        )

        return res.choices[0].message.content

    except Exception as e:
        print("GPT Assist Error:", e)

        # Fallback
        return "Şu anda GPT-4o yanıt veremiyor. Birkaç dakika sonra tekrar deneyin."
# ==========================================================
# A5 — GPT ASİSTANI UI ROUTER
# ==========================================================

def handle_gpt_assistant(profile: Literal["ecom", "consult"], user_message: str):
    if not user_message:
        return

    # 1) Kimlik veya yardımcı intercept
    ident = custom_identity_interceptor(user_message)
    util = custom_utility_interceptor(user_message)

    if ident:
        with st.chat_message("assistant"): st.write(ident)
        st.session_state.chat_history.append({"role": "assistant", "content": ident})
        return

    if util:
        with st.chat_message("assistant"): st.write(util)
        st.session_state.chat_history.append({"role": "assistant", "content": util})
        return

    # 2) Normal GPT-4o cevabı
    with st.chat_message("assistant"):
        with st.spinner("Qelyon AI düşünüyor..."):
            answer = gpt_assistant(profile)
            st.write(answer)

    st.session_state.chat_history.append({"role": "assistant", "content": answer})
# ==========================================================
# A6 — MOD SEÇİMİ + GENEL CHAT (Gemini) + GPT ASİSTAN UI
# ==========================================================

# Başta A1'de şunların tanımlı olduğunu varsayıyorum:
# - st.session_state.mode  (varsayılan: "📸 Stüdyo Modu")
# - st.session_state.chat_history
# - st.session_state.studio_result
# Bu bölüm, sadece chat modlarını yönetir.


# ---------------------------------------------
# 🔀 1) Üç Modluk Üst Menü (Genel / Ecom / Consult)
# ---------------------------------------------
def render_main_modes():
    st.markdown("### 🤖 Qelyon AI Mod Seçimi")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(
            "💬 Genel Chat (Gemini 1.5 Pro)",
            use_container_width=True,
            type="primary" if st.session_state.mode == "GENERAL_CHAT" else "secondary",
        ):
            st.session_state.mode = "GENERAL_CHAT"
            st.session_state.chat_history = [
                {
                    "role": "assistant",
                    "content": "Merhaba! Ben Qelyon AI. Bu modda Gemini 1.5 Pro ile genel sohbet, görsel analizi ve görsel oluşturma yapabilirsin. ✨",
                }
            ]
            st.session_state.chat_image = None
            st.rerun()

    with col2:
        if st.button(
            "🛒 E-Ticaret Asistanı (GPT-4o)",
            use_container_width=True,
            type="primary" if st.session_state.mode == "ECOM" else "secondary",
        ):
            st.session_state.mode = "ECOM"
            st.session_state.chat_history = [
                {
                    "role": "assistant",
                    "content": "E-Ticaret Asistanı aktif! Ürününle ilgili bilgileri paylaş, birlikte profesyonel açıklamalar ve stratejiler oluşturalım. 🛒",
                }
            ]
            st.session_state.chat_image = None
            st.rerun()

    with col3:
        if st.button(
            "💼 Danışmanlık Asistanı (GPT-4o)",
            use_container_width=True,
            type="primary" if st.session_state.mode == "CONSULT" else "secondary",
        ):
            st.session_state.mode = "CONSULT"
            st.session_state.chat_history = [
                {
                    "role": "assistant",
                    "content": "Danışmanlık Asistanı aktif! İş modelini, hedeflerini ve sorunlarını anlat; sana stratejik bir yol haritası çıkaracağım. 💼",
                }
            ]
            st.session_state.chat_image = None
            st.rerun()

    st.divider()


# ---------------------------------------------
# 💬 2) GENEL CHAT UI (Gemini 1.5 Pro + Flash)
# ---------------------------------------------
def general_chat_ui():
    st.markdown("### 💬 Qelyon AI — Genel Chat (Gemini)")
    st.caption("Gemini 1.5 Pro & Flash ile metin, görsel analizi ve görsel oluşturma yapabilirsin.")

    # --- Mesaj geçmişi ---
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # --- Dosya yükleme (görsel / pdf) ---
    upload = st.file_uploader(
        "Görsel / PDF yükle (isteğe bağlı)",
        type=["png", "jpg", "jpeg", "webp", "pdf"],
        key="general_upload",
    )

    if upload is not None:
        file_bytes = upload.read()
        # Hem eski isim hem yeni isim uyumlu olsun diye ikisini de set ediyoruz
        st.session_state.chat_image = file_bytes
        st.session_state.uploaded_chat_image = file_bytes
        st.success("📎 Dosya yüklendi! Mesajında bu dosyadan bahsedebilirsin.")

    # --- Kullanıcı mesajı ---
    user_msg = st.chat_input("Mesajını yaz...")

    if user_msg:
        # Güvenlik filtresi
        mod = moderate_text(user_msg)
        st.session_state.chat_history.append({"role": "user", "content": user_msg})

        with st.chat_message("user"):
            st.write(user_msg)

        if mod:
            with st.chat_message("assistant"):
                st.write(mod)
            st.session_state.chat_history.append({"role": "assistant", "content": mod})
            return

        # Gemini tarafına yönlendir
        handle_general_chat(user_msg)


# ---------------------------------------------
# 🛒 3) E-TİCARET ASİSTANI UI (GPT-4o)
# ---------------------------------------------
def ecom_chat_ui():
    st.markdown("### 🛒 Qelyon AI — E-Ticaret Asistanı (GPT-4o)")
    st.caption("Ürün açıklamaları, SEO başlıklar, etiketler ve kampanya metinleri için kullan.")

    # Mesaj geçmişi
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # İsteğe bağlı görsel / pdf yükleme
    upload = st.file_uploader(
        "Ürün görseli veya PDF yükle (opsiyonel)",
        type=["png", "jpg", "jpeg", "webp", "pdf"],
        key="ecom_upload",
    )
    if upload is not None:
        file_bytes = upload.read()
        st.session_state.chat_image = file_bytes
        st.session_state.uploaded_chat_image = file_bytes
        st.success("📎 Dosya yüklendi! Ürün açıklamasında bu dosyaya referans verebilirsin.")

    user_msg = st.chat_input("Ürün veya ihtiyacını anlat...")

    if user_msg:
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.write(user_msg)

        handle_gpt_assistant("ecom", user_message=user_msg)


# ---------------------------------------------
# 💼 4) DANIŞMANLIK ASİSTANI UI (GPT-4o)
# ---------------------------------------------
def consult_chat_ui():
    st.markdown("### 💼 Qelyon AI — Danışmanlık Asistanı (GPT-4o)")
    st.caption("İş modeli, büyüme stratejisi, KPI/OKR ve operasyonel verimlilik için kullan.")

    # Mesaj geçmişi
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Opsiyonel doküman/görsel yükleme
    upload = st.file_uploader(
        "Rapor, PDF veya görsel yükle (opsiyonel)",
        type=["png", "jpg", "jpeg", "webp", "pdf"],
        key="consult_upload",
    )
    if upload is not None:
        file_bytes = upload.read()
        st.session_state.chat_image = file_bytes
        st.session_state.uploaded_chat_image = file_bytes
        st.success("📎 Dosya yüklendi! Analiz yaparken bu dosyadan bahsedebilirsin.")

    user_msg = st.chat_input("İşini veya sorunu anlat...")

    if user_msg:
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.write(user_msg)

        handle_gpt_assistant("consult", user_message=user_msg)


# ---------------------------------------------
# 🚦 5) ANA ROUTER — Hangi chat UI çalışacak?
# ---------------------------------------------
def run_assistant_router():
    # Üstte mod butonlarını çiz
    render_main_modes()

    # Sonra seçilen moda göre UI aç
    if st.session_state.mode == "GENERAL_CHAT":
        general_chat_ui()

    elif st.session_state.mode == "ECOM":
        ecom_chat_ui()

    elif st.session_state.mode == "CONSULT":
        consult_chat_ui()

    # Eğer mode başka bir şey ise (örneğin 📸 Stüdyo Modu),
    # burada hiçbir şey yapma; stüdyo kodun kendi bloğunda çalışsın.
    # ==========================================================
# A7 — 📸 QELYON AI STÜDYO MODU (FINAL v8)
# ==========================================================

def render_studio_mode():
    st.markdown("## 📸 Qelyon AI — Stüdyo Modu")
    st.caption("Ürünlerin için profesyonel arka plan, ışık, gölge ve sahne oluşturma modu.")

    # ------------------------
    # 1) Görsel yükleme alanı
    # ------------------------
    uploaded = st.file_uploader(
        "🎨 Ürün fotoğrafını yükle",
        type=["png", "jpg", "jpeg", "webp"],
        key="studio_upload",
    )

    if uploaded is not None:
        img = Image.open(uploaded).convert("RGBA")
        st.image(img, caption="Yüklenen Görsel", width=350)
        st.session_state.studio_source = img

    # Eğer henüz görsel yoksa devam etme
    if "studio_source" not in st.session_state:
        st.info("Başlamak için bir ürün görseli yükle.")
        return

    img = st.session_state.studio_source

    # ------------------------
    # 2) Preset seçimleri
    # ------------------------
    st.markdown("### 🎛 Hazır Temalar")

    preset_name = st.selectbox(
        "Bir tema seç:",
        list(PRESETS.keys()),
        index=0,
    )

    # ------------------------
    # 3) Profesyonel AI sahne oluşturma
    # ------------------------
    st.markdown("### ✨ AI Sahne Oluşturma (Opsiyonel)")

    ai_prompt = st.text_area(
        "Profesyonel sahne (örn: 'lüx stüdyo ışığı, soft shadow, minimal set')",
        placeholder="Buraya yazarsan Gemini Vision özel sahne oluşturur.",
    )

    generate_ai_scene = st.button("✨ AI Sahne Oluştur", type="primary")

    # ------------------------
    # 4) İşlem butonu
    # ------------------------
    apply_preset_btn = st.button("🎨 Temayı Uygula")

    result = None

    # ------------------------
    # 5) Temayı uygula (lokal render)
    # ------------------------
    if apply_preset_btn:
        with st.spinner("Temanız işleniyor..."):
            result = apply_preset(img, PRESETS[preset_name])
            st.session_state.studio_result = result

    # ------------------------
    # 6) AI sahne oluştur
    # ------------------------
    if generate_ai_scene and ai_prompt.strip():
        with st.spinner("AI sahne oluşturuluyor... (Gemini Vision)"):
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            bytes_img = buffered.getvalue()

            ai_img_bytes = gemini_edit_scene(ai_prompt, bytes_img)

            if ai_img_bytes:
                result = Image.open(io.BytesIO(ai_img_bytes)).convert("RGBA")
                st.session_state.studio_result = result
            else:
                st.error("AI sahne oluşturulamadı. Lütfen yeniden deneyin.")

    # ------------------------
    # 7) Sonuç görüntüleme
    # ------------------------
    if st.session_state.studio_result is not None:
        st.markdown("### 📤 Çıktı")

        st.image(st.session_state.studio_result, width=512)

        # İndirilebilir link
        output_buffer = io.BytesIO()
        st.session_state.studio_result.save(output_buffer, format="PNG")
        st.download_button(
            "📥 Çıktıyı İndir (PNG)",
            data=output_buffer.getvalue(),
            file_name="qelyon_studio_output.png",
            mime="image/png",
        )
# ==========================================================
# A8 — 📄 PDF & 🖼 Görsel OCR + Belge Analiz Motoru (Gemini 1.5 Pro)
# ==========================================================

import mimetypes

def guess_mime_type(filename: str, default: str = "application/octet-stream") -> str:
    """
    Dosya adına göre MIME type tahmini.
    Örn:
      - .pdf  -> application/pdf
      - .png  -> image/png
      - .jpg  -> image/jpeg
    """
    mime, _ = mimetypes.guess_type(filename)
    return mime or default


def gemini_analyze_document(
    file_bytes: bytes,
    filename: str,
    user_instruction: str = "Bu dosyayı profesyonelce özetle ve önemli maddeleri çıkar.",
) -> str:
    """
    PDF, PNG, JPG gibi dosyaları Gemini 1.5 Pro ile okur (OCR + anlamlandırma).
    - PDF ise: içeriği okur, metni anlar, özetler.
    - Görsel ise: görsel üzerindeki yazıları (OCR) + görsel içeriğini analiz eder.
    """

    if not file_bytes:
        return "Dosya içeriği boş görünüyor."

    mime_type = guess_mime_type(filename)

    # Gemini'ye gönderilecek parça
    file_part = {
        "mime_type": mime_type,
        "data": file_bytes,
    }

    # Sistem promptu + kullanıcının talimatı
    prompt = (
        "Sen Qelyon AI doküman analiz uzmanısın. "
        "PDF, resim veya taranmış belge içeriğini dikkatlice okur, "
        "önemli kısımları net ve anlaşılır bir şekilde özetlersin. "
        "Maddeler halinde kritik başlıkları ve aksiyon alınabilir önerileri çıkar.\n\n"
        f"Kullanıcı talimatı: {user_instruction}"
    )

    try:
        model = genai.GenerativeModel(GEMINI_TEXT_MODEL)
        response = model.generate_content([prompt, file_part])

        if hasattr(response, "text") and response.text:
            return response.text.strip()

        return "Dosya analiz edildi fakat metin cevap üretilemedi."
    except Exception as e:
        print("Gemini Document Analyze Error:", e)
        return "Belge analizinde bir hata oluştu. Lütfen daha sonra tekrar dene."


# ----------------------------------------------------------
# A8 — 🔌 Genel Chat / Diğer Modlarda Kullanım Örneği (opsiyonel)
# ----------------------------------------------------------

def analyze_uploaded_file_in_chat(user_message: str) -> str:
    """
    General Chat içinde:
      - Kullanıcı PDF / görsel yüklediyse
      - 'bu pdfi özetle', 'bu görseli analiz et', 'bu dosyayı incele' gibi bir şey yazdıysa
    → Bu fonksiyon çağrılıp Gemini belge analiz çalıştırılabilir.

    Bunu direkt general_chat_ui veya başka bir UI fonksiyonundan çağırabilirsin.
    """

    if "chat_image" not in st.session_state or st.session_state.chat_image is None:
        return "Analiz edilecek yüklü bir dosya bulamadım. Lütfen önce bir PDF veya görsel yükle."

    triggers = [
        "pdfi özetle",
        "pdf'i özetle",
        "pdf özetle",
        "bu dosyayı özetle",
        "bu dosyayı analiz et",
        "belgeyi analiz et",
        "dokümanı analiz et",
        "bu görseli analiz et",
        "bu resmi analiz et",
        "dosyayı incele",
    ]

    if not any(t in user_message.lower() for t in triggers):
        # Kullanıcının isteği doğrudan doküman analizi değilse, normal chat akışı devam edebilir.
        return ""

    # Buraya geldiğimizde → gerçekten belge analizi isteniyor
    file_bytes = st.session_state.chat_image
    filename = getattr(st.session_state, "chat_filename", "dosya")

    # Kullanıcı talimatı (isteğe bağlı geliştirilebilir)
    user_instruction = user_message

    result = gemini_analyze_document(file_bytes, filename, user_instruction)
    return result
upload = st.file_uploader(
    "Görsel / PDF / Dosya ekle",
    type=["png", "jpg", "jpeg", "webp", "pdf"],
    key="general_upload"
)

if upload:
    st.session_state.chat_image = upload.read()
    st.session_state.chat_filename = upload.name  # 🔹 A8 için önemli
    st.success("Dosya yüklendi!")
prompt = st.chat_input("Bir mesaj yaz...")

if prompt:
    # önce doküman analizi tetikleniyor mu diye bak
    doc_answer = analyze_uploaded_file_in_chat(prompt)
    if doc_answer:
        with st.chat_message("assistant"):
            st.write(doc_answer)
        st.session_state.chat_history.append({"role": "assistant", "content": doc_answer})
    else:
        # normal Gemini general chat akışı (senin mevcut kodun)
        handle_general_chat(prompt)


