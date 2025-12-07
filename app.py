"""
File: app.py
ALPTECH AI Stüdyo — v4.0 (E-Ticaret Pro, GPT-5.1 Ready)
"""

from __future__ import annotations

import base64
import re
import traceback
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

import requests
import streamlit as st
from openai import OpenAI
from PIL import Image, ImageOps, ImageFilter
from rembg import remove

# ===========================
# GÜVENLİ AYARLAR & KONFIG
# ===========================
if "OPENAI_API_KEY" in st.secrets:
    SABIT_API_KEY = st.secrets["OPENAI_API_KEY"]
else:
    SABIT_API_KEY = None
    st.warning("⚠️ OPENAI_API_KEY tanımlı değil. Sohbet devre dışı.")

DEFAULT_MODEL = st.secrets.get("OPENAI_MODEL", "gpt-5.1")

# OpenWeather
WEATHER_API_KEY = st.secrets.get("WEATHER_API_KEY", "5f9ee20a060a62ba9cb79d4a048395d9")
WEATHER_DEFAULT_CITY = st.secrets.get("WEATHER_DEFAULT_CITY", "İstanbul")

# Logo yükleme
LOGO_PATH = "ALPTECHAI.png"
try:
    with open(LOGO_PATH, "rb") as lf:
        LOGO_B64 = base64.b64encode(lf.read()).decode("utf-8")
except:
    LOGO_B64 = None

st.set_page_config(
    page_title="ALPTECH AI Stüdyo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)
# ===========================
# THEME & CSS
# ===========================
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


def apply_apple_css(tema):
    st.markdown(
        f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    body, html, .stApp {{
        font-family: -apple-system, BlinkMacSystemFont, "Inter";
        background: {tema['bg']};
        color: {tema['text']};
    }}

    #MainMenu, footer, header, [data-testid="stToolbar"] {{
        visibility: hidden !important;
    }}

    .block-container {{
        padding-top: 1rem;
        padding-bottom: 4rem;
        max-width: 1280px;
    }}

    .image-container {{
        background: {tema['card_bg']};
        backdrop-filter: blur(14px);
        border-radius: 18px;
        padding: 14px;
        border: 1px solid {tema['border']};
        box-shadow: 0 6px 24px rgba(2,6,23,0.12);
    }}

    .stButton>button {{
        background-color: {tema['accent']} !important;
        color: white !important;
        border-radius: 12px !important;
        padding: 9px 16px !important;
        font-weight: 600;
    }}

    .stButton>button:hover {{
        background-color: {tema['button_hover']} !important;
        transform: translateY(-2px);
    }}

    /* Chat balonları */
    [data-testid="stChatMessage"] {{
        border-radius: 16px;
        padding: 6px 12px;
        background: {tema['card_bg']};
        border: 1px solid {tema['border']};
    }}

    [data-testid="stChatInput"] textarea {{
        background: {tema['input_bg']} !important;
        color: {tema['text']} !important;
    }}

    textarea::placeholder {{
        color: {tema['subtext']} !important;
    }}
    </style>
    """,
        unsafe_allow_html=True,
    )
def inject_voice_js():
    st.markdown("""
<script>
(function() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) { return; }

  function addMic() {
    const root = window.parent.document.querySelector('[data-testid="stChatInput"]');
    if (!root) return;

    if (root.querySelector('#mic-btn')) return;

    const textarea = root.querySelector('textarea');
    if (!textarea) return;

    const btn = document.createElement('button');
    btn.id = 'mic-btn';
    btn.innerText = '🎤';
    btn.style.marginLeft = '8px';
    btn.style.borderRadius = '999px';
    btn.style.background = '#0a84ff';
    btn.style.color = 'white';
    btn.style.border = 'none';
    btn.style.padding = '4px 10px';
    btn.style.cursor = 'pointer';

    const rec = new SpeechRecognition();
    rec.lang = 'tr-TR';
    rec.onresult = (event) => {
      const text = event.results[0][0].transcript;
      textarea.value = textarea.value + " " + text;
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    };

    btn.onclick = () => rec.start();
    root.appendChild(btn);
  }

  setInterval(addMic, 1500);
})();
</script>
""", unsafe_allow_html=True)
# SESSION STATE
if "sonuc_gorseli" not in st.session_state:
    st.session_state.sonuc_gorseli = None

if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {}

if "current_session" not in st.session_state:
    st.session_state.current_session = "Oturum 1"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Merhaba! Hangi modu kullanmak istersin?"}
    ]
# ===========================
# ANALYTICS HELPER
# ===========================
def inc_stat(key: str, step: int = 1):
    if "analytics" not in st.session_state:
        return
    if key not in st.session_state.analytics:
        st.session_state.analytics[key] = 0
    st.session_state.analytics[key] += step


# ===========================
# E-TİCARET TEMA & PRESET LİSTESİ
# ===========================
TEMA_LISTESI = {
    "🧹 Arka Planı Kaldır (Şeffaf)": "ACTION_TRANSPARENT",
    "⬜ Saf Beyaz Fon (E-ticaret)": "ACTION_WHITE",
    "⬛ Saf Siyah Fon (Premium)": "ACTION_BLACK",
    "🍦 Krem / Bej Soft Fon": "ACTION_BEIGE",

    # --- Profesyonel katalog presetleri ---
    "🛒 Katalog Stüdyo (Beyaz & Yumuşak Gölge)": (
        "Clean e-commerce catalog shot of the object on a pure white seamless background. "
        "Soft diffused lighting, subtle shadow, Amazon listing style, ultra-sharp."
    ),
    "📦 Ürün Kartı (Soft Shadow)": (
        "High-end product photo on a light grey / white gradient background. "
        "Soft shadow, centered composition, premium cosmetic style."
    ),

    # --- Sosyal medya presetleri ---
    "📲 Instagram Postu 1080×1350": (
        "Instagram 4:5 vertical post. Modern gradient background, soft shadows, "
        "product centered, vibrant but clean style."
    ),
    "📱 Story 1080×1920": (
        "16:9 vertical Instagram story layout. Smooth gradient background, space left "
        "top & bottom for text, bright and engaging design."
    ),
    "🎯 Kampanya Reklamı": (
        "Advertising key visual with the object centered. Dynamic lighting, strong "
        "contrast, clean gradient, empty negative space for text."
    ),

    # --- YouTube / reklam ---
    "▶️ YouTube Thumbnail (16:9)": (
        "Cinematic lighting, strong contrast, bold colors, product on the right side "
        "with empty space on the left for title text."
    ),

    # --- Hacimsel presetler ---
    "🌫 Nötr Gri Fon": (
        "Minimalistic product photo on a neutral grey seamless background. "
        "Softbox lighting, subtle vignette, professional."
    ),
    "💡 3-Nokta Stüdyo Işığı": (
        "High-end commercial product photo using 3-point lighting (key, fill, rim). "
        "Infinity curve background, ultra-sharp."
    ),
    "🌑 Karanlık Stüdyo": (
        "Dark matte black background, dramatic rim lighting, premium luxury aesthetic."
    ),

    # --- Lifestyle ortamlar ---
    "🏛️ Mermer Zemin (Lüks)": (
        "Product on polished white Carrara marble. Soft cinematic lighting, shallow DOF."
    ),
    "🪵 Ahşap Masa (Doğal)": (
        "Product on rustic oak wooden table, side daylight, cozy blurred background."
    ),
    "🧱 Beton Yüzey (Modern)": (
        "Minimal product on textured concrete surface with hard directional light."
    ),
    "🛋️ İpek Kumaş (Zarif)": (
        "Object resting on champagne silk fabric. Soft reflections, editorial style."
    ),
    "🏠 Modern Salon": (
        "Lifestyle shot in a Scandinavian living room with blurred decor background."
    ),
    "🍽 Mutfak Tezgahı": (
        "Bright kitchen countertop, soft daylight, clean food-related composition."
    ),
    "🛁 Banyo Tezgahı": (
        "Cosmetic product on bathroom countertop, blurred mirror reflections."
    ),
    "🌿 Doğal Dış Mekan (Yeşil Arka Plan)": (
        "Outdoor shot with blurred greenery, natural daylight, organic mood."
    ),
    "🌅 Gün Batımı Gradient": (
        "Warm gradient background in orange/pink/purple sunset tones."
    ),
    "🍬 Pastel Minimalist Gradient": (
        "Pastel pink/lilac/blue gradient, subtle soft shadow, clean minimal style."
    ),
}
# ===========================
# TÜRKİYE SAATİ (WorldTimeAPI)
# ===========================
def fetch_tr_time() -> datetime:
    try:
        r = requests.get("http://worldtimeapi.org/api/timezone/Europe/Istanbul", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return datetime.fromisoformat(data["datetime"])
    except:
        pass

    # Fallback — her durumda çalışır
    return datetime.now(ZoneInfo("Europe/Istanbul"))


def turkce_zaman_getir() -> str:
    t = fetch_tr_time()
    gunler = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]
    aylar  = ["","Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz",
              "Ağustos","Eylül","Ekim","Kasım","Aralık"]

    return f"{t.day} {aylar[t.month]} {t.year}, {gunler[t.weekday()]}, Saat {t.strftime('%H:%M')}"


def get_time_answer():
    t = fetch_tr_time()
    return f"📅 Tarih: {t.strftime('%d.%m.%Y')} — ⏱ Saat: {t.strftime('%H:%M')}"
# ===========================
# ŞEHİR AYIKLAMA
# ===========================
def extract_city_from_message(msg: str) -> str | None:
    m = msg.lower()
    m = re.sub(r"[^\wçğıöşü\s]", " ", m)
    toks = [t for t in m.split() if t]

    if not toks:
        return None

    # “Ankara'da hava nasıl” → Ankara
    possible = toks[0]
    for suf in ["'da","'de","'ta","'te","da","de","ta","te"]:
        if possible.endswith(suf):
            possible = possible[:-len(suf)]

    return possible.strip() or None


# ===========================
# GEO → Koordinat bul
# ===========================
def resolve_city_to_coords(city: str, limit: int = 1):
    try:
        url = (
            "http://api.openweathermap.org/geo/1.0/direct"
            f"?q={city},TR&limit={limit}&appid={WEATHER_API_KEY}"
        )
        r = requests.get(url, timeout=5)
        data = r.json()
        if not data:
            return None
        return float(data[0]["lat"]), float(data[0]["lon"])
    except:
        return None
def get_weather_answer(city: str | None = None):
    inc_stat("weather_queries")

    if city is None:
        city = WEATHER_DEFAULT_CITY

    coords = resolve_city_to_coords(city)
    if not coords:
        return f"'{city}' için hava durumu bulamadım. Başka bir şehir söyleyebilirsin."

    lat, lon = coords

    try:
        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric&lang=tr"
        )
        r = requests.get(url, timeout=5)
        data = r.json()

        durum = data["weather"][0]["description"].capitalize()
        t = data["main"]["temp"]
        his = data["main"].get("feels_like", t)
        nem = data["main"]["humidity"]

        return (
            f"📍 **{city.title()}**\n"
            f"🌡️ Sıcaklık: **{t:.1f}°C** (Hissedilen {his:.1f}°C)\n"
            f"☁️ Durum: {durum}\n"
            f"💧 Nem: %{nem}\n"
        )
    except:
        return "Hava durumu API şu an yanıt vermiyor. Biraz sonra tekrar deneyebilirsin."
def get_weather_forecast_answer(city: str | None = None, days=7):
    inc_stat("forecast_queries")

    if city is None:
        city = WEATHER_DEFAULT_CITY

    coords = resolve_city_to_coords(city)
    if not coords:
        return f"{city} için konum çözülemedi."

    lat, lon = coords

    try:
        url = (
            "https://api.openweathermap.org/data/3.0/onecall"
            f"?lat={lat}&lon={lon}&exclude=minutely,hourly,alerts"
            f"&appid={WEATHER_API_KEY}&units=metric&lang=tr"
        )
        r = requests.get(url, timeout=5)
        data = r.json()

        lines = [f"📍 **{city.title()} için 7 Günlük Hava Tahmini:**\n"]
        for d in data["daily"][:days]:
            dt = datetime.fromtimestamp(d["dt"], ZoneInfo("Europe/Istanbul"))
            tarih = dt.strftime("%d.%m.%Y %a")

            lines.append(
                f"- **{tarih}** — {d['weather'][0]['description'].capitalize()}, "
                f"min {d['temp']['min']:.1f}°C / max {d['temp']['max']:.1f}°C"
            )

        return "\n".join(lines)

    except:
        return "7 günlük hava tahmini şu anda alınamıyor."
BAD_PATTERNS = [
    r"(?i)orospu", r"(?i)siktir", r"(?i)amk", r"(?i)ibne",
    r"(?i)tecavüz", r"(?i)uyuşturucu", r"(?i)bomba yap",
]

def moderate_content(text: str):
    for p in BAD_PATTERNS:
        if re.search(p, text):
            return (
                "Bu isteğe güvenlik nedeniyle yanıt veremiyorum. "
                "Dilersen daha farklı bir konuda yardımcı olabilirim. 🙂"
            )
    return None
def custom_identity_interceptor(msg: str):
    m = msg.lower()
    triggers = [
        "seni kim yaptı", "kim geliştirdi", "who created you", "who made you",
        "sen kimsin", "kimdesin", "origin"
    ]
    if any(t in m for t in triggers):
        return (
            "Ben **ALPTECH AI** ekibi tarafından geliştirilen profesyonel bir yapay zeka asistanıyım. 🚀\n"
            "E-ticaret içerikleri, ürün açıklamaları, varyant analizi, fiyat stratejileri ve görsel düzenleme konusunda uzmanım."
        )
    return None
def build_system_talimati():
    z = turkce_zaman_getir()
    return f"""
    Senin adın **ALPTECH AI**.

    Uzmanlık alanların:
    - Ürün açıklaması, SEO, satış odaklı metin
    - Ürün faydaları, kutu içeriği, CTA üretimi
    - Trendyol / Hepsiburada / Amazon etiket & başlık üretimi
    - Fiyatlandırma psikolojisi
    - Ürün varyant çıkarımı (renk/beden/kapasite)
    - Yorum analizi (memnuniyet & şikâyet temaları)
    - Markalar için premium marka hikâyesi yazımı
    - Sosyal medya reklam metinleri

    Görseller: gerektiğinde görsel içeriğini analiz ederek ürün özelliklerini çıkar.

    Cevap stilin:
    • Profesyonel ve güven veren
    • Gerektiğinde kısa, gerektiğinde detaylı
    • Hatalı bilgi uydurma
    • Kullanıcı dostu ve sade Türkçe

    Sistem notu: Bu yanıt {z} tarihinde oluşturulmuştur.
    """
"""
File: app.py
ALPTECH AI Stüdyo — FINAL (E-Ticaret Pro)

- Apple-style UI
- Studio + Chat modları
- TR gerçek saat (WorldTimeAPI fallback local)
- OpenWeather: Geo + Current + 7-günlük tahmin (TR şehirleri)
- ALPTECH AI kimlik, güvenlik filtresi
- Chat içinde: '+' ile dosya/görsel yükleme, 🎤 sesle yaz (Web Speech API)
- Sol sidebar: konuşma geçmişi, prompt kütüphanesi, E-Ticaret akıllı şablonları, basit analytics
- GPT-5.1 uyumlu, hata olursa gpt-4o-mini fallback
"""

from __future__ import annotations

import base64
import re
import traceback
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

import requests
import streamlit as st
from openai import OpenAI
from PIL import Image, ImageOps, ImageFilter
from rembg import remove

# ===========================
# GÜVENLİ AYARLAR & KONFIG
# ===========================
if "OPENAI_API_KEY" in st.secrets:
    SABIT_API_KEY = st.secrets["OPENAI_API_KEY"]
else:
    SABIT_API_KEY = None
    st.warning("⚠️ OPENAI_API_KEY tanımlı değil. Sohbet ve AI sahne düzenleme devre dışı.")

# Varsayılan model: gpt-5.1 (secrets içinde değiştirilebilir)
DEFAULT_MODEL = st.secrets.get("OPENAI_MODEL", "gpt-5.1")

# OpenWeather
WEATHER_API_KEY = st.secrets.get("WEATHER_API_KEY", "5f9ee20a060a62ba9cb79d4a048395d9")
WEATHER_DEFAULT_CITY = st.secrets.get("WEATHER_DEFAULT_CITY", "İstanbul")

# Logo dosya yolu (aynı klasörde ALPTECHAI.png olmalı)
LOGO_PATH = "ALPTECHAI.png"
try:
    with open(LOGO_PATH, "rb") as _lf:
        LOGO_B64 = base64.b64encode(_lf.read()).decode("utf-8")
except Exception:
    LOGO_B64 = None

st.set_page_config(
    page_title="ALPTECH AI Stüdyo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===========================
# TEMA & CSS
# ===========================
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
    #MainMenu, footer, header, [data-testid="stToolbar"] {{
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
    .container-header {{
        color: {tema['accent']} !important;
        font-weight: 600;
        font-size: 1.05rem;
        margin-bottom: 6px;
    }}
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

    /* Chat balonları */
    [data-testid="stChatMessage"] {{
        border-radius: 16px;
        padding: 6px 12px;
        backdrop-filter: blur(12px);
        margin-bottom: 10px;
        background: {tema['card_bg']};
        border: 1px solid {tema['border']};
    }}
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] span,
    [data-testid="stChatMessage"] div {{
        color: {tema['text']} !important;
    }}

    /* Chat input text görünür (koyu mod mobil dahil) */
    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInput"] input {{
        background: {tema['input_bg']} !important;
        color: {tema['text']} !important;
        border-radius: 999px !important;
        border: 1px solid {tema['border']} !important;
    }}
    [data-testid="stChatInput"] textarea::placeholder,
    [data-testid="stChatInput"] input::placeholder {{
        color: {tema['subtext']} !important;
        opacity: 1 !important;
    }}

    textarea, input[type="text"] {{
        color: {tema['text']} !important;
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


def inject_voice_js():
    """Web Speech API ile stChatInput içine '🎤' butonu ekler."""
    st.markdown(
        """
<script>
(function() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) { return; }

  function addMicButton() {
    const root = window.parent.document.querySelector('[data-testid="stChatInput"]');
    if (!root) return;
    if (root.querySelector('#alptech-mic-btn')) return;

    const textarea = root.querySelector('textarea');
    if (!textarea) return;

    const btn = document.createElement('button');
    btn.id = 'alptech-mic-btn';
    btn.innerText = '🎤';
    btn.title = 'Sesle yaz (tarayıcı mikrofon izni ister)';
    btn.style.marginLeft = '8px';
    btn.style.borderRadius = '999px';
    btn.style.border = 'none';
    btn.style.cursor = 'pointer';
    btn.style.padding = '4px 10px';
    btn.style.background = '#0a84ff';
    btn.style.color = 'white';
    btn.style.fontSize = '16px';

    const rec = new SpeechRecognition();
    rec.lang = 'tr-TR';
    rec.interimResults = false;
    rec.maxAlternatives = 1;

    rec.onresult = (event) => {
      const text = event.results[0][0].transcript;
      const current = textarea.value;
      textarea.value = current ? (current + ' ' + text) : text;
      textarea.dispatchEvent(new Event('input', {bubbles: true}));
    };

    rec.onerror = (event) => {
      console.log('Speech recognition error', event);
    };

    btn.onclick = (e) => {
      e.preventDefault();
      try { rec.start(); } catch (err) { console.log(err); }
    };

    root.appendChild(btn);
  }

  setInterval(addMicButton, 1500);
})();
</script>
        """,
        unsafe_allow_html=True,
    )

# ===========================
# SESSION STATE
# ===========================
if "sonuc_gorseli" not in st.session_state:
    st.session_state.sonuc_gorseli = None
if "sonuc_format" not in st.session_state:
    st.session_state.sonuc_format = "PNG"

if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {}
if "current_session" not in st.session_state:
    st.session_state.current_session = "Oturum 1"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Merhaba! Hangi modu kullanmak istersin?"}
    ]
if "chat_sessions" in st.session_state and "Oturum 1" not in st.session_state.chat_sessions:
    st.session_state.chat_sessions["Oturum 1"] = st.session_state.chat_history

if "chat_image" not in st.session_state:
    st.session_state.chat_image = None
if "show_upload_panel" not in st.session_state:
    st.session_state.show_upload_panel = False
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

if "app_mode" not in st.session_state:
    st.session_state.app_mode = "📸 Stüdyo Modu (Görsel Düzenleme)"

if "analytics" not in st.session_state:
    st.session_state.analytics = {
        "studio_runs": 0,
        "chat_messages": 0,
        "weather_queries": 0,
        "forecast_queries": 0,
        "uploads": 0,
    }

# ===========================
# ANALYTICS HELPER
# ===========================
def inc_stat(key: str, step: int = 1):
    if "analytics" not in st.session_state:
        return
    if key not in st.session_state.analytics:
        st.session_state.analytics[key] = 0
    st.session_state.analytics[key] += step

# ===========================
# E-TİCARET TEMA & PRESET LİSTESİ
# ===========================
TEMA_LISTESI = {
    "🧹 Arka Planı Kaldır (Şeffaf)": "ACTION_TRANSPARENT",
    "⬜ Saf Beyaz Fon (E-ticaret)": "ACTION_WHITE",
    "⬛ Saf Siyah Fon (Premium)": "ACTION_BLACK",
    "🍦 Krem / Bej Soft Fon": "ACTION_BEIGE",

    "🛒 Katalog Stüdyo (Beyaz & Yumuşak Gölge)": (
        "Clean e-commerce catalog shot of the object on a pure white seamless background. "
        "Soft diffused lighting, subtle shadow, Amazon listing style, ultra-sharp."
    ),
    "📦 Ürün Kartı (Soft Shadow)": (
        "High-end product photo on a light grey / white gradient background. "
        "Soft shadow, centered composition, premium cosmetic style."
    ),

    "📲 Instagram Postu 1080×1350": (
        "Instagram 4:5 vertical post. Modern gradient background, soft shadows, "
        "product centered, vibrant but clean style."
    ),
    "📱 Story 1080×1920": (
        "16:9 vertical Instagram story layout. Smooth gradient background, space left "
        "top & bottom for text, bright and engaging design."
    ),
    "🎯 Kampanya Reklamı": (
        "Advertising key visual with the object centered. Dynamic lighting, strong "
        "contrast, clean gradient, empty negative space for text."
    ),

    "▶️ YouTube Thumbnail (16:9)": (
        "Cinematic lighting, strong contrast, bold colors, product on the right side "
        "with empty space on the left for title text."
    ),

    "🌫 Nötr Gri Fon": (
        "Minimalistic product photo on a neutral grey seamless background. "
        "Softbox lighting, subtle vignette, professional."
    ),
    "💡 3-Nokta Stüdyo Işığı": (
        "High-end commercial product photo using 3-point lighting (key, fill, rim). "
        "Infinity curve background, ultra-sharp."
    ),
    "🌑 Karanlık Stüdyo": (
        "Dark matte black background, dramatic rim lighting, premium luxury aesthetic."
    ),

    "🏛️ Mermer Zemin (Lüks)": (
        "Product on polished white Carrara marble. Soft cinematic lighting, shallow DOF."
    ),
    "🪵 Ahşap Masa (Doğal)": (
        "Product on rustic oak wooden table, side daylight, cozy blurred background."
    ),
    "🧱 Beton Yüzey (Modern)": (
        "Minimal product on textured concrete surface with hard directional light."
    ),
    "🛋️ İpek Kumaş (Zarif)": (
        "Object resting on champagne silk fabric. Soft reflections, editorial style."
    ),
    "🏠 Modern Salon": (
        "Lifestyle shot in a Scandinavian living room with blurred decor background."
    ),
    "🍽 Mutfak Tezgahı": (
        "Bright kitchen countertop, soft daylight, clean food-related composition."
    ),
    "🛁 Banyo Tezgahı": (
        "Cosmetic product on bathroom countertop, blurred mirror reflections."
    ),
    "🌿 Doğal Dış Mekan (Yeşil Arka Plan)": (
        "Outdoor shot with blurred greenery, natural daylight, organic mood."
    ),
    "🌅 Gün Batımı Gradient": (
        "Warm gradient background in orange/pink/purple sunset tones."
    ),
    "🍬 Pastel Minimalist Gradient": (
        "Pastel pink/lilac/blue gradient, subtle soft shadow, clean minimal style."
    ),
}

# ===========================
# ZAMAN & HAVA
# ===========================
def fetch_tr_time() -> datetime:
    try:
        r = requests.get("http://worldtimeapi.org/api/timezone/Europe/Istanbul", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return datetime.fromisoformat(data["datetime"])
    except Exception:
        pass
    return datetime.now(ZoneInfo("Europe/Istanbul"))


def turkce_zaman_getir() -> str:
    t = fetch_tr_time()
    gunler = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]
    aylar  = ["","Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz",
              "Ağustos","Eylül","Ekim","Kasım","Aralık"]
    return f"{t.day} {aylar[t.month]} {t.year}, {gunler[t.weekday()]}, Saat {t.strftime('%H:%M')}"


def get_time_answer() -> str:
    t = fetch_tr_time()
    return f"📅 Tarih: {t.strftime('%d.%m.%Y')} — ⏱ Saat: {t.strftime('%H:%M')}"


def extract_city_from_message(msg: str) -> str | None:
    m = msg.lower()
    m = re.sub(r"[^\wçğıöşü\s]", " ", m)
    toks = [t for t in m.split() if t]
    if not toks:
        return None
    candidate = toks[0]
    for suf in ["'da","'de","'ta","'te","da","de","ta","te"]:
        if candidate.endswith(suf) and len(candidate) > len(suf) + 1:
            candidate = candidate[:-len(suf)]
            break
    return candidate.strip() or None


def resolve_city_to_coords(city: str, limit: int = 1):
    if not WEATHER_API_KEY:
        return None
    try:
        url = (
            "http://api.openweathermap.org/geo/1.0/direct"
            f"?q={city},TR&limit={limit}&appid={WEATHER_API_KEY}"
        )
        r = requests.get(url, timeout=5)
        data = r.json()
        if not data:
            return None
        return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        return None


def get_weather_answer(city: str | None = None) -> str:
    inc_stat("weather_queries")
    if not WEATHER_API_KEY:
        return "Hava durumu API anahtarı olmadığı için şu an hava durumu veremiyorum. 🌤️"

    if city is None:
        city = WEATHER_DEFAULT_CITY

    coords = resolve_city_to_coords(city)
    if not coords:
        return f"'{city}' için hava durumu bulamadım. Başka bir şehir söyleyebilirsin."

    lat, lon = coords
    try:
        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric&lang=tr"
        )
        r = requests.get(url, timeout=5)
        data = r.json()

        durum = data["weather"][0]["description"].capitalize()
        t = data["main"]["temp"]
        his = data["main"].get("feels_like", t)
        nem = data["main"]["humidity"]

        return (
            f"📍 **{city.title()}**\n"
            f"🌡️ Sıcaklık: **{t:.1f}°C** (Hissedilen {his:.1f}°C)\n"
            f"☁️ Durum: {durum}\n"
            f"💧 Nem: %{nem}\n"
        )
    except Exception:
        return "Hava durumu servisine şu an ulaşamıyorum. Biraz sonra tekrar deneyebilirsin."


def get_weather_forecast_answer(city: str | None = None, days: int = 7) -> str:
    inc_stat("forecast_queries")
    if not WEATHER_API_KEY:
        return "Hava durumu API anahtarı olmadığı için şu an tahmin veremiyorum."

    if city is None:
        city = WEATHER_DEFAULT_CITY

    coords = resolve_city_to_coords(city)
    if not coords:
        return f"{city} için konum çözülemedi."

    lat, lon = coords
    try:
        url = (
            "https://api.openweathermap.org/data/3.0/onecall"
            f"?lat={lat}&lon={lon}&exclude=minutely,hourly,alerts"
            f"&appid={WEATHER_API_KEY}&units=metric&lang=tr"
        )
        r = requests.get(url, timeout=5)
        data = r.json()
        daily = data.get("daily", [])
        if not daily:
            return f"{city} için günlük tahmin verisi bulunamadı."

        lines = [f"📍 **{city.title()} için 7 Günlük Hava Tahmini:**"]
        for d in daily[:days]:
            dt = datetime.fromtimestamp(d["dt"], ZoneInfo("Europe/Istanbul"))
            tarih = dt.strftime("%d.%m.%Y %a")
            lines.append(
                f"- **{tarih}** — {d['weather'][0]['description'].capitalize()}, "
                f"min {d['temp']['min']:.1f}°C / max {d['temp']['max']:.1f}°C"
            )
        return "\n".join(lines)
    except Exception:
        return "7 günlük hava tahmini şu anda alınamıyor."

# ===========================
# GÜVENLİK / FİLTRE
# ===========================
BAD_PATTERNS = [
    r"(?i)orospu", r"(?i)siktir", r"(?i)amk", r"(?i)ibne",
    r"(?i)tecavüz", r"(?i)uyuşturucu", r"(?i)bomba yap", r"(?i)intihar",
]


def moderate_content(text: str) -> str | None:
    for pat in BAD_PATTERNS:
        if re.search(pat, text):
            return (
                "Bu isteğe güvenlik nedeniyle yanıt veremiyorum. "
                "Dilersen daha farklı bir konuda yardımcı olabilirim. 🙂"
            )
    return None

# ===========================
# KİMLİK & CHAT YARDIMCI
# ===========================
def custom_identity_interceptor(user_message: str) -> str | None:
    m = user_message.lower()
    triggers = [
        "seni kim yaptı", "seni kim yarattı", "kim geliştirdi",
        "kimsin", "sen kimsin", "who created you", "who made you",
        "who built you", "who are you",
    ]
    if any(t in m for t in triggers):
        return (
            "Beni **ALPTECH AI** ekibi geliştirdi 🚀\n\n"
            "Görevim; senin için akıllı bir stüdyo asistanı olmak, ürün görsellerini profesyonelleştirmek "
            "ve metin tarafında da markanı güçlendirmek. Her zaman yanındayım. 🙂"
        )
    return None


def custom_utility_interceptor(user_message: str) -> str | None:
    m = user_message.lower()

    if "saat" in m or "tarih" in m:
        return get_time_answer()

    if "7 günlük hava" in m or "7 gunluk hava" in m or "haftalık hava" in m:
        city = extract_city_from_message(user_message) or WEATHER_DEFAULT_CITY
        return get_weather_forecast_answer(city)

    if "hava" in m or "hava durumu" in m or "hava nasıl" in m:
        city = extract_city_from_message(user_message) or WEATHER_DEFAULT_CITY
        return get_weather_answer(city)

    return None


def build_system_talimati():
    z = turkce_zaman_getir()
    return f"""
    Senin adın **ALPTECH AI**.

    Uzmanlık alanların:
    - Ürün açıklaması, SEO, satış odaklı metin
    - Ürün faydaları, kutu içeriği, CTA üretimi
    - Trendyol / Hepsiburada / Amazon etiket & başlık üretimi
    - Fiyatlandırma psikolojisi ve fiyat önerileri
    - Ürün varyant çıkarımı (renk/beden/kapasite)
    - Müşteri yorum analizi (memnuniyet & şikâyet temaları)
    - Markalar için premium marka hikâyesi yazımı
    - Sosyal medya reklam metinleri (Instagram, TikTok, Facebook vb.)

    Görseller: Yüklenen ürün görselini analiz ederek ürünün tipi, tarzı, malzemesi gibi noktaları çıkar
    ve e-ticaret için uygun açıklama, başlık, etiket ve kampanya fikirleri öner.

    Cevap stilin:
    • Profesyonel, net ve güven veren
    • Hatalı bilgi uydurma, eksik bilgi varsa sor
    • Türkçe'yi sade ve akıcı kullan
    • Kullanıcı "kısa" derse özet, "detaylı" derse kapsamlı anlat

    Sistem notu: Bu yanıt {z} tarihinde oluşturulmuştur.
    """

# ===========================
# GPT-5.1 / GPT-4o CHAT MOTORU
# ===========================
def normal_sohbet(client: OpenAI):
    system_talimati = build_system_talimati()
    max_context = 40
    messages = [{"role": "system", "content": system_talimati}]
    history_slice = st.session_state.chat_history[-max_context:]

    for i, msg in enumerate(history_slice):
        api_role = "user" if msg["role"] == "user" else "assistant"
        if api_role == "user":
            if (
                i == len(history_slice) - 1
                and st.session_state.get("chat_image") is not None
            ):
                img_bytes = st.session_state.chat_image
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                content = [
                    {"type": "text", "text": msg["content"]},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ]
                messages.append({"role": "user", "content": content})
            else:
                messages.append({"role": "user", "content": msg["content"]})
        else:
            messages.append({"role": "assistant", "content": msg["content"]})

    model_to_use = st.secrets.get("OPENAI_MODEL", DEFAULT_MODEL) or "gpt-5.1"

    # 1. Deneme: kullanıcının seçtiği (örn: gpt-5.1)
    try:
        resp = client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            temperature=0.25,
            max_tokens=1500,
        )
        try:
            return resp.choices[0].message.content
        except Exception:
            return resp.choices[0].text
    except Exception as e:
        # 2. Deneme: fallback gpt-4o-mini
        print("Model hatası, fallback'e geçiliyor:", e)
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.25,
                max_tokens=1500,
            )
            try:
                return resp.choices[0].message.content
            except Exception:
                return resp.choices[0].text
        except Exception as e2:
            tb = traceback.format_exc()
            st.error("⚠️ Sohbet API çağrısında hata. Konsolu kontrol et.")
            print("Chat API HATA:", e, e2, tb)
            return "Üzgünüm, sohbet hizmetinde şu an teknik bir sorun var."

# ===========================
# GÖRSEL İŞLEME
# ===========================
def remove_bg_high_quality(img: Image.Image) -> Image.Image:
    """
    Zincir, saç, ince detayları daha iyi korumaya çalışır.
    rembg parametreleri biraz daha yumuşatıldı.
    """
    try:
        return remove(
            img,
            alpha_matting=True,
            alpha_matting_foreground_threshold=250,
            alpha_matting_background_threshold=5,
            alpha_matting_erode_size=0,  # 0 = detayları koru
        )
    except Exception as e:
        print("rembg hata (fallback RGBA):", e)
        return img.convert("RGBA")


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


def sahne_olustur(client: OpenAI, urun_resmi: Image.Image, prompt_text: str):
    if SABIT_API_KEY is None:
        return None
    try:
        max_boyut = 1200
        if urun_resmi.width > max_boyut or urun_resmi.height > max_boyut:
            urun_resmi.thumbnail((max_boyut, max_boyut), Image.Resampling.LANCZOS)

        temiz_urun = remove_bg_high_quality(urun_resmi)
        hazir_urun = resmi_hazirla(temiz_urun)

        if hazir_urun.mode != "RGBA":
            hazir_urun = hazir_urun.convert("RGBA")
        maske_ham = hazir_urun.split()[3]
        maske_yumusak = maske_ham.filter(ImageFilter.GaussianBlur(radius=2))
        final_maske = Image.new("RGBA", hazir_urun.size, (0, 0, 0, 0))
        final_maske.putalpha(maske_yumusak)

        resp = client.images.edit(
            image=("image.png", bayt_cevir(hazir_urun), "image/png"),
            mask=("mask.png", bayt_cevir(final_maske), "image/png"),
            prompt=prompt_text,
            n=1,
            size="1024x1024",
        )
        try:
            return resp.data[0].url
        except Exception:
            try:
                return resp["data"][0]["url"]
            except Exception:
                return None
    except Exception as e:
        print("sahne_olustur hata:", e, traceback.format_exc())
        return None


def yerel_islem(urun_resmi: Image.Image, islem_tipi: str):
    max_boyut = 1200
    if urun_resmi.width > max_boyut or urun_resmi.height > max_boyut:
        urun_resmi.thumbnail((max_boyut, max_boyut), Image.Resampling.LANCZOS)

    temiz_urun = remove_bg_high_quality(urun_resmi)

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

# ===========================
# SIDEBAR — Geçmiş & Prompt Kütüphanesi
# ===========================
def sidebar_ui():
    st.sidebar.markdown("### 🧠 ALPTECH AI Panel")

    st.sidebar.markdown("**Konuşmalarım**")
    sessions = list(st.session_state.chat_sessions.keys())
    if st.sidebar.button("➕ Yeni konuşma"):
        new_name = f"Oturum {len(sessions) + 1}"
        st.session_state.chat_sessions[new_name] = [
            {
                "role": "assistant",
                "content": "Yeni bir konuşma başlattın. Neye odaklanmak istersin?",
            }
        ]
        st.session_state.current_session = new_name
        st.session_state.chat_history = st.session_state.chat_sessions[new_name]
        st.rerun()

    sessions = list(st.session_state.chat_sessions.keys())
    if sessions:
        selected = st.sidebar.selectbox(
            "Aktif konuşma",
            sessions,
            index=sessions.index(st.session_state.current_session),
        )
        if selected != st.session_state.current_session:
            st.session_state.chat_sessions[st.session_state.current_session] = (
                st.session_state.chat_history
            )
            st.session_state.current_session = selected
            st.session_state.chat_history = st.session_state.chat_sessions[selected]
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Hazır Promptlar**")

    prompt_exp = st.sidebar.expander("Metin & Kampanya", expanded=False)
    with prompt_exp:
        if st.button("🛍 Ürün açıklaması oluştur", key="p_prod_desc"):
            st.session_state.pending_prompt = (
                "Bir e-ticaret ürünü için profesyonel bir ürün açıklaması yazmanı istiyorum.\n\n"
                "Şu yapıyı takip et:\n"
                "- Kısa giriş paragrafı\n"
                "- Öne çıkan 5 fayda (madde madde)\n"
                "- Kutu içeriği\n"
                "- Hedef kitle\n"
                "- Kullanım önerileri\n"
                "- Güçlü bir satın almaya çağrı (CTA)\n\n"
                "Ürün bilgilerini sorarak benden alabilirsin."
            )
        if st.button("🎉 Kampanya / İndirim duyurusu", key="p_campaign"):
            st.session_state.pending_prompt = (
                "Markam için kısa bir kampanya / indirim duyurusu metni yaz. Ton: samimi, enerjik, aksiyona çağıran."
            )
        if st.button("📢 Eğitim / Etkinlik duyurusu", key="p_event"):
            st.session_state.pending_prompt = (
                "Online eğitim için Instagram postu açıklaması yaz. Konu, tarih ve hedef kitleyi benden sor."
            )

    prompt_img = st.sidebar.expander("Görsel & Tasarım", expanded=False)
    with prompt_img:
        if st.button("📲 Instagram post tasarım fikri", key="p_ig_post"):
            st.session_state.pending_prompt = (
                "Bir ürün için Instagram post tasarım fikri üret. Renk paleti, tipografi ve çekim açısı öner."
            )
        if st.button("🎯 Reklam kreatif fikirleri", key="p_ad_ideas"):
            st.session_state.pending_prompt = (
                "Yeni çıkacak bir ürün için 3 farklı dijital reklam kreatif fikri öner. "
                "Her fikirde hedef kitle, ana mesaj ve görsel tarzı belirt."
            )

    ecom = st.sidebar.expander("🛒 E-Ticaret Asistanı (Akıllı Şablonlar)", expanded=False)
    with ecom:
        st.write("Birini seç → sohbet kutusuna hazır prompt olarak gelsin.")

        if st.button("📄 Profesyonel ürün açıklaması (5 fayda + kutu içeriği)", key="e_full_desc"):
            st.session_state.pending_prompt = (
                "E-ticaret odaklı profesyonel bir ürün açıklaması yazmanı istiyorum.\n\n"
                "Yapı:\n"
                "1) Kısa giriş\n"
                "2) Öne çıkan 5 fayda\n"
                "3) Kutu içeriği\n"
                "4) Hedef kitle\n"
                "5) Kullanım önerileri\n"
                "6) CTA\n\n"
                "Ürün detayı: [ÜRÜN ADI], [MARKA], [ÖZELLİKLER], [KULLANIM ALANI]. "
                "Eksik bilgileri benden sor."
            )

        if st.button("🖼 Görselden ürün analizi ve açıklama", key="e_image_analysis"):
            st.session_state.pending_prompt = (
                "Yüklediğim ürün görseline bakarak ürünün ne olduğunu tarif et ve "
                "e-ticaret odaklı bir açıklama yaz. Öne çıkan özellikler, kullanım alanları "
                "ve hedef kitleyi de belirt."
            )

        if st.button("🧪 Başlık için A/B test (5 varyasyon)", key="e_title_ab"):
            st.session_state.pending_prompt = (
                "Bir e-ticaret ürünü için 5 farklı SEO uyumlu ürün başlığı üret. "
                "Her başlıkta marka + ürün adı + 1-2 güçlü fayda geçsin."
            )

        if st.button("🏷 Trendyol / Pazaryeri etiketleri", key="e_tags"):
            st.session_state.pending_prompt = (
                "Bir ürün için Trendyol ve benzeri pazaryerlerinde kullanılabilecek, "
                "küçük harfle yazılmış, virgülle ayrılmış en az 25 etiket üret."
            )

        if st.button("💰 Fiyat psikolojisi & konumlandırma", key="e_pricing"):
            st.session_state.pending_prompt = (
                "Bir ürünü fiyatlandırırken fiyat psikolojisi açısından öneriler ver. "
                "Hedef fiyat aralığı, psikolojik fiyat (ör: 499,90), paketleme ve kampanya önerileri ekle."
            )

        if st.button("📦 Varyant çıkarımı (renk/beden/kapasite)", key="e_variants"):
            st.session_state.pending_prompt = (
                "Vereceğim ürün açıklamasına bakarak renk, beden, kapasite ve diğer olası varyantları listele."
            )

        if st.button("⭐ Müşteri yorum analizi", key="e_reviews"):
            st.session_state.pending_prompt = (
                "Yapıştıracağım müşteri yorumlarını analiz et. En çok beğenilen yönler, "
                "en çok şikâyet edilen noktalar ve geliştirme önerilerini yaz."
            )

        if st.button("📣 Sosyal medya reklam metinleri", key="e_ads"):
            st.session_state.pending_prompt = (
                "Bir ürün için Instagram, TikTok ve Facebook reklam metinleri üret. "
                "Her platform için 2'şer kısa metin, altında uygun hashtagler ver."
            )

        if st.button("🏪 Premium marka hikâyesi", key="e_brand_story"):
            st.session_state.pending_prompt = (
                "Mağazam için premium bir marka hikâyesi yaz. Kuruluş amacı, değerler, "
                "müşteriye verilen sözler ve vizyonu anlat."
            )

    st.sidebar.markdown("---")
    with st.sidebar.expander("📊 Analytics (demo)", expanded=False):
        a = st.session_state.analytics
        st.write(f"Stüdyo çalıştırma: {a.get('studio_runs', 0)}")
        st.write(f"Sohbet mesajı: {a.get('chat_messages', 0)}")
        st.write(f"Hava durumu sorgusu: {a.get('weather_queries', 0)}")
        st.write(f"7 günlük tahmin sorgusu: {a.get('forecast_queries', 0)}")
        st.write(f"Yüklenen dosya/görsel: {a.get('uploads', 0)}")

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "**Hakkında**\n\n"
        "Bu platform, ALPTECH AI ekibi tarafından geliştirilmiş bir yapay zeka stüdyosudur. "
        "Ürün görsellerini profesyonel seviyeye taşımak ve içerik üretim sürecini hızlandırmak için tasarlandı. 🚀"
    )

# ===========================
# HEADER & GENEL UI
# ===========================
col_bosluk, col_tema = st.columns([10, 1])
with col_tema:
    karanlik_mod = st.toggle("🌙 / ☀️", value=True, key="theme_toggle")
tema = get_theme(karanlik_mod)
apply_apple_css(tema)

sidebar_ui()

# Logo + Başlık
header_left, header_right = st.columns([0.16, 0.84])
with header_left:
    if LOGO_B64:
        if karanlik_mod:
            style = "max-width:160px; width:100%; display:block; margin-bottom:0.3rem;"
        else:
            style = (
                "max-width:160px; width:100%; display:block; margin-bottom:0.3rem;"
                "filter: invert(1) drop-shadow(0 0 4px rgba(0,0,0,0.6));"
            )
        st.markdown(
            f"<img src='data:image/png;base64,{LOGO_B64}' style='{style}'>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("### ALPTECH")

with header_right:
    st.markdown(
        """
        <h1 style="margin-bottom: 0.2rem;">ALPTECH AI Stüdyo</h1>
        <p style="margin-top: 0; font-size: 0.95rem;">
        Ürününü ekle, e-ticaret ve sosyal medya için profesyonel sahneler oluştur; GPT-5.1 destekli asistanla metinlerini hazırla.
        </p>
        """,
        unsafe_allow_html=True,
    )

# Mod seçimi
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

# ===========================
# STÜDYO MODU
# ===========================
if st.session_state.app_mode == "📸 Stüdyo Modu (Görsel Düzenleme)":
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"""
            <div class="image-container">
                <h4 style="margin-bottom:4px;">🎨 Yaratıcılık</h4>
                <p style="font-size:0.85rem; color:{tema['subtext']}; margin-bottom:0;">
                Ürününü farklı sahnelerde dene: beyaz fon, Instagram postu, mermer zemin,
                ahşap masa ve daha fazlası. Hepsi tek tıkla.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="image-container">
                <h4 style="margin-bottom:4px;">✨ Efektler</h4>
                <p style="font-size:0.85rem; color:{tema['subtext']}; margin-bottom:0;">
                Arka planı tamamen kaldırabilir, düz renk fonlar ekleyebilir veya
                yapay zeka ile profesyonel stüdyo sahneleri oluşturabilirsin.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="image-container">
                <h4 style="margin-bottom:4px;">📤 Paylaşım</h4>
                <p style="font-size:0.85rem; color:{tema['subtext']}; margin-bottom:0;">
                Hazırladığın sahneleri PNG/JPEG olarak indirip e-ticaret sitelerinde,
                kataloglarda veya reklamlarda doğrudan kullanabilirsin.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("#### Ürün görselini yükle")
    uploaded_file = st.file_uploader(
        "Ürün fotoğrafı",
        type=["png", "jpg", "jpeg", "webp"],
        label_visibility="collapsed",
        key="studio_upload",
    )
    kaynak_dosya = uploaded_file

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
                    st.image(raw_image, width=320, caption="Yüklenen Görsel")
                    st.markdown("</div>", unsafe_allow_html=True)

            with col_sag_panel:
                if st.session_state.sonuc_gorseli is None:
                    st.markdown(
                        '<div class="container-header">✨ Düzenleme Modu</div>',
                        unsafe_allow_html=True,
                    )

                    tab_hazir, tab_serbest = st.tabs(
                        ["🎨 Hazır Temalar / Preset", "✏️ Serbest Yazım"]
                    )
                    final_prompt = None
                    islem_tipi_local = None

                    with tab_hazir:
                        secilen_tema_input = st.selectbox(
                            "Ortam / preset seç:",
                            list(TEMA_LISTESI.keys()),
                            key="studio_tema",
                        )
                        if secilen_tema_input:
                            kod = TEMA_LISTESI[secilen_tema_input]
                            if isinstance(kod, str) and kod.startswith("ACTION_"):
                                islem_tipi_local = kod
                            else:
                                final_prompt = kod

                    with tab_serbest:
                        user_input = st.text_area(
                            "Hayalindeki sahneyi yaz:",
                            placeholder=(
                                "Örn: Çantayı beyaz fonda bırak, zincirleri net kalsın, "
                                "zemine hafif gölge ekle..."
                            ),
                            height=120,
                        )
                        if user_input:
                            final_prompt = (
                                "Professional product photography shot of the object. "
                                f"{user_input}. High quality, realistic lighting, 8k, photorealistic."
                            )

                    st.write("")
                    buton_placeholder = st.empty()
                    if buton_placeholder.button("🚀 İşlemi Başlat", type="primary"):
                        inc_stat("studio_runs")
                        try:
                            if final_prompt and SABIT_API_KEY is not None:
                                client = OpenAI(api_key=SABIT_API_KEY)
                                with st.spinner("AI sahneni oluşturuyor (10–30sn)... 🎨"):
                                    url = sahne_olustur(client, raw_image, final_prompt)
                                    if url:
                                        try:
                                            resp = requests.get(url, timeout=40)
                                            if resp.status_code == 200:
                                                st.session_state.sonuc_gorseli = resp.content
                                                st.session_state.sonuc_format = "PNG"
                                                st.rerun()
                                            else:
                                                st.error("AI görseli indirilemedi. Lütfen tekrar dene.")
                                        except Exception as e:
                                            st.error("Sonuç indirilemedi. Lütfen tekrar dene.")
                                            print("resim indir hata:", e, traceback.format_exc())
                                    else:
                                        st.error(
                                            "AI görsel düzenlemesi başarısız oldu. "
                                            "Daha net bir açıklama yazarak tekrar deneyebilirsin."
                                        )
                            elif islem_tipi_local:
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
                            else:
                                st.warning("Lütfen bir hazır tema seç veya kendi sahneni yaz.")
                        except Exception as e:
                            st.error(f"Hata: {e}")
                            print("İşlem başlat hata:", traceback.format_exc())
                            buton_placeholder.button("🚀 Tekrar Dene", type="primary")
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
                            st.image(st.session_state.sonuc_gorseli, use_container_width=True)
                    with c2:
                        if isinstance(st.session_state.sonuc_gorseli, (bytes, bytearray)):
                            st.download_button(
                                label=f"📥 İndir ({st.session_state.sonuc_format})",
                                data=st.session_state.sonuc_gorseli,
                                file_name=f"alptech_pro.{st.session_state.sonuc_format.lower()}",
                                mime=f"image/{st.session_state.sonuc_format.lower()}",
                                use_container_width=True,
                            )
                        else:
                            try:
                                resp = requests.get(st.session_state.sonuc_gorseli, timeout=30)
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
                                print("download fallback hata:", e, traceback.format_exc())

                    st.write("")
                    if st.button("🔄 Yeni İşlem Yap"):
                        st.session_state.sonuc_gorseli = None
                        st.rerun()

# ===========================
# SOHBET MODU
# ===========================
elif st.session_state.app_mode == "💬 Sohbet Modu (Genel Asistan)":
    inject_voice_js()

    st.markdown(
        '<div class="container-header">💬 ALPTECH AI Sohbet</div>',
        unsafe_allow_html=True,
    )

    # Geçmiş mesajlar
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    st.write("")

    # Chat alanının hemen üstünde: + butonu & uploader
    bottom_bar = st.container()
    with bottom_bar:
        col_plus, col_info = st.columns([0.12, 0.88])
        with col_plus:
            if st.button("➕", key="chat_plus_bottom", help="Dosya / görsel ekle"):
                st.session_state.show_upload_panel = not st.session_state.show_upload_panel

        with col_info:
            if st.session_state.chat_image:
                st.caption(
                    "📎 Bir ürün görseli yüklü. Yeni mesajlarında bu görsele göre açıklama isteyebilirsin."
                )
            else:
                st.caption(
                    "İstersen alttaki '+' ile ürün görseli yükleyip mağaza açıklaması, kampanya metni vb. yazdırabilirsin."
                )

        if st.session_state.show_upload_panel:
            chat_upload = st.file_uploader(
                "Görsel veya dosya yükle",
                type=["png", "jpg", "jpeg", "webp", "pdf", "txt"],
                key="chat_upload_bottom",
            )
            if chat_upload is not None:
                try:
                    file_bytes = chat_upload.read()
                    st.session_state.chat_image = file_bytes
                    st.session_state.show_upload_panel = False
                    inc_stat("uploads")
                    st.success(
                        "Dosya yüklendi. Şimdi bu dosya/görsel hakkında soru sorabilirsin."
                    )
                except Exception as e:
                    st.error("Dosya okunamadı, lütfen tekrar dene.")
                    print("chat upload error:", e)

    pending_prompt = st.session_state.pending_prompt
    if pending_prompt:
        st.session_state.pending_prompt = None

    chat_input_value = st.chat_input("Mesaj yazın...")
    prompt = pending_prompt or chat_input_value

    if prompt:
        inc_stat("chat_messages")
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        mod_msg = moderate_content(prompt)
        if mod_msg is not None:
            with st.chat_message("assistant"):
                st.write(mod_msg)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": mod_msg}
            )
        else:
            override = custom_identity_interceptor(prompt)
            if override is not None:
                with st.chat_message("assistant"):
                    st.write(override)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": override}
                )
            else:
                util_override = custom_utility_interceptor(prompt)
                if util_override is not None:
                    with st.chat_message("assistant"):
                        st.write(util_override)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": util_override}
                    )
                else:
                    if SABIT_API_KEY is None:
                        cevap = (
                            "Sohbet özelliğini kullanmak için bir OPENAI_API_KEY tanımlaman gerekiyor. "
                            "st.secrets içine ekledikten sonra uygulamayı yeniden başlat."
                        )
                        with st.chat_message("assistant"):
                            st.write(cevap)
                        st.session_state.chat_history.append(
                            {"role": "assistant", "content": cevap}
                        )
                    else:
                        with st.chat_message("assistant"):
                            with st.spinner("ALPTECH yazıyor..."):
                                client = OpenAI(api_key=SABIT_API_KEY)
                                cevap = normal_sohbet(client)
                                st.write(cevap)
                                st.session_state.chat_history.append(
                                    {"role": "assistant", "content": cevap}
                                )

    st.session_state.chat_sessions[st.session_state.current_session] = (
        st.session_state.chat_history
    )

# ===========================
# FOOTER
# ===========================
st.markdown(
    "<div class='custom-footer'>ALPTECH AI Stüdyo © 2025 | Developed by Alper</div>",
    unsafe_allow_html=True,
)
