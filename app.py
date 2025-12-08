# app.py

"""
Qelyon AI Stüdyo — v4.0 (E-Ticaret + Danışmanlık + Pro Stüdyo)

- Qelyon AI markası
- 3 Mod:
  • 📸 Stüdyo Modu (Görsel Düzenleme)
  • 🛒 E-Ticaret Asistanı
  • 💼 Danışmanlık Asistanı

- OPENAI_MODEL varsayılanı: gpt-4o
- İki logo:
  • Koyu tema: QelyonAIwhite.png
  • Açık tema: QelyonAIblack.png

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

import io
import base64
import re
import traceback
from datetime import datetime
from io import BytesIO
from typing import Literal
from zoneinfo import ZoneInfo

import requests
import streamlit as st
from openai import OpenAI
from PIL import Image, ImageFilter, ImageDraw, ImageOps, ImageChops
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
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===========================
# THEME & CSS
# ===========================
def get_theme(is_dark: bool):
    # Ana vurgu rengi: mor (#6C47FF)
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
    # 3 mod: Studio, E-Ticaret, Danışmanlık
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
# TEMA LİSTESİ (Sadeleştirilmiş)
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
    r"(?i)intihar",
    r"(?i)bomba yap",
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
            "Qelyon AI olarak, profesyonel danışmanlık ve veri destekli içgörülerle "
            "iş hedeflerine ulaşmanı hızlandırıyorum. 🚀\n\n"
            "Ürün görselleri, e-ticaret metinleri ve iş stratejisi tarafında sana eşlik ediyorum."
        )
    return None


def custom_utility_interceptor(user_message: str) -> str | None:
    msg = user_message.lower()

    # Saat / tarih
    if "saat" in msg or "tarih" in msg:
        # 'tarihi / tarihçesi' gibi tarih (history) isteklerine karışma
        if not re.search(r"\b(tarihi|tarihçesi|tarihcesi|geçmişi|gecmisi)\b", msg):
            return get_time_answer()

    # 7 günlük hava
    if "7 günlük hava" in msg or "7 gunluk hava" in msg or "haftalık hava" in msg:
        city = extract_city_from_message(user_message) or WEATHER_DEFAULT_CITY
        return get_weather_forecast_answer(city)

    # Genel hava
    if "hava" in msg or "hava durumu" in msg or "hava nasıl" in msg or "hava nasil" in msg:
        city = extract_city_from_message(user_message) or WEATHER_DEFAULT_CITY
        return get_weather_answer(city)

    return None


def build_system_talimati(profile: Literal["ecom", "consult"]) -> str:
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

    # Danışmanlık profili
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

# ===========================
# GPT-4o CHAT MOTORU
# ===========================
def normal_sohbet(client: OpenAI, profile: Literal["ecom", "consult"]) -> str:
    system_talimati = build_system_talimati(profile)
    max_context = 40
    history_slice = st.session_state.chat_history[-max_context:]

    messages: list[dict] = [{"role": "system", "content": system_talimati}]

    # Geçmişi ekle
    for i, msg in enumerate(history_slice):
        api_role = "user" if msg["role"] == "user" else "assistant"
        if api_role == "user":
            # Son kullanıcı mesajına görsel ekleme zaten aşağıda ayrıca ele alınacak,
            # burada olduğu gibi bırakıyoruz.
            messages.append({"role": "user", "content": msg["content"]})
        else:
            messages.append({"role": "assistant", "content": msg["content"]})

    # Son kullanıcı mesajını görselle birlikte tekrar ekleyelim (varsa)
    last_user = None
    for msg in reversed(history_slice):
        if msg["role"] == "user":
            last_user = msg["content"]
            break

    if last_user is not None:
        if st.session_state.get("chat_image") is not None:
            img_bytes = st.session_state.chat_image
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            content = [
                {"type": "text", "text": last_user},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": last_user})

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
        # Fallback: gpt-4o-mini
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


def _binary_mask(alpha: Image.Image, thresh: int = 5, dilate: int = 3, erode: int = 0) -> Image.Image:
    """Kritik: AI maskesinde ürün tamamen opak kalsın, kanama olmasın."""
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
    kare_resim = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    image = image.copy()
    image.thumbnail((850, 850), Image.Resampling.LANCZOS)
    x = (1024 - image.width) // 2
    y = (1024 - image.height) // 2
    kare_resim.paste(image, (x, y), image if image.mode == "RGBA" else None)
    return kare_resim


def _contact_shadow_from_alpha(alpha: Image.Image, strength: int = 110) -> Image.Image:
    """Beyaz/siyah/bej zemin için yumuşak 'temas gölgesi' üret."""
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
    can = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    im = im.copy()
    im.thumbnail((int(side * 0.85), int(side * 0.85)), Image.Resampling.LANCZOS)
    x = (side - im.width) // 2
    y = (side - im.height) // 2
    can.paste(im, (x, y), im)
    return can


def _reflection(clip: Image.Image, fade: int = 220) -> Image.Image:
    """Hafif zemin yansıması."""
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


def pro_studio_composite(cutout_rgba: Image.Image, bg: str = "white",
                         do_shadow: bool = True, do_reflection: bool = True) -> Image.Image:
    """
    Sonsuz arka plan + temas gölgesi + hafif refleksiyon.
    Ürün %100 korunur.
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
        return pro_studio_composite(cut, bg="white", do_shadow=True, do_reflection=True)

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
    st.sidebar.markdown("### 🧠 Qelyon AI Panel")

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

    prompt_exp = st.sidebar.expander("Metin & Kampanya (E-Ticaret)", expanded=False)
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
                "Markam için kısa ve vurucu bir kampanya / indirim duyurusu metni yaz. "
                "Ton: samimi, enerjik, aksiyona çağıran."
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

    consult_exp = st.sidebar.expander("💼 Danışmanlık Promptları", expanded=False)
    with consult_exp:
        if st.button("📊 İş modeli analizi", key="c_biz_model"):
            st.session_state.pending_prompt = (
                "İş modelimi analiz etmeni istiyorum. Önce bana birkaç soru sor, sonra güçlü ve zayıf yönlerimi "
                "özetleyip öneriler ver."
            )
        if st.button("📈 Büyüme stratejisi fikirleri", key="c_growth"):
            st.session_state.pending_prompt = (
                "Şirketim için sürdürülebilir büyüme stratejisi önerileri istiyorum. "
                "Hedef: gelir artışı ve kârlılık."
            )
        if st.button("🎯 KPI & OKR önerileri", key="c_kpi"):
            st.session_state.pending_prompt = (
                "Şirketim için ölçülebilir KPI ve OKR önerileri istiyorum. "
                "Önce sektör ve mevcut durum hakkında birkaç soru sor."
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
        "Bu platform, Qelyon AI altyapısıyla geliştirilmiş bir yapay zeka stüdyosudur. "
        "Ürün görsellerini profesyonel hale getirmek, e-ticaret metinleri ve danışmanlık içgörüleri üretmek için tasarlandı. 🚀"
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
    logo_path = LOGO_DARK_PATH if karanlik_mod else LOGO_LIGHT_PATH
    try:
        st.image(logo_path, use_column_width=True)
    except Exception:
        st.markdown("### Qelyon AI")
with header_right:
    st.markdown(
        """
        <h1 style="margin-bottom: 0.2rem;">Qelyon AI Stüdyo</h1>
        <p style="margin-top: 0; font-size: 0.95rem;">
        Ürününü ekle, e-ticaret ve sosyal medya için profesyonel sahneler oluştur;
        Qelyon AI ile içerik ve danışmanlık içgörülerini hazırla.
        </p>
        """,
        unsafe_allow_html=True,
    )

# Mod seçimi (3 mod)
col_studio, col_ecom, col_consult = st.columns(3, gap="small")
is_studio_active = st.session_state.app_mode == "📸 Stüdyo Modu (Görsel Düzenleme)"
is_ecom_active = st.session_state.app_mode == "🛒 E-Ticaret Asistanı"
is_consult_active = st.session_state.app_mode == "💼 Danışmanlık Asistanı"

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

with col_ecom:
    if st.button(
        "🛒 E-Ticaret Asistanı",
        key="btn_ecom",
        use_container_width=True,
        type="primary" if is_ecom_active else "secondary",
    ):
        st.session_state.app_mode = "🛒 E-Ticaret Asistanı"
        st.session_state.sonuc_gorseli = None
        st.rerun()

with col_consult:
    if st.button(
        "💼 Danışmanlık Asistanı",
        key="btn_consult",
        use_container_width=True,
        type="primary" if is_consult_active else "secondary",
    ):
        st.session_state.app_mode = "💼 Danışmanlık Asistanı"
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
                Ürününü farklı sahnelerde dene: beyaz fon, siyah fon, bej fon veya tamamen şeffaf arka plan.
                Hepsi tek tıkla.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="image-container">
                <h4 style="margin-bottom:4px;">✨ Profesyonel Dokunuş</h4>
                <p style="font-size:0.85rem; color:{tema['subtext']}; margin-bottom:0;">
                Temas gölgesi, hafif yansıma ve stüdyo ışığı ile ürününü gerçek bir stüdyo çekimi gibi gösterebilirsin.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="image-container">
                <h4 style="margin-bottom:4px;">📤 Kullanıma Hazır</h4>
                <p style="font-size:0.85rem; color:{tema['subtext']}; margin-bottom:0;">
                Oluşturduğun görselleri PNG/JPEG olarak indirip e-ticaret sitelerinde,
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
                        ["🎨 Hazır Temalar / Preset", "✏️ Serbest Yazım (AI)"]
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

                    with tab_serbest:
                        user_input = st.text_area(
                            "Hayalindeki sahneyi yaz:",
                            placeholder=(
                                "Örn: Arka planı açık gri degrade yap, zeminde yumuşak yansıma olsun, "
                                "ürün merkezde kalsın..."
                            ),
                            height=120,
                        )
                        if user_input:
                            final_prompt = (
                                "Professional product photography shot of the object. "
                                "Preserve the product exactly as-is (no color/shape change). "
                                f"{user_input}. High quality, realistic lighting, 8k, photorealistic."
                            )

                    st.write("")
                    buton_placeholder = st.empty()
                    if buton_placeholder.button("🚀 İşlemi Başlat", type="primary"):
                        inc_stat("studio_runs")
                        try:
                            if final_prompt and SABIT_API_KEY is not None:
                                client = OpenAI(api_key=SABIT_API_KEY)
                                with st.spinner("Qelyon AI sahneni oluşturuyor (10–30sn)... 🎨"):
                                    url = sahne_olustur(client, raw_image, final_prompt)
                                    if url:
                                        try:
                                            resp = requests.get(url, timeout=40)
                                            if resp.status_code == 200:
                                                st.session_state.sonuc_gorseli = resp.content
                                                st.session_state.sonuc_format = "PNG"
                                                st.rerun()
                                            else:
                                                st.error(
                                                    "AI görseli indirilemedi. Lütfen tekrar dene."
                                                )
                                        except Exception as e:
                                            st.error(
                                                "Sonuç indirilemedi. Lütfen tekrar dene."
                                            )
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
                                    fmt = "PNG"
                                    sonuc.save(buf, format=fmt)
                                    st.session_state.sonuc_gorseli = buf.getvalue()
                                    st.session_state.sonuc_format = fmt
                                    st.rerun()
                            else:
                                st.warning(
                                    "Lütfen bir hazır tema seç veya kendi sahneni yaz."
                                )
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
                                file_name=f"qelyon_pro.{st.session_state.sonuc_format.lower()}",
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
                                        file_name="qelyon_pro.png",
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

# ===========================
# SOHBET MODU (E-Ticaret & Danışmanlık)
# ===========================
def sohbet_ui(profile: Literal["ecom", "consult"]):
    inject_voice_js()

    if profile == "ecom":
        baslik = "💬 Qelyon AI — E-Ticaret Asistanı"
        aciklama = (
            "Ürün açıklamaları, başlıklar, etiketler ve kampanya metinleri için sorularını sorabilirsin. "
            "İstersen ürün görseli de ekleyebilirsin."
        )
    else:
        baslik = "💬 Qelyon AI — Danışmanlık Asistanı"
        aciklama = (
            "İş modeli, büyüme stratejisi, KPI/OKR ve operasyonel verimlilik konusunda soru sorabilirsin. "
            "İşini tanıtarak başlayabilirsin."
        )

    st.markdown(
        f'<div class="container-header">{baslik}</div>',
        unsafe_allow_html=True,
    )
    st.caption(aciklama)

    # Geçmiş mesajlar
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    st.write("")

    # '+' butonu ve uploader
    bottom_bar = st.container()
    with bottom_bar:
        col_plus, col_info = st.columns([0.12, 0.88])
        with col_plus:
            if st.button("➕", key=f"chat_plus_{profile}", help="Dosya / görsel ekle"):
                st.session_state.show_upload_panel = not st.session_state.show_upload_panel

        with col_info:
            if st.session_state.chat_image:
                st.caption(
                    "📎 Bir ürün/görsel yüklü. Yeni mesajlarında bu görsele göre açıklama veya analiz isteyebilirsin."
                )
            else:
                st.caption(
                    "İstersen '+' ile görsel veya dosya ekleyip Qelyon AI'dan buna göre yorum isteyebilirsin."
                )

        if st.session_state.show_upload_panel:
            chat_upload = st.file_uploader(
                "Görsel veya dosya yükle",
                type=["png", "jpg", "jpeg", "webp", "pdf", "txt"],
                key=f"chat_upload_{profile}",
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

    # Hazır prompt geldiyse input'u onunla doldur
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
                            with st.spinner("Qelyon AI yazıyor..."):
                                client = OpenAI(api_key=SABIT_API_KEY)
                                cevap = normal_sohbet(client, profile)
                                st.write(cevap)
                                st.session_state.chat_history.append(
                                    {"role": "assistant", "content": cevap}
                                )

    st.session_state.chat_sessions[st.session_state.current_session] = (
        st.session_state.chat_history
    )

# Chat modları
if st.session_state.app_mode == "🛒 E-Ticaret Asistanı":
    sohbet_ui("ecom")
elif st.session_state.app_mode == "💼 Danışmanlık Asistanı":
    sohbet_ui("consult")

# ===========================
# FOOTER
# ===========================
st.markdown(
    "<div class='custom-footer'>Qelyon AI Stüdyo © 2025 | Developed by Alper</div>",
    unsafe_allow_html=True,
)
