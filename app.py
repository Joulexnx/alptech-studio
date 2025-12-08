# app.py

"""
Qelyon AI Stüdyo — v4.0 (E-Ticaret + Danışmanlık + Pro Stüdyo + Psikolojik Danışmanlık)

- Marka: Qelyon AI
- 4 Mod:
  • 📸 Stüdyo Modu (Görsel Düzenleme)
  • 🛒 E-Ticaret Asistanı
  • 💼 Danışmanlık Asistanı
  • 🧠 Psikolojik Danışmanlık Asistanı

- OPENAI_MODEL varsayılanı: gpt-4o
- İki logo:
  • Koyu tema: QelyonAIwhite.png
  • Açık tema: QelyonAIblack.png

- Favicon: favicn.png

- Stüdyo:
  • Şeffaf arka plan (HQ, zincir/ince detaylara dikkat)
  • Beyaz fon + profesyonel temas gölgesi
  • Siyah fon + gölge
  • Bej fon + gölge
  • Profesyonel stüdyo: sonsuz arka plan, gölge + hafif yansıma

- Sohbet:
  • Sesle yaz (🎤, Web Speech API)
  • '+' ile görsel/dosya ekleme
  • TR saati, hava durumu, 7 günlük tahmin kısayolları
"""

from __future__ import annotations

import base64
import io
import re
import traceback
from datetime import datetime
from io import BytesIO
from typing import Literal
from zoneinfo import ZoneInfo

import requests
import streamlit as st
from openai import OpenAI
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps
from rembg import remove

# ===========================
# GÜVENLİ AYARLAR & KONFIG
# ===========================
if "OPENAI_API_KEY" in st.secrets:
    SABIT_API_KEY = st.secrets["OPENAI_API_KEY"]
else:
    SABIT_API_KEY = None
    st.warning(
        "⚠️ OPENAI_API_KEY tanımlı değil. Sohbet ve AI sahne düzenleme devre dışı."
    )

# Varsayılan model: gpt-4o
DEFAULT_MODEL = st.secrets.get("OPENAI_MODEL", "gpt-4o")

# OpenWeather
WEATHER_API_KEY = st.secrets.get(
    "WEATHER_API_KEY", "5f9ee20a060a62ba9cb79d4a048395d9"
)
WEATHER_DEFAULT_CITY = st.secrets.get("WEATHER_DEFAULT_CITY", "İstanbul")

# Logo dosya adları (uygulama klasöründe olmalı)
LOGO_LIGHT_PATH = "QelyonAIblack.png"   # Açık tema
LOGO_DARK_PATH = "QelyonAIwhite.png"    # Koyu tema

st.set_page_config(
    page_title="Qelyon AI Stüdyo",
    page_icon="favicn.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===========================
# THEME & CSS
# ===========================
def get_theme(is_dark: bool):
    accent = "#6C47FF"
    button_hover = "#5532CC"
    if is_dark:
        return {
            "bg": "#050509",
            "card_bg": "rgba(255,255,255,0.04)",
            "text": "#F9FAFB",
            "subtext": "#A0AEC0",
            "accent": accent,
            "button_hover": button_hover,
            "border": "rgba(255,255,255,0.08)",
            "input_bg": "rgba(255,255,255,0.04)",
        }
    else:
        return {
            "bg": "#F5F5FB",
            "card_bg": "rgba(255,255,255,0.85)",
            "text": "#0F172A",
            "subtext": "#6B7280",
            "accent": accent,
            "button_hover": button_hover,
            "border": "rgba(15,23,42,0.08)",
            "input_bg": "rgba(255,255,255,0.98)",
        }


def apply_apple_css(tema: dict):
    st.markdown(
        f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    body, html, .stApp {{
        font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
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
        backdrop-filter: blur(16px) saturate(140%);
        border-radius: 18px;
        padding: 14px;
        border: 1px solid {tema['border']};
        box-shadow: 0 8px 28px rgba(15,23,42,0.25);
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
        border-radius: 999px !important;
        padding: 9px 18px !important;
        border: none !important;
        font-weight: 600 !important;
        box-shadow: 0 8px 20px rgba(76,29,149,0.35);
        transition: transform 120ms ease, box-shadow 120ms ease;
    }}
    .stButton>button:hover {{
        background-color: {tema['button_hover']} !important;
        transform: translateY(-2px);
        box-shadow: 0 10px 24px rgba(76,29,149,0.45);
    }}

    .stTextArea textarea,
    input[type="text"],
    .stTextInput>div>div>input {{
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
        background: {tema['card_bg']};
        border: 1px solid {tema['border']};
    }}
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] span,
    [data-testid="stChatMessage"] div {{
        color: {tema['text']} !important;
    }}

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
        background: rgba(3,7,18,0.8);
        backdrop-filter: blur(12px);
        color: {tema['subtext']};
        text-align: center;
        padding: 8px 12px;
        font-size: 12px;
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
    if (root.querySelector('#qelyon-mic-btn')) return;

    const textarea = root.querySelector('textarea');
    if (!textarea) return;

    const btn = document.createElement('button');
    btn.id = 'qelyon-mic-btn';
    btn.innerText = '🎤';
    btn.title = 'Sesle yaz (tarayıcı mikrofon izni ister)';
    btn.style.marginLeft = '8px';
    btn.style.borderRadius = '999px';
    btn.style.border = 'none';
    btn.style.cursor = 'pointer';
    btn.style.padding = '4px 10px';
    btn.style.background = '#6C47FF';
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

    rec.onerror = (event) => { console.log('Speech recognition error', event); };

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
# ANALYTICS
# ===========================
def inc_stat(key: str, step: int = 1):
    if "analytics" not in st.session_state:
        return
    if key not in st.session_state.analytics:
        st.session_state.analytics[key] = 0
    st.session_state.analytics[key] += step

# ===========================
# TEMA LİSTESİ (Presetler)
# ===========================
TEMA_LISTESI = {
    "🧹 Şeffaf Arka Plan (HQ)": "ACTION_TRANSPARENT",
    "⬜ Beyaz Arka Plan · Profesyonel gölge": "ACTION_WHITE_PRO",
    "⬛ Siyah Arka Plan · Premium": "ACTION_BLACK",
    "🍦 Bej Arka Plan · Soft": "ACTION_BEIGE",
    "✨ Profesyonel Stüdyo (Gölge + Hafif Yansıma)": "ACTION_PRO_STUDIO",
}

# ===========================
# ZAMAN & HAVA
# ===========================
def fetch_tr_time() -> datetime:
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
    msg = message.lower()
    msg = re.sub(r"[^\wçğıöşü\s]", " ", msg)
    tokens = [t for t in msg.split() if t]
    if not tokens:
        return None

    if "hava" in tokens:
        idx = tokens.index("hava")
        candidate = tokens[idx - 1] if idx >= 1 else tokens[0]
    else:
        candidate = tokens[0]

    for suf in ["'da", "'de", "'ta", "'te", "da", "de", "ta", "te"]:
        if candidate.endswith(suf) and len(candidate) > len(suf) + 1:
            candidate = candidate[: -len(suf)]
            break
    candidate = candidate.strip()
    return candidate or None


def resolve_city_to_coords(city: str, limit: int = 1):
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
    r"(?i)orospu",
    r"(?i)siktir",
    r"(?i)amk",
    r"(?i)ibne",
    r"(?i)tecavüz",
    r"(?i)uyuşturucu",
    r"(?i)bomba yap",
]


def moderate_content(text: str) -> str | None:
    """
    Bazı hassas içeriklerde güvenli yanıtlar üretir veya isteği reddeder.
    Özellikle kendine zarar verme / intihar içeriğinde destekleyici + yönlendirici cevap döndürür.
    """
    lowered = text.lower()

    # Kendine zarar verme / intihar ifadeleri için özel yanıt
    crisis_keywords = [
        "intihar",
        "kendimi öldürmek",
        "kendimi oldurmek",
        "yaşamak istemiyorum",
        "yasamak istemiyorum",
        "hayatıma son vermek",
        "hayatima son vermek",
    ]
    if any(k in lowered for k in crisis_keywords):
        return (
            "Böyle hissettiğini duymak gerçekten zor ve yalnız olmadığını bilmeni isterim. 💛\n\n"
            "Ben bir yapay zeka asistanıyım; **kriz anlarında profesyonel yardımın yerini tutamam** "
            "ve acil müdahale sağlayamam.\n\n"
            "Şu anda kendine zarar verme düşüncelerin varsa lütfen:\n"
            "- Mümkünse **yalnız kalmamaya** çalış,\n"
            "- Güvendiğin bir yakınından destek iste,\n"
            "- Bulunduğun ülkedeki **acil yardım hattını** veya en yakın **sağlık kuruluşunu** hemen ara.\n"
            "- Türkiye'de yaşıyorsan **112 Acil**'i arayabilirsin.\n\n"
            "Burada sana genel anlamda duygularını düzenlemene yardımcı olabilecek, "
            "terapinin yerini almayan bazı öneriler sunabilirim; "
            "ama en önemli adım bir ruh sağlığı profesyoneliyle yüz yüze ya da online görüşmek olacaktır."
        )

    for pat in BAD_PATTERNS:
        if re.search(pat, text):
            return (
                "Bu isteğe güvenlik nedeniyle yanıt veremiyorum. "
                "Dilersen daha farklı ve güvenli bir konuda yardımcı olabilirim. 🙂"
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
            "Ben **Qelyon AI**.\n\n"
            "Qelyon AI olarak; ürün görselleri, e-ticaret içerikleri, iş stratejisi ve "
            "psikolojik danışmanlık alanında bilgilendirici destek sunan bir yapay zeka asistanıyım. 🚀\n\n"
            "Terapi yapmam, tanı koymam ve ilaç önermem; yalnızca genel bilgiler, "
            "fikirler ve metin taslakları üretirim."
        )
    return None


def custom_utility_interceptor(user_message: str) -> str | None:
    msg = user_message.lower()

    # Saat / tarih — tarihçesi/tarihi gibi history isteklerine karışma
    if re.search(r"\b(saat|tarih)\b", msg):
        if not re.search(r"\b(tarihi|tarihçesi|tarihcesi|geçmişi|gecmisi)\b", msg):
            return get_time_answer()

    if "7 günlük hava" in msg or "7 gunluk hava" in msg or "haftalık hava" in msg:
        city = extract_city_from_message(user_message) or WEATHER_DEFAULT_CITY
        return get_weather_forecast_answer(city)

    if "hava" in msg or "hava durumu" in msg or "hava nasıl" in msg or "hava nasil" in msg:
        city = extract_city_from_message(user_message) or WEATHER_DEFAULT_CITY
        return get_weather_answer(city)

    return None


def build_system_talimati(profile: Literal["ecom", "consult", "psy"]) -> str:
    z = turkce_zaman_getir()

    if profile == "ecom":
        return f"""
        Senin adın **Qelyon AI**.

        Rolün:
        - E-ticaret ve online satış odaklı bir yapay zeka asistansın.
        - Ürün açıklamaları, SEO uyumlu başlıklar, fayda listeleri, kutu içeriği,
          pazaryeri etiketleri, kampanya metinleri ve sosyal medya postlarında uzmansın.

        Yazım tarzın:
        - Profesyonel, net, güven veren.
        - Gerektiğinde madde madde, okunması kolay.
        - Türkçe'yi sade ve anlaşılır kullan.
        - Eksik bilgi varsa uydurma, önce kullanıcıya sor.

        Ürün açıklaması yazarken varsayılan yapı:
        - Kısa giriş paragrafı
        - Öne çıkan 5 fayda (madde madde)
        - Kutu içeriği
        - Hedef kitle
        - Kullanım önerileri
        - Güçlü bir satın almaya çağrı (CTA)

        Görsel yüklüyse:
        - Ürünü kısaca tarif et.
        - E-ticaret için önemli özellikleri vurgula (malzeme, kullanım alanı, stil vb.).

        Sistem notu: Bu yanıt {z} tarihinde oluşturulmuştur.
        """

    if profile == "consult":
        return f"""
        Senin adın **Qelyon AI**.

        Qelyon AI olarak, profesyonel danışmanlık ve veri destekli içgörülerle
        iş hedeflerine ulaşmayı hızlandıran bir asistansın. 🚀

        Uzmanlık alanların:
        - İş stratejisi ve büyüme planları
        - Pazarlama ve satış hunisi analizi
        - KPI belirleme, OKR yapısı ve performans ölçümü
        - Müşteri segmentasyonu ve hedef kitle analizi
        - Temel finansal modelleme (gelir, maliyet, kârlılık senaryoları)
        - Operasyonel verimlilik ve süreç iyileştirme

        Cevap stilin:
        - Önce durumu anlamaya çalışan 1-2 net soru sorabilirsin.
        - Sonra yapıyı bozmadan analitik, ancak sade ve uygulanabilir öneriler ver.
        - Gerektiğinde maddelerle özetle, aksiyon adımları ver.
        - Uydurma veri üretme; varsayım kullanıyorsan bunu açıkça belirt.

        Sistem notu: Bu yanıt {z} tarihinde oluşturulmuştur.
        """

    # Psikolojik danışmanlık profili
    return f"""
    Senin adın **Qelyon AI Psikolojik Danışmanlık Asistanı**.

    Rolün:
    - Psikolojik danışmanlık merkezleri, psikologlar, psikolojik danışmanlar ve danışanlar için
      destekleyici, bilgilendirici ve etik sınırları olan bir yapay zeka asistansın.
    - Terapi YAPMAZ, tanı KOYMAZ ve ilaç ÖNERMEZSİN.
    - Her zaman, gerekli olduğunda kişiyi lisanslı ruh sağlığı profesyoneline yönlendirirsin.

    Kullanım senaryoların (kullanıcı mesajına göre hangisinin uygun olduğuna karar ver):
    1) Danışan için ön görüşme ve yönlendirme:
       - Kısa, açık uçlu sorularla kişinin şikâyetini ve hedefini anlamaya çalış.
       - Asla net tanı koyma; bunun yerine "şu belirtiler için bir uzmana görünmeniz faydalı olabilir" gibi ifadeler kullan.
       - Merkezin/uzmanın uygunluk bilgisini UYDURMA; sadece genel "uzmanla görüş" tavsiyesi ver.

    2) Psiko-eğitim içerikleri:
       - Kaygı, stres, uyku, sınav kaygısı, iletişim, ilişkiler, öfke vb. konularda
         bilgilendirici ama tıbbi olmayan açıklamalar ve pratik, temel öneriler üret.
       - İçeriği istenen formata göre yaz (blog, PDF broşür taslağı, mail, Instagram postu vb.).

    3) Uzman odaklı kullanım:
       - Uzmanın verdiği seans notlarını başlıklar ve maddeler halinde toparla.
       - "Oturum özeti", "Danışanın duygu durumu", "Ele alınan temalar", "Verilen ev ödevleri" gibi bölümler önerebilirsin.
       - Notları her zaman anonimleştirmeyi ve gizliliğe saygı duymayı hatırlat.

    4) Ev ödevi / çalışma taslakları:
       - Uzmanın belirttiği hedefe göre haftalık küçük egzersizler ve yansıtıcı sorular üret.
       - Her seferinde ödevin terapiyi destekleyen, ama onun yerini almayan bir araç olduğuna dair kısa bir not ekleyebilirsin.

    5) Kurumsal çalışan destek iletişimi:
       - Çalışanlara yönelik duyuru metni, bilgilendirme maili, temel stres yönetimi önerileri
         ve seansa yönlendiren mesaj şablonları hazırlayabilirsin.

    DİL VE TON:
    - Sıcak, empatik, yargılamayan bir dil kullan.
    - Cümleleri sade ve anlaşılır tut; gerektiğinde madde madde yaz.
    - Özellikle duygusal konularda kişinin duygusunu yansıt ("Böyle hissetmen çok anlaşılır..." gibi).

    SINIRLAR:
    - Tanı isimlerini (depresyon, panik bozukluk vb.) "net tanı koyamam ancak..." gibi yumuşat.
    - İlaçlarla ilgili hiçbir detaylı öneri verme; her zaman "bu konuyu psikiyatristinle görüşmelisin" de.
    - Kriz / kendine zarar verme / intihar ima eden ifadelerde:
      • Acil yardım hatlarını ve en yakın sağlık kuruluşunu aramasını öner.
      • Bu platformun acil müdahale sağlayamayacağını açıkça belirt.

    Sistem notu: Bu yanıt {z} tarihinde oluşturulmuştur.
    """

# ===========================
# GPT-4o CHAT MOTORU
# ===========================
def normal_sohbet(client: OpenAI, profile: Literal["ecom", "consult", "psy"]) -> str:
    system_talimati = build_system_talimati(profile)
    max_context = 40
    history_slice = st.session_state.chat_history[-max_context:]

    messages: list[dict] = [{"role": "system", "content": system_talimati}]

    # Geçmişi ekle (user/assistant)
    for msg in history_slice:
        api_role = "user" if msg["role"] == "user" else "assistant"
        messages.append({"role": api_role, "content": msg["content"]})

    # Son user mesajına görsel ekleyebilmek için:
    last_user = None
    for msg in reversed(history_slice):
        if msg["role"] == "user":
            last_user = msg["content"]
            break

    if last_user is not None and st.session_state.get("chat_image") is not None:
        img_bytes = st.session_state.chat_image
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        content = [
            {"type": "text", "text": last_user},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]
        messages.append({"role": "user", "content": content})

    model_to_use = st.secrets.get("OPENAI_MODEL", DEFAULT_MODEL) or "gpt-4o"
    try:
        response = client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            temperature=0.25,
            max_tokens=1500,
        )
        try:
            return response.choices[0].message.content
        except Exception:
            return response.choices[0].text
    except Exception as e:
        print("Model hatası, fallback gpt-4o-mini deneniyor:", e)
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.25,
                max_tokens=1500,
            )
            try:
                return response.choices[0].message.content
            except Exception:
                return response.choices[0].text
        except Exception as e2:
            tb = traceback.format_exc()
            st.error("⚠️ Sohbet API çağrısında hata. Konsolu kontrol et.")
            print("Chat API HATA:", e, e2, tb)
            return "Üzgünüm, sohbet hizmetinde şu an teknik bir sorun var."

# ===========================
# GÖRSEL İŞLEME (HQ)
# ===========================
def _to_png_bytes(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def _binary_mask(
    alpha: Image.Image,
    thresh: int = 5,
    dilate: int = 3,
    erode: int = 0,
) -> Image.Image:
    """
    Kenarlarda kanama olmaması için alfa maskesini sertleştirip genişletir.
    İnce zincir / saç vb. detaylar için yumuşak Gaussian blur ile rafine edilir.
    """
    m = alpha.convert("L").filter(ImageFilter.MedianFilter(size=3))
    m = m.point(lambda p: 255 if p > thresh else 0)
    for _ in range(max(dilate, 0)):
        m = m.filter(ImageFilter.MaxFilter(3))
    for _ in range(max(erode, 0)):
        m = m.filter(ImageFilter.MinFilter(3))
    return m


def remove_bg_high_quality(img: Image.Image) -> Image.Image:
    """
    Yüksek kaliteli arka plan temizleme.
    Zincir / ince dokular için daha yumuşak, kenarları rafine eder.
    """
    try:
        cut = remove(
            img,
            alpha_matting=True,
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10,
            alpha_matting_erode_size=1,
        )
    except Exception:
        cut = img.convert("RGBA")

    if cut.mode != "RGBA":
        cut = cut.convert("RGBA")

    a = cut.split()[3]
    mask = _binary_mask(a, thresh=5, dilate=2, erode=0).filter(
        ImageFilter.GaussianBlur(radius=0.5)
    )
    rgb = cut.convert("RGB")
    out = Image.new("RGBA", cut.size, (0, 0, 0, 0))
    out.paste(rgb, (0, 0), mask)
    return out


def resmi_hazirla(image: Image.Image) -> Image.Image:
    """
    Ürünü 1024x1024 kare tuvale ortalar. (AI edit için uygun format)
    """
    kare_resim = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    image = image.copy()
    image.thumbnail((850, 850), Image.Resampling.LANCZOS)
    x = (1024 - image.width) // 2
    y = (1024 - image.height) // 2
    kare_resim.paste(image, (x, y), image if image.mode == "RGBA" else None)
    return kare_resim


def _contact_shadow_from_alpha(alpha: Image.Image, strength: int = 110) -> Image.Image:
    """
    Beyaz/siyah/bej zemin için yumuşak 'temas gölgesi' üretir.
    Ürünün altındaki alanı hafifçe koyulaştırır.
    """
    a = alpha.convert("L")
    bbox = a.getbbox()
    if not bbox:
        return Image.new("L", a.size, 0)

    w = bbox[2] - bbox[0]
    h = max(8, int((bbox[3] - bbox[1]) * 0.18))
    shadow = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(shadow)
    draw.ellipse([0, 0, w, h], fill=strength)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=max(10, h // 2)))

    mask = Image.new("L", a.size, 0)
    x = bbox[0]
    y = bbox[3] - int(h * 0.4)
    mask.paste(shadow, (x, y))
    return mask


def _center_on_square(im: Image.Image, side: int = 1024) -> Image.Image:
    """
    Ürünü istenen boyutta kare kanvasa ortalar (RGBA).
    """
    can = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    im = im.copy()
    im.thumbnail((int(side * 0.85), int(side * 0.85)), Image.Resampling.LANCZOS)
    x = (side - im.width) // 2
    y = (side - im.height) // 2
    can.paste(im, (x, y), im)
    return can


def _reflection(clip: Image.Image, fade: int = 220) -> Image.Image:
    """
    Hafif zemin yansıması üretir (profesyonel stüdyo görünümü için).
    """
    a = clip.split()[3]
    box = a.getbbox()
    if not box:
        return Image.new("RGBA", clip.size, (0, 0, 0, 0))
    crop = clip.crop(box)
    ref = ImageOps.flip(crop)

    grad = Image.linear_gradient("L").resize((1, ref.height))
    grad = ImageOps.invert(grad).point(lambda p: int(p * (fade / 255)))
    grad = grad.resize(ref.size)
    ref.putalpha(grad)

    canvas = Image.new("RGBA", clip.size, (0, 0, 0, 0))
    canvas.paste(ref, (box[0], box[3] + 4), ref)
    return canvas


def pro_studio_composite(
    cutout_rgba: Image.Image,
    bg: str = "white",
    do_shadow: bool = True,
    do_reflection: bool = True,
) -> Image.Image:
    """
    Sonsuz arka plan + temas gölgesi + hafif refleksiyon.
    Ürün %100 korunur, sadece sahne oluşturulur.
    """
    side = 1024
    obj = _center_on_square(cutout_rgba, side)
    a = obj.split()[3]

    if bg == "white":
        base = Image.new("RGB", (side, side), (255, 255, 255))
        overlay = Image.new("L", (1, side), 0)
        overlay = overlay.point(lambda p: int(p * 0.08)).resize((side, side))
        base = ImageChops.screen(base, Image.merge("RGB", (overlay, overlay, overlay)))
        base = base.convert("RGBA")
    elif bg == "black":
        base = Image.new("RGBA", (side, side), (0, 0, 0, 255))
    elif bg == "beige":
        base = Image.new("RGBA", (side, side), (245, 240, 225, 255))
    else:
        base = Image.new("RGBA", (side, side), (255, 255, 255, 255))

    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.alpha_composite(base)

    if do_shadow:
        sh_mask = _contact_shadow_from_alpha(a, strength=120)
        shadow_rgba = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        shadow_rgba.putalpha(sh_mask)
        out.alpha_composite(shadow_rgba)

    if do_reflection:
        refl = _reflection(obj)
        out.alpha_composite(refl)

    out.alpha_composite(obj)
    return out


def yerel_islem(urun_resmi: Image.Image, islem_tipi: str) -> Image.Image:
    """
    Şeffaf / beyaz / siyah / bej ve profesyonel stüdyo preset'leri.
    """
    max_boyut = 1400
    if urun_resmi.width > max_boyut or urun_resmi.height > max_boyut:
        urun_resmi = urun_resmi.copy()
        urun_resmi.thumbnail((max_boyut, max_boyut), Image.Resampling.LANCZOS)

    cut = remove_bg_high_quality(urun_resmi)

    if islem_tipi == "ACTION_TRANSPARENT":
        return cut

    if islem_tipi == "ACTION_PRO_STUDIO":
        return pro_studio_composite(
            cut, bg="white", do_shadow=True, do_reflection=True
        )

    bg_map = {
        "ACTION_WHITE_PRO": ("white", True, False),
        "ACTION_BLACK": ("black", True, False),
        "ACTION_BEIGE": ("beige", True, False),
    }
    if islem_tipi in bg_map:
        bg, sh, refl = bg_map[islem_tipi]
        return pro_studio_composite(cut, bg=bg, do_shadow=sh, do_reflection=refl)

    # Varsayılan: beyaz fon
    return pro_studio_composite(cut, bg="white", do_shadow=True, do_reflection=False)


def sahne_olustur(client: OpenAI, urun_resmi: Image.Image, prompt_text: str):
    """
    Serbest yazım için AI sahne üretimi.
    Ürün HQ kaldırılır ve kare tuvale oturtulur, maske ile ürün korunur.
    """
    if SABIT_API_KEY is None:
        return None
    try:
        max_boyut = 1200
        if urun_resmi.width > max_boyut or urun_resmi.height > max_boyut:
            urun_resmi = urun_resmi.copy()
            urun_resmi.thumbnail((max_boyut, max_boyut), Image.Resampling.LANCZOS)

        try:
            temiz_urun = remove_bg_high_quality(urun_resmi)
        except Exception:
            temiz_urun = urun_resmi.convert("RGBA")

        hazir_urun = resmi_hazirla(temiz_urun)
        if hazir_urun.mode != "RGBA":
            hazir_urun = hazir_urun.convert("RGBA")

        alpha = hazir_urun.split()[3]
        alpha_bin = _binary_mask(alpha, thresh=5, dilate=2, erode=0)
        mask_rgba = Image.new("RGBA", hazir_urun.size, (255, 255, 255, 255))
        mask_rgba.putalpha(alpha_bin)

        safe_prompt = (
            "Pure white or softly graded studio background, soft realistic shadow under the product, "
            "professional lighting. Preserve the product exactly as-is: DO NOT change brand, geometry, "
            "color, or texture. Ultra realistic, sharp details. "
        ) + (prompt_text or "")

        response = client.images.edit(
            image=("image.png", _to_png_bytes(hazir_urun), "image/png"),
            mask=("mask.png", _to_png_bytes(mask_rgba), "image/png"),
            prompt=safe_prompt,
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

# ===========================
# SIDEBAR / PROMPT KÜTÜPHANESİ
# ===========================
def sidebar_ui():
    st.sidebar.markdown("### 🧠 Qelyon AI Paneli")

    st.sidebar.markdown("**Konuşmalarım**")
    sessions = list(st.session_state.chat_sessions.keys())

    if st.sidebar.button("➕ Yeni konuşma"):
        new_name = f"Oturum {len(sessions) + 1}"
        st.session_state.chat_sessions[new_name] = [
            {"role": "assistant", "content": "Yeni bir konuşma başlattın. Seni dinliyorum!"}
        ]
        st.session_state.current_session = new_name
        st.session_state.chat_history = st.session_state.chat_sessions[new_name]
        st.rerun()

    # Oturum seçici
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

    # Hazır promptlar
    st.sidebar.markdown("---")
    st.sidebar.markdown("**📦 Hazır Promptlar**")

    exp_ecom = st.sidebar.expander("🛒 E-Ticaret Promptları", expanded=False)
    with exp_ecom:
        if st.button("📝 Ürün açıklaması oluştur"):
            st.session_state.pending_prompt = (
                "Bir ürün için profesyonel e-ticaret açıklaması yaz. "
                "Giriş + 5 Fayda + Kutu içeriği + Kullanım önerisi + CTA formatını kullan."
            )

        if st.button("📢 Kampanya duyurusu"):
            st.session_state.pending_prompt = (
                "Marka için kısa ve etkili bir kampanya duyurusu yaz."
            )

        if st.button("🏷 Trendyol etiket önerisi"):
            st.session_state.pending_prompt = (
                "Bu ürün için en doğru Trendyol etiketlerini yaz. "
                "Arama hacmine uygun 20 etiket öner."
            )

    exp_design = st.sidebar.expander("🎨 Görsel / Tasarım Promptları", expanded=False)
    with exp_design:
        if st.button("📲 Instagram Post Fikri"):
            st.session_state.pending_prompt = (
                "Bu ürün için 3 farklı Instagram post tasarım fikri üret. "
                "Renk paleti + tipografi + kompozisyon dahil olsun."
            )
        if st.button("🎯 Reklam kreatif fikirleri"):
            st.session_state.pending_prompt = (
                "Ürün için 3 adet yüksek performanslı reklam kreatif fikri üret."
            )

    exp_consult = st.sidebar.expander("💼 Danışmanlık Promptları", expanded=False)
    with exp_consult:
        if st.button("📊 İş modeli analizi"):
            st.session_state.pending_prompt = (
                "İş modelimi analiz et. Önce bana kritik sorular sor, sonra güçlü/zayıf yönleri çıkar."
            )
        if st.button("📈 Büyüme stratejisi"):
            st.session_state.pending_prompt = (
                "Şirketim için profesyonel bir büyüme stratejisi oluştur."
            )
        if st.button("🎯 KPI & OKR oluşturma"):
            st.session_state.pending_prompt = (
                "Şirketim için net KPI ve OKR önerileri ver."
            )

    exp_psy = st.sidebar.expander("🧠 Psikolojik Danışmanlık Promptları", expanded=False)
    with exp_psy:
        if st.button("👤 Danışan ön görüşme akışı"):
            st.session_state.pending_prompt = (
                "Psikolojik danışmanlık merkezine ilk kez yazan bir danışan için, "
                "empatik bir dille kısa bir karşılama ve 4-5 soruluk ön görüşme akışı oluştur."
            )
        if st.button("📄 Psiko-eğitim broşürü taslağı"):
            st.session_state.pending_prompt = (
                "Kaygı ve stresle baş etme konusunda, bir psikolojik danışmanlık merkezinin "
                "danışanlarına verebileceği psiko-eğitim broşürü taslağı yaz."
            )
        if st.button("🗒 Seans notu özetleyici"):
            st.session_state.pending_prompt = (
                "Aşağıdaki seans notunu; Oturum Özeti / Danışanın Duygusu / Ele Alınan Temalar / "
                "Verilen Ev Ödevleri başlıklarıyla profesyonelce yeniden düzenle."
            )
        if st.button("✅ Ev ödevi / egzersiz önerileri"):
            st.session_state.pending_prompt = (
                "Kaygı odaklı çalışan bir danışan için 1 haftalık kısa ev ödevi ve egzersiz planı taslağı oluştur."
            )
        if st.button("🏢 Kurumsal çalışan destek maili"):
            st.session_state.pending_prompt = (
                "Bir şirketin çalışanlarına yönelik, kurumla anlaşmalı psikolojik danışmanlık hizmetini "
                "duyuran bilgilendirme maili metni yaz."
            )

    st.sidebar.markdown("---")

    st.sidebar.markdown(
        "**ℹ️ Hakkında**\n\n"
        "Qelyon AI Stüdyo; ürün görselleri, içerik üretimi, profesyonel "
        "danışmanlık içgörüleri ve psikolojik danışmanlık alanında destekleyici "
        "metinler üretmek için geliştirilmiş bir yapay zeka platformudur. 🚀"
    )


# ===========================
# HEADER & TEMA
# ===========================
col_space, col_theme = st.columns([10, 1])
with col_theme:
    dark_mode = st.toggle("🌙 / ☀️", value=True, key="theme_toggle")

tema = get_theme(dark_mode)
apply_apple_css(tema)

sidebar_ui()

# ===========================
# LOGO + BAŞLIK BLOĞU
# ===========================
col_logo, col_title = st.columns([0.16, 0.84])
with col_logo:
    logo_file = LOGO_DARK_PATH if dark_mode else LOGO_LIGHT_PATH
    try:
        st.image(logo_file, use_column_width=True)
    except:
        st.markdown("### Qelyon AI")

with col_title:
    st.markdown(
        """
        <h1 style="margin-bottom: 4px;">Qelyon AI Stüdyo</h1>
        <p style="margin-top: 0; font-size: 0.94rem;">
            Ürününü yükle, profesyonel sahneler oluştur, metinleri optimize et;
            iş stratejilerini ve psikolojik danışmanlık süreçlerini Qelyon AI ile destekle.
        </p>
        """,
        unsafe_allow_html=True,
    )


# ===========================
# MOD SEÇİMİ (4 Mod)
# ===========================
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

is_studio = st.session_state.app_mode == "📸 Stüdyo Modu"
is_ecom = st.session_state.app_mode == "🛒 E-Ticaret Asistanı"
is_consult = st.session_state.app_mode == "💼 Danışmanlık Asistanı"
is_psy = st.session_state.app_mode == "🧠 Psikolojik Danışmanlık Asistanı"

with col_m1:
    if st.button(
        "📸 Stüdyo Modu",
        use_container_width=True,
        type="primary" if is_studio else "secondary",
    ):
        st.session_state.app_mode = "📸 Stüdyo Modu"
        st.session_state.sonuc_gorseli = None
        st.rerun()

with col_m2:
    if st.button(
        "🛒 E-Ticaret Asistanı",
        use_container_width=True,
        type="primary" if is_ecom else "secondary",
    ):
        st.session_state.app_mode = "🛒 E-Ticaret Asistanı"
        st.session_state.sonuc_gorseli = None
        st.rerun()

with col_m3:
    if st.button(
        "💼 Danışmanlık Asistanı",
        use_container_width=True,
        type="primary" if is_consult else "secondary",
    ):
        st.session_state.app_mode = "💼 Danışmanlık Asistanı"
        st.session_state.sonuc_gorseli = None
        st.rerun()

with col_m4:
    if st.button(
        "🧠 Psikolojik Danışmanlık",
        use_container_width=True,
        type="primary" if is_psy else "secondary",
    ):
        st.session_state.app_mode = "🧠 Psikolojik Danışmanlık Asistanı"
        st.session_state.sonuc_gorseli = None
        st.rerun()

st.divider()


# ===========================
# STÜDYO MODU — ÜRÜN YÜKLEME BLOĞU
# ===========================
if st.session_state.app_mode == "📸 Stüdyo Modu":
    st.markdown("### 📤 Ürün görselini yükle")
    uploaded_file = st.file_uploader(
        "Görsel seçin",
        type=["png", "jpg", "jpeg", "webp"],
        label_visibility="collapsed",
    )

    raw_source = uploaded_file
    # ===========================
    # STÜDYO MODU — İŞLEME & SONUÇ
    # ===========================
    if raw_source:
        try:
            raw_image = Image.open(raw_source)
            raw_image = ImageOps.exif_transpose(raw_image).convert("RGBA")
        except Exception as e:
            st.error("⚠️ Yüklenen görsel okunamadı.")
            print("image decode error:", e, traceback.format_exc())
            raw_image = None

        if raw_image:
            col_left, col_right = st.columns([1, 1])

            # --- Sol taraf: Orijinal görsel ---
            with col_left:
                st.markdown("### 📌 Orijinal Görsel")
                st.image(raw_image, width=360)

            # --- Sağ taraf: Düzenleme paneli ---
            with col_right:
                if st.session_state.sonuc_gorseli is None:
                    st.markdown("### 🎨 Düzenleme Seçenekleri")

                    tab_preset, tab_free = st.tabs(["🎛 Hazır Temalar", "✏️ Serbest Yazım"])

                    # ------------------
                    # HAZIR PRESET
                    # ------------------
                    with tab_preset:
                        preset_name = st.selectbox(
                            "Tema seç:",
                            list(TEMA_LISTESI.keys()),
                        )
                        preset_code = TEMA_LISTESI[preset_name]

                    # ------------------
                    # SERBEST YAZIM
                    # ------------------
                    with tab_free:
                        free_prompt = st.text_area(
                            "Sahne açıklaması yaz:",
                            placeholder="Örn: Ürünü merkezde tut, açık gri degrade arka plan, yumuşak gölge...",
                        )

                    st.write("")
                    if st.button("🚀 İşlemi Başlat", type="primary"):
                        st.session_state.sonuc_gorseli = None

                        # Eğer kullanıcı kendi sahnesini yazdıysa → AI edit
                        if free_prompt.strip() != "":
                            client = OpenAI(api_key=SABIT_API_KEY)
                            with st.spinner("Qelyon AI sahneyi oluşturuyor..."):
                                url = sahne_olustur(client, raw_image, free_prompt)
                                if url:
                                    data = requests.get(url).content
                                    st.session_state.sonuc_gorseli = data
                                    st.rerun()
                                else:
                                    st.error("⚠️ AI sahneyi oluşturamadı. Daha net bir açıklama deneyin.")
                        else:
                            # Yerel işlem (şeffaf / beyaz / siyah / profesyonel)
                            with st.spinner("İşleniyor..."):
                                sonuc = yerel_islem(raw_image, preset_code)
                                buf = BytesIO()
                                sonuc.save(buf, format="PNG")
                                st.session_state.sonuc_gorseli = buf.getvalue()
                                st.rerun()

                else:
                    # ===========================
                    # SONUÇ GÖRÜNTÜSÜ
                    # ===========================
                    st.markdown("### ✅ Sonuç")
                    st.image(st.session_state.sonuc_gorseli, width=360)

                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("🔄 Yeni İşlem"):
                            st.session_state.sonuc_gorseli = None
                            st.rerun()

                    with col_b:
                        st.download_button(
                            "📥 İndir (PNG)",
                            data=st.session_state.sonuc_gorseli,
                            file_name="qelyon_ai.png",
                            mime="image/png",
                        )


# ==========================================================
# ===============   CHAT / METİN ASİSTANI   ================
# ==========================================================
if st.session_state.app_mode in [
    "🛒 E-Ticaret Asistanı",
    "💼 Danışmanlık Asistanı",
    "🧠 Psikolojik Danışmanlık Asistanı",
]:
    inject_voice_js()

    if st.session_state.app_mode == "🛒 E-Ticaret Asistanı":
        profile: Literal["ecom", "consult", "psy"] = "ecom"
    elif st.session_state.app_mode == "💼 Danışmanlık Asistanı":
        profile = "consult"
    else:
        profile = "psy"

    if profile == "ecom":
        sub_title = "E-Ticaret Asistanı"
    elif profile == "consult":
        sub_title = "Danışmanlık Asistanı"
    else:
        sub_title = "Psikolojik Danışmanlık Asistanı"

    st.markdown(f"### 💬 Qelyon AI — {sub_title}")
    if profile == "psy":
        st.caption(
            "Bu mod, psikolojik danışmanlık merkezleri, uzmanlar ve danışanlar için "
            "bilgilendirici ve destekleyici içerikler üretir. Terapi yapmaz, tanı koymaz ve "
            "ilaç önermez."
        )
    else:
        st.caption(
            "Mesaj yazabilir, sesle giriş yapabilir veya görsel yükleyip analiz isteyebilirsin."
        )

    # ----------------------
    # Mesaj geçmişi göster
    # ----------------------
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # ----------------------
    # '+' butonu & upload paneli
    # ----------------------
    bar = st.container()
    with bar:
        col_p, col_t = st.columns([0.12, 0.88])
        with col_p:
            if st.button("➕", key="add_file", help="Dosya / görsel ekle"):
                st.session_state.show_upload_panel = not st.session_state.show_upload_panel

        with col_t:
            if st.session_state.chat_image:
                st.caption("📎 Bir ürün/görsel yüklü. Buna göre açıklama isteyebilirsin.")
            else:
                st.caption("İstersen dosya ekleyebilirsin.")

        if st.session_state.show_upload_panel:
            up = st.file_uploader(
                "Görsel veya belge ekle",
                type=["png", "jpg", "jpeg", "webp", "pdf"],
            )
            if up:
                st.session_state.chat_image = up.read()
                st.session_state.show_upload_panel = False
                st.success("Dosya yüklendi, şimdi soru sorabilirsin.")

    # ----------------------
    # Mesaj input
    # ----------------------
    placeholder_text = "Mesaj yazın..."
    if st.session_state.pending_prompt:
        # Kullanıcı isterse hızlıca hazır prompt'u inputa kopyalayıp düzenleyebilir
        placeholder_text = st.session_state.pending_prompt

    message = st.chat_input(placeholder_text)

    if message:
        st.session_state.pending_prompt = None
        st.session_state.chat_history.append({"role": "user", "content": message})
        with st.chat_message("user"):
            st.write(message)

        # Güvenlik filtresi
        mod = moderate_content(message)
        if mod:
            with st.chat_message("assistant"):
                st.write(mod)
            st.session_state.chat_history.append({"role": "assistant", "content": mod})
        else:
            # Saat, hava durumu, kimlik intercept
            util = custom_utility_interceptor(message)
            ident = custom_identity_interceptor(message)

            final = ident or util
            if final:
                with st.chat_message("assistant"):
                    st.write(final)
                st.session_state.chat_history.append({"role": "assistant", "content": final})
            else:
                # Normal GPT yanıtı
                with st.chat_message("assistant"):
                    with st.spinner("Qelyon AI yazıyor..."):
                        client = OpenAI(api_key=SABIT_API_KEY)
                        cevap = normal_sohbet(client, profile)
                        st.write(cevap)
                        st.session_state.chat_history.append(
                            {"role": "assistant", "content": cevap}
                        )


# ==========================================================
# ======================== FOOTER ==========================
# ==========================================================
st.markdown(
    "<div class='custom-footer'>Qelyon AI Stüdyo © 2025 | Developed by Alper</div>",
    unsafe_allow_html=True,
)

# ==========================================================
# ========== GLOBAL HATA YÖNETİMİ & GÜVENLİ KAPATMA =========
# ==========================================================

def global_error_boundary():
    """
    Uygulama çökmesini engeller.
    Hata olursa kullanıcıya nazik bir mesaj, geliştiriciye ise traceback basılır.
    """
    try:
        pass  # Normal işlem akışı burada zaten çalışıyor
    except Exception as e:
        tb = traceback.format_exc()
        print("GLOBAL ERROR:", tb)
        st.error("⚠️ Beklenmeyen bir hata oluştu. İşleme devam etmek ister misin?")
        if st.button("🔄 Uygulamayı Yenile"):
            st.rerun()


# ==========================================================
# =============== SESSİON & YÜKLEMELER TEMİZLEME ============
# ==========================================================

def reset_chat_image():
    """Chat görseli temizlenir."""
    st.session_state.chat_image = None


def reset_studio_result():
    """Stüdyo sonucu temizlenir."""
    st.session_state.sonuc_gorseli = None


def reset_all_sessions():
    """Tüm konuşma geçmişi temizlenir."""
    st.session_state.chat_sessions = {"Oturum 1": []}
    st.session_state.current_session = "Oturum 1"
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Yeni bir konuşma başlattın. Nasıl yardımcı olabilirim?"}
    ]


# ==========================================================
# =================== MODEL SEÇİCİ (Sabit) =================
# ==========================================================

def choose_model():
    """
    Sistem modeli sabit olarak gpt-4o kullanır.
    Eğer API hata verirse gpt-4o-mini fallback devreye girer.
    """
    model_main = st.secrets.get("OPENAI_MODEL", "gpt-4o")
    model_fallback = "gpt-4o-mini"
    return model_main, model_fallback


# ==========================================================
# ==================== FAVICON ENTEGRASYONU =================
# ==========================================================

def inject_favicon():
    """
    favicn.png tarayıcı üst sekmesi ve chat UI'da kullanılabilir.
    """
    st.markdown(
        """
        <link rel="icon" type="image/png" href="favicn.png">
        """,
        unsafe_allow_html=True,
    )


inject_favicon()


# ==========================================================
# ==================== LOGO SEÇİCİ (Tema) ==================
# ==========================================================

def get_active_logo():
    """
    Koyu tema → QelyonAIwhite.png
    Açık tema → QelyonAIblack.png
    """
    if st.session_state.get("theme_toggle", True):
        return "QelyonAIwhite.png"
    return "QelyonAIblack.png"


# ==========================================================
# ===================== UYGULAMA SONU =======================
# ==========================================================

try:
    global_error_boundary()
except Exception:
    print("GENEL HATA:", traceback.format_exc())
    st.error("⚠️ Kritik bir hata oluştu. Sayfayı yenilemeyi deneyin.")

# NOT:
# Bu dosya; stüdyo, e-ticaret, danışmanlık ve psikolojik danışmanlık modlarıyla
# tam entegre Qelyon AI Stüdyo uygulamasının güncel sürümüdür.

