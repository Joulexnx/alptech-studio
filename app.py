"""
File: app.py
ALPTECH AI Stüdyo — v3.0
- Apple-style UI
- Studio + Chat modları
- TR gerçek saat (WorldTimeAPI fallback local)
- OpenWeather: Geo + Current + 7-günlük tahmin (TR şehirleri)
- ALPTECH AI kimlik, güvenlik filtresi
- Chat içinde: '+' ile dosya/görsel yükleme, 🎤 sesle yaz (Web Speech API)
- Sol sidebar: konuşma geçmişi, prompt kütüphanesi, basit analytics
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
    st.warning(
        "⚠️ OPENAI_API_KEY tanımlı değil. Sohbet ve AI sahne düzenleme özellikleri devre dışı."
    )

DEFAULT_MODEL = st.secrets.get("OPENAI_MODEL", "gpt-4o-mini")

# OpenWeather
WEATHER_API_KEY = st.secrets.get(
    "WEATHER_API_KEY", "5f9ee20a060a62ba9cb79d4a048395d9"
)
WEATHER_DEFAULT_CITY = st.secrets.get("WEATHER_DEFAULT_CITY", "İstanbul")

# Logo dosya yolu (uygulama dizininde olmalı)
LOGO_PATH = "ALPTECHAI.png"

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
        transition: transform 120ms ease, box-shadow 120ms ease, transform 120ms ease;
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

    /* Chat input görünür (koyu mod mobil dahil) */
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

# Chat oturumları
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
# TEMA LİSTESİ (E-TİCARET ODAKLI)
# ===========================
TEMA_LISTESI = {
    # Basit arka plan işlemleri
    "🧹 Arka Planı Kaldır (Şeffaf)": "ACTION_TRANSPARENT",
    "⬜ Saf Beyaz Fon (E-ticaret)": "ACTION_WHITE",
    "⬛ Saf Siyah Fon (Premium)": "ACTION_BLACK",
    "🍦 Krem / Bej Fon (Soft)": "ACTION_BEIGE",
    # E-ticaret & katalog
    "🛒 Katalog Stüdyosu (Beyaz)": (
        "Clean e-commerce product photo of the object on a pure white seamless background. "
        "Soft diffused studio lighting, natural soft shadow under the product, Amazon listing style, 4k, ultra sharp."
    ),
    "📦 Ürün Kartı (Yumuşak Gölge)": (
        "E-commerce catalog shot of the object on a very light grey to white gradient background. "
        "Soft drop shadow, subtle reflection, minimalistic high-end cosmetics style, centered composition."
    ),
    # Sosyal medya presetleri
    "📲 Instagram Postu 1080x1350": (
        "Vertical 4:5 ratio (1080x1350) Instagram post of the object. "
        "Modern gradient background, bold soft shadows, high contrast, ready to post layout with focus on the product."
    ),
    "📱 Story 1080x1920": (
        "Vertical 9:16 ratio (1080x1920) Instagram story style image of the object. "
        "Room for text above and below, clean gradient background, bright and eye-catching design."
    ),
    "🎯 Reklam Görseli (Kampanya)": (
        "Advertising key visual with the object in the center. "
        "Dynamic lighting, gradient background, plenty of negative space for campaign text on the sides, "
        "professional marketing look."
    ),
    "▶️ YouTube Thumbnail": (
        "16:9 ratio YouTube thumbnail style design featuring the object on the right side with bold light background, "
        "strong contrast, cinematic shading and room for title text on the left."
    ),
    # Sahne / ortamlar
    "🌫 Nötr Gri Fon (Universal)": (
        "Professional product photography of the object on a neutral light grey seamless background. "
        "Soft softbox lighting, gentle vignette, clean catalogue style, 4k."
    ),
    "💡 Profesyonel Stüdyo (3 Nokta Işık)": (
        "High-end studio product photo, object on an infinity curve background. "
        "Three-point lighting setup, key light, fill light, and rim light, ultra sharp focus, commercial advertising style."
    ),
    "🌑 Karanlık Stüdyo (Drama)": (
        "Professional product shot on a matte black non-reflective background. "
        "Dramatic rim lighting, strong contrast, subtle reflection under the product, cinematic mood."
    ),
    "🏛️ Mermer Zemin (Lüks)": (
        "Luxury product photo of the object placed on a polished white carrara marble podium. "
        "Soft cinematic lighting, realistic shadows, depth of field, 8k, luxury aesthetic."
    ),
    "🪵 Ahşap Zemin (Doğal)": (
        "Product photo of the object on a textured warm oak wooden table. "
        "Soft daylight coming from the side, blurred cozy home background, natural lifestyle look."
    ),
    "🧱 Beton Zemin (Modern)": (
        "Minimalist product photo of the object on a raw grey concrete surface. "
        "Hard directional light, high contrast, modern industrial style, 8k."
    ),
    "🛋️ İpek Kumaş (Zarif)": (
        "Elegant product photo of the object resting on flowing champagne-colored silk fabric. "
        "Soft studio lighting, fashion editorial look, shallow depth of field."
    ),
    "🏠 Modern Salon Ortamı": (
        "Lifestyle product photo of the object on a modern living room coffee table. "
        "Soft natural daylight from a large window, blurred sofa and decor in the background, Scandinavian interior style."
    ),
    "🍽 Mutfak Tezgahı (Gıda / Mutfak Ürünü)": (
        "Product photo of the object on a bright kitchen countertop. "
        "White cabinets and soft daylight, slightly blurred background, fresh and clean cooking atmosphere."
    ),
    "🛁 Banyo Tezgahı (Kozmetik)": (
        "Cosmetics-style product photo of the object on a light bathroom counter with a blurred mirror and tiles in the background. "
        "Soft top lighting, clean spa-like aesthetic."
    ),
    "🌿 Doğal Dış Mekan (Yeşillik)": (
        "Product photo of the object outdoors on a simple neutral surface with blurred green plants and trees in the background. "
        "Soft natural daylight, bokeh background, fresh and organic feeling."
    ),
    "🌅 Gün Batımı Tonları (Sıcak)": (
        "Product photo of the object with a warm gradient background in sunset colors (orange, pink, purple). "
        "Soft cinematic lighting, gentle reflections, premium cosmetic ad style."
    ),
    "🍬 Pastel Gradient (Minimal)": (
        "Minimal product photo of the object standing on a soft pastel gradient background "
        "in light pink, lilac and blue tones. Clean composition, subtle soft shadow."
    ),
}

# ===========================
# ZAMAN & HAVA FONKSİYONLARI
# ===========================
def fetch_tr_time() -> datetime:
    """Önce WorldTimeAPI, hata olursa local Europe/Istanbul."""
    try:
        resp = requests.get(
            "http://worldtimeapi.org/api/timezone/Europe/Istanbul", timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            dt_str = data.get("datetime")
            if dt_str:
                return datetime.fromisoformat(dt_str)
    except Exception:
        pass
    return datetime.now(ZoneInfo("Europe/Istanbul"))


def turkce_zaman_getir() -> str:
    simdi = fetch_tr_time()
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


def get_time_answer() -> str:
    simdi = fetch_tr_time()
    return (
        f"Güncel sisteme göre tarih {simdi.strftime('%d.%m.%Y')}. "
        f"Şu an saat {simdi.strftime('%H:%M')}."
    )


def extract_city_from_message(message: str) -> str | None:
    """Türkçe cümleden şehir adını tahmini çıkarır."""
    msg = message.lower()
    msg = re.sub(r"[^\wçğıöşü\s]", " ", msg)
    tokens = [t for t in msg.split() if t]

    if "hava" in tokens:
        idx = tokens.index("hava")
        if idx >= 1:
            candidate = tokens[idx - 1]
        else:
            candidate = tokens[0]
    elif tokens:
        candidate = tokens[0]
    else:
        return None

    for suf in ["'da", "'de", "'ta", "'te", "da", "de", "ta", "te"]:
        if candidate.endswith(suf) and len(candidate) > len(suf) + 1:
            candidate = candidate[: -len(suf)]
            break

    candidate = candidate.strip()
    if not candidate:
        return None
    return candidate


def resolve_city_to_coords(city: str, limit: int = 1):
    """OpenWeather Geocoding API ile şehir → (lat, lon)."""
    if not WEATHER_API_KEY:
        return None
    try:
        q = f"{city},TR"
        url = (
            "http://api.openweathermap.org/geo/1.0/direct"
            f"?q={q}&limit={limit}&appid={WEATHER_API_KEY}"
        )
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data:
            return None
        first = data[0]
        return float(first["lat"]), float(first["lon"])
    except Exception:
        return None


def get_weather_answer(location: str | None = None) -> str:
    inc_stat("weather_queries")
    if not WEATHER_API_KEY:
        return "Şu an hava durumu bilgisini veremiyorum; sistemde hava durumu API anahtarı yok. 🌤️"

    city_raw = location or WEATHER_DEFAULT_CITY or "İstanbul"
    sehir = city_raw.strip()
    coords = resolve_city_to_coords(sehir)

    try:
        if coords:
            lat, lon = coords
            url = (
                "https://api.openweathermap.org/data/2.5/weather"
                f"?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric&lang=tr"
            )
        else:
            url = (
                "https://api.openweathermap.org/data/2.5/weather"
                f"?q={sehir},TR&appid={WEATHER_API_KEY}&units=metric&lang=tr"
            )

        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return f"{sehir} için anlık hava durumu bulunamadı. Başka bir şehir söyleyebilirsin."

        data = resp.json()
        durum = data["weather"][0]["description"].capitalize()
        derece = data["main"]["temp"]
        his = data["main"].get("feels_like", derece)
        nem = data["main"]["humidity"]
        ruzgar = data["wind"]["speed"]

        sehir_gorunum = sehir.title()
        return (
            f"📍 **{sehir_gorunum}**\n"
            f"🌡️ Sıcaklık: **{derece:.1f}°C** (Hissedilen **{his:.1f}°C**)\n"
            f"☁️ Hava: **{durum}**\n"
            f"💧 Nem: **%{nem}**\n"
            f"🍃 Rüzgar: **{ruzgar} m/s**"
        )
    except Exception:
        return "Hava durumu servisinde bir sorun oluştu; lütfen biraz sonra tekrar dene."


def get_weather_forecast_answer(location: str | None = None, days: int = 7) -> str:
    inc_stat("forecast_queries")
    if not WEATHER_API_KEY:
        return "Şu an hava durumu bilgisini veremiyorum; sistemde hava durumu API anahtarı yok. 🌤️"

    city_raw = location or WEATHER_DEFAULT_CITY or "İstanbul"
    sehir = city_raw.strip()
    coords = resolve_city_to_coords(sehir)
    if not coords:
        return f"{sehir} için konum bilgisi alınamadı; başka bir şehir söyleyebilirsin."

    lat, lon = coords
    try:
        url = (
            "https://api.openweathermap.org/data/3.0/onecall"
            f"?lat={lat}&lon={lon}&exclude=minutely,hourly,alerts"
            f"&appid={WEATHER_API_KEY}&units=metric&lang=tr"
        )
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return f"{sehir} için 7 günlük hava tahmini alınamadı."

        data = resp.json()
        daily = data.get("daily", [])
        if not daily:
            return f"{sehir} için günlük tahmin verisi bulunamadı."

        gun_sayisi = min(days, len(daily))
        sehir_gorunum = sehir.title()
        lines = [f"📍 **{sehir_gorunum} için 7 günlük hava tahmini:**"]
        for i in range(gun_sayisi):
            d = daily[i]
            dt = datetime.fromtimestamp(d["dt"], ZoneInfo("Europe/Istanbul"))
            tarih = dt.strftime("%d.%m.%Y %a")
            min_t = d["temp"]["min"]
            max_t = d["temp"]["max"]
            desc = d["weather"][0]["description"].capitalize()
            lines.append(
                f"- **{tarih}** → {desc}, min **{min_t:.1f}°C**, max **{max_t:.1f}°C**"
            )
        return "\n".join(lines)
    except Exception:
        return "7 günlük hava tahmini alınırken bir sorun oluştu; lütfen daha sonra tekrar dene."

# ===========================
# GÜVENLİK / FİLTRE
# ===========================
BAD_PATTERNS = [
    r"(?i)küfret",
    r"(?i)orospu",
    r"(?i)piç",
    r"(?i)siktir",
    r"(?i)ibne",
    r"(?i)tecavüz",
    r"(?i)uyuşturucu",
    r"(?i)intihar",
    r"(?i)bomba yap",
]


def moderate_content(text: str) -> str | None:
    for pat in BAD_PATTERNS:
        if re.search(pat, text):
            return (
                "Bu isteğe doğrudan yardımcı olamam. "
                "Ancak istediğin konuyu daha güvenli ve olumlu bir şekilde ele almak istersen beraber bakabiliriz. 🙂"
            )
    return None

# ===========================
# KİMLİK & CHAT YARDIMCI
# ===========================
def custom_identity_interceptor(user_message: str) -> str | None:
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
            "Görevim; senin için akıllı bir stüdyo asistanı olmak, ürün görsellerini profesyonelleştirmek "
            "ve metin tarafında da markanı güçlendirmek. Her zaman yanındayım. 🙂"
        )
    return None


def custom_utility_interceptor(user_message: str) -> str | None:
    msg = user_message.lower()

    if "saat" in msg or "tarih" in msg:
        return get_time_answer()

    if "7 günlük hava" in msg or "7 gunluk hava" in msg or "haftalık hava" in msg:
        city = extract_city_from_message(user_message) or WEATHER_DEFAULT_CITY
        return get_weather_forecast_answer(city)

    if "hava" in msg or "hava durumu" in msg or "hava nasıl" in msg:
        city = extract_city_from_message(user_message) or WEATHER_DEFAULT_CITY
        return get_weather_answer(city)

    return None


def build_system_talimati():
    zaman_bilgisi = turkce_zaman_getir()
    return f"""
    Senin adın **ALPTECH AI**.
    ALPTECH AI ekibi tarafından geliştirilen, modern ve profesyonel bir yapay zeka asistansın.

    Odak noktaların:
    - Ürün görselleri üzerinde çalışma (arka plan kaldırma, sahne oluşturma, e-ticaret görselleri).
    - E-ticaret odaklı metinler yazma (ürün açıklaması, kampanya metni, sosyal medya postu).
    - Genel sorularda açıklayıcı, sade cevaplar verme.

    Her zaman kendini "ALPTECH AI" olarak tanıt.
    Seni kimin geliştirdiği sorulduğunda: "ALPTECH AI ekibi" de.
    Mümkün olduğunca kısa ama net cevap ver; kullanıcı isterse detaya gir.
    Sistem notu: Bu yanıtlar {zaman_bilgisi} tarihinde oluşturuluyor.
    """


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
        st.error("⚠️ Sohbet API çağrısında hata. Konsolu kontrol et.")
        print("Chat API HATA:", e, tb)
        return "Üzgünüm, sohbet hizmetinde şu an bir sorun var."

# ===========================
# GÖRSEL İŞLEME
# ===========================
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

# ===========================
# SIDEBAR (KONUŞMA GEÇMİŞİ & PROMPT KÜTÜPHANESİ)
# ===========================
def sidebar_ui():
    st.sidebar.markdown("### 🧠 ALPTECH AI Panel")

    # Konuşma geçmişi
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
        st.experimental_rerun()

    sessions = list(st.session_state.chat_sessions.keys())
    if sessions:
        selected = st.sidebar.selectbox(
            "Aktif konuşma", sessions, index=sessions.index(st.session_state.current_session)
        )
        if selected != st.session_state.current_session:
            st.session_state.chat_sessions[st.session_state.current_session] = (
                st.session_state.chat_history
            )
            st.session_state.current_session = selected
            st.session_state.chat_history = st.session_state.chat_sessions[selected]
            st.experimental_rerun()

    st.sidebar.markdown("---")

    # Prompt kütüphanesi
    st.sidebar.markdown("**Hazır Promptlar**")
    prompt_exp = st.sidebar.expander("Metin & Kampanya", expanded=False)
    with prompt_exp:
        if st.button("🛍 Ürün açıklaması oluştur", key="p_prod_desc"):
            st.session_state.pending_prompt = (
                "Bir e-ticaret ürünü için SEO uyumlu, ikna edici bir ürün açıklaması "
                "yazar mısın? Özellikler: [ÜRÜN ADI], [ÖNE ÇIKAN ÖZELLİKLER], [KULLANIM ALANLARI]."
            )
        if st.button("🎉 Kampanya / İndirim duyurusu", key="p_campaign"):
            st.session_state.pending_prompt = (
                "Markam için % indirim içeren kısa bir kampanya duyurusu metni yazar mısın? "
                "Ton: samimi, enerjik, aksiyona çağıran."
            )
        if st.button("📢 Eğitim / Etkinlik duyurusu", key="p_event"):
            st.session_state.pending_prompt = (
                "Online eğitim için Instagram postu açıklaması yazar mısın? "
                "Konu: [EĞİTİM KONUSU], Tarih: [TARİH], Hedef kitle: [HEDEF]."
            )

    prompt_img = st.sidebar.expander("Görsel & Tasarım", expanded=False)
    with prompt_img:
        if st.button("📲 Instagram post tasarım fikri", key="p_ig_post"):
            st.session_state.pending_prompt = (
                "Bir ürün için Instagram post tasarım fikri üret. Arka plan, renk paleti, "
                "tipografi ve çekim açısı önerisi içersin."
            )
        if st.button("🎯 Reklam kreatif fikirleri", key="p_ad_ideas"):
            st.session_state.pending_prompt = (
                "Yeni çıkacak bir ürün için 3 farklı dijital reklam kreatif fikri öner. "
                "Her fikirde hedef kitle, mesaj ve görsel tarzı belirt."
            )

    st.sidebar.markdown("---")

    # Analytics
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
# Tema seçimi
col_bosluk, col_tema = st.columns([10, 1])
with col_tema:
    karanlik_mod = st.toggle("🌙 / ☀️", value=True, key="theme_toggle")
tema = get_theme(karanlik_mod)
apply_apple_css(tema)

# Sidebar UI
sidebar_ui()

# Header
header_left, header_right = st.columns([0.16, 0.84])
with header_left:
    try:
        st.image(LOGO_PATH, use_column_width=True)
    except Exception:
        st.markdown("### ALPTECH")
with header_right:
    st.markdown(
        """
        <h1 style="margin-bottom: 0.2rem;">ALPTECH AI Stüdyo</h1>
        <p style="margin-top: 0; font-size: 0.95rem;">
        Ürününü ekle, e-ticaret ve sosyal medya için profesyonel sahneler oluştur.
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
        st.experimental_rerun()

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
                                "Örn: Arabanın rengini mavi yap, arkayı koyu gri degrade yap, "
                                "zeminde yumuşak yansıma olsun..."
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
                                with st.spinner(
                                    "AI sahneni oluşturuyor (10–30sn)... 🎨"
                                ):
                                    url = sahne_olustur(
                                        client, raw_image, final_prompt
                                    )
                                    if url:
                                        try:
                                            resp = requests.get(url, timeout=40)
                                            if resp.status_code == 200:
                                                st.session_state.sonuc_gorseli = (
                                                    resp.content
                                                )
                                                st.session_state.sonuc_format = "PNG"
                                                st.experimental_rerun()
                                            else:
                                                st.error(
                                                    "AI görseli indirilemedi. Lütfen tekrar dene."
                                                )
                                        except Exception as e:
                                            st.error(
                                                "Sonuç indirilemedi. Lütfen tekrar dene."
                                            )
                                            print(
                                                "resim indir hata:",
                                                e,
                                                traceback.format_exc(),
                                            )
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
                                    st.experimental_rerun()
                            else:
                                st.warning(
                                    "Lütfen bir hazır tema seç veya kendi sahneni yaz."
                                )
                        except Exception as e:
                            st.error(f"Hata: {e}")
                            print("İşlem başlat hata:", traceback.format_exc())
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
                        st.experimental_rerun()

# ===========================
# SOHBET MODU
# ===========================
elif st.session_state.app_mode == "💬 Sohbet Modu (Genel Asistan)":
    inject_voice_js()

    st.markdown(
        '<div class="container-header">💬 ALPTECH AI Sohbet</div>',
        unsafe_allow_html=True,
    )

    # Chat içi '+' ile upload panel yönetimi
    top_bar = st.container()
    with top_bar:
        col_plus, col_info = st.columns([0.12, 0.88])
        with col_plus:
            if st.button("➕", key="chat_plus", help="Dosya / görsel ekle"):
                st.session_state.show_upload_panel = (
                    not st.session_state.show_upload_panel
                )
        with col_info:
            if st.session_state.chat_image:
                st.caption(
                    "📎 Bir ürün görseli eklendi. Yeni sorularında bu görsele göre açıklama isteyebilirsin."
                )
            else:
                st.caption(
                    "İstersen '+' ile ürün görseli ekleyip mağaza açıklaması, kampanya metni vb. yazdırabilirsin."
                )

    if st.session_state.show_upload_panel:
        with st.expander("📎 Dosya / Görsel yükle", expanded=True):
            chat_upload = st.file_uploader(
                "Görsel veya dosya yükle",
                type=["png", "jpg", "jpeg", "webp", "pdf", "txt"],
                key="chat_upload",
            )
            if chat_upload is not None:
                try:
                    file_bytes = chat_upload.read()
                    st.session_state.chat_image = file_bytes
                    st.session_state.show_upload_panel = False
                    inc_stat("uploads")
                    st.success("Dosya yüklendi. Şimdi bu dosya/görsel hakkında soru sorabilirsin.")
                except Exception as e:
                    st.error("Dosya okunamadı, lütfen tekrar dene.")
                    print("chat upload error:", e)

    # Mesaj geçmişini göster
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Pending prompt (sidebar hazır prompt)
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

        # Güvenlik filtresi
        mod_msg = moderate_content(prompt)
        if mod_msg is not None:
            with st.chat_message("assistant"):
                st.write(mod_msg)
            st.session_state.chat_history.append({"role": "assistant", "content": mod_msg})
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

    # Güncel chat'i aktif oturuma kaydet
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

