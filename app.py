# File: app.py
# Shopalm — E-Ticaret Yapay Zekâ Platformu (Advanced Studio + Transparent PNG + DPI)
from __future__ import annotations

import base64
import io
import re
import traceback
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
from rembg import remove

try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # type: ignore


# =========================
# Brand & Config
# =========================
BRAND_NAME = "Shopalm"
ACCENT = "#f39669"
LOGO_LIGHT_PATH = "shopalmblue.png"
LOGO_DARK_PATH = "shopalmwhite.png"
LOGO_FALLBACK_SVG = "shopalm.svg"

OPENAI_SECRET = st.secrets.get("OPENAI_API_KEY")
DEFAULT_MODEL = st.secrets.get("OPENAI_MODEL", "gpt-5.1")
FALLBACK_MODEL = "gpt-4o-mini"
SERPAPI_KEY = st.secrets.get("SERPAPI_API_KEY")

st.set_page_config(
    page_title=f"{BRAND_NAME} — E-Ticaret Yapay Zekâ",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

def _load_logo_b64(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None

LOGO_LIGHT_B64 = _load_logo_b64(LOGO_LIGHT_PATH)
LOGO_DARK_B64 = _load_logo_b64(LOGO_DARK_PATH)
LOGO_FALLBACK_B64 = _load_logo_b64(LOGO_FALLBACK_SVG)


# =========================
# Theme & CSS
# =========================
def theme_vars(dark: bool) -> Dict[str, str]:
    if dark:
        return {
            "bg": "#0a0b0d",
            "card": "rgba(255,255,255,0.05)",
            "text": "#e8eef6",
            "sub": "#b9c6d6",
            "border": "rgba(255,255,255,0.08)",
            "input": "rgba(255,255,255,0.06)",
            "accent": ACCENT,
            "hover": "#e07e4d",
        }
    return {
        "bg": "#fffaf6",
        "card": "rgba(255,255,255,0.9)",
        "text": "#1f1410",
        "sub": "#7a5b4b",
        "border": "rgba(12,17,25,0.06)",
        "input": "rgba(255,255,255,0.95)",
        "accent": ACCENT,
        "hover": "#e07e4d",
    }

def inject_css(p: Dict[str, str]) -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
:root {{
  --bg: {p['bg']}; --card: {p['card']}; --text: {p['text']}; --sub: {p['sub']};
  --border: {p['border']}; --input: {p['input']}; --accent: {p['accent']}; --hover: {p['hover']};
}}
html, body, .stApp {{ background: var(--bg); color: var(--text);
  font-family: -apple-system,BlinkMacSystemFont,Inter,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }}
#MainMenu, footer, header, [data-testid="stToolbar"] {{ display:none !important; }}
.block-container {{ padding-top: 0.8rem; padding-bottom: 4rem; max-width: 1240px; }}
.card {{ background: var(--card); border: 1px solid var(--border); border-radius: 18px; padding: 14px 16px;
  backdrop-filter: blur(14px) saturate(120%); box-shadow: 0 6px 24px rgba(2,6,23,0.10); }}
.hint {{ color: var(--sub); font-size: 0.9rem; }}
.brand-btn .stButton>button {{ background: var(--accent) !important; color:#fff !important; border:none !important;
  border-radius:12px !important; padding:9px 14px !important; font-weight:700 !important; }}
.brand-btn .stButton>button:hover {{ background: var(--hover) !important; transform: translateY(-1px); }}
.stTextArea textarea, .stTextInput input {{ background: var(--input) !important; color: var(--text) !important;
  border: 1px solid var(--border) !important; border-radius: 12px !important; }}
[data-testid="stChatMessage"] {{ background: var(--card); border: 1px solid var(--border); border-radius: 16px; }}
.mic-btn {{ margin-left:8px; border-radius:999px; border:none; cursor:pointer; padding:4px 10px;
  background: var(--accent); color:white; font-size:16px; }}
.logo-subtitle {{ margin-top:6px; color: var(--text); font-size:0.95rem; font-weight:700; line-height:1.1; text-align:left; }}
.tagline {{ margin:4px 0 0 0; color: var(--accent); font-size:1rem; font-weight:700; text-align:left; }}
</style>
""",
        unsafe_allow_html=True,
    )

def inject_voice_button() -> None:
    st.markdown(
        """
<script>
(function(){
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if(!SR) return;
  function add(){
    const root = window.parent.document.querySelector('[data-testid="stChatInput"]');
    if(!root || root.querySelector('#shopalm-mic')) return;
    const textarea = root.querySelector('textarea'); if(!textarea) return;
    const btn = document.createElement('button');
    btn.id='shopalm-mic'; btn.className='mic-btn'; btn.textContent='🎤';
    const rec = new SR(); rec.lang='tr-TR'; rec.interimResults=false; rec.maxAlternatives=1;
    rec.onresult = (e)=>{ const t=e.results[0][0].transcript; textarea.value = textarea.value? textarea.value+' '+t: t; textarea.dispatchEvent(new Event('input',{bubbles:true})); };
    btn.onclick=(ev)=>{ ev.preventDefault(); try{rec.start()}catch(e){} };
    root.appendChild(btn);
  }
  setInterval(add,1200);
})();
</script>
""",
        unsafe_allow_html=True,
    )


# =========================
# Session
# =========================
def ensure_session() -> None:
    ss = st.session_state
    ss.setdefault("dark_mode", True)
    ss.setdefault("page", "🖼 Görsel Stüdyo")
    # chat
    ss.setdefault("chat_sessions", {})
    ss.setdefault("current_session", "Oturum 1")
    ss.setdefault("messages", [{"role":"assistant","content":f"Merhaba! Ben {BRAND_NAME}. E-ticaretle ilgili nasıl yardımcı olabilirim?"}])
    ss.setdefault("uploads", 0)
    ss.setdefault("chat_image_bytes", None)
    # studio state
    ss.setdefault("studio_src_bytes", None)
    ss.setdefault("studio_fg_rgba", None)
    ss.setdefault("studio_result_bytes", None)
    ss.setdefault("studio_result_fmt", "PNG")
    ss.setdefault("studio_result_size", (0,0))
    ss.setdefault("bg_mode", "COLOR")  # COLOR|PRESET|UPLOAD|URL|SEARCH
    ss.setdefault("bg_color", "#ffffff")
    ss.setdefault("bg_preset", "BRAND")
    ss.setdefault("bg_url", "")
    ss.setdefault("bg_upload_bytes", None)
    ss.setdefault("fx_blur", 0.0)
    ss.setdefault("fx_brightness", 1.0)
    ss.setdefault("fx_contrast", 1.0)
    ss.setdefault("fg_scale", 100)
    ss.setdefault("fg_offset_x", 0)
    ss.setdefault("fg_offset_y", 20)
    ss.setdefault("add_shadow", True)
    ss.setdefault("canvas_size", 1200)
    ss.setdefault("crop_ratio", "1:1")
    # Export controls
    ss.setdefault("export_format", "PNG")   # PNG | JPEG | WEBP
    ss.setdefault("export_edge", 1600)      # longest edge
    ss.setdefault("jpeg_quality", 95)       # 60–100
    ss.setdefault("png_compress", 6)        # 0–9
    ss.setdefault("export_transparent", False)  # NEW: transparent PNG
    ss.setdefault("export_dpi", 300)            # NEW: DPI for PNG/JPEG
    # misc
    ss.setdefault("prefill_prompt", None)
    ss.setdefault("analytics", {"chat":0,"studio_runs":0,"exports":0,"price_scans":0})
    if "Oturum 1" not in ss["chat_sessions"]:
        ss["chat_sessions"]["Oturum 1"] = ss["messages"]

def bump(k: str, step: int = 1) -> None:
    try:
        st.session_state["analytics"][k] = st.session_state["analytics"].get(k, 0) + step
    except Exception:
        pass


# =========================
# Guard (chat)
# =========================
ALLOW_KEYWORDS = [
    "ürün","product","fiyat","price","stok","stock","sku","kargo","shipping","kategori","category","seo",
    "başlık","title","etiket","tag","varyant","variant","kampanya","campaign","dönüşüm","conversion",
    "açıklama","description","pazaryeri","trendyol","hepsiburada","amazon","etsy","shopify","özellik",
    "bundle","set","yorum","review","reklam","ads","meta","facebook","instagram","tiktok","e-ticaret",
    "ecommerce","checkout","sepet","iade","garanti","kullanım","müşteri","customer","satış","sales",
    "landing","listing","fotoğraf","görsel","fotograf","rembg","arka plan","background","ürün fotoğrafı"
]
def is_ecommerce_query(text: str) -> bool:
    t = text.lower()
    if any(k in t for k in ALLOW_KEYWORDS): return True
    return bool(re.search(r"\b(e-?ticaret|ecommerce|ürün|fiyat|seo)\b", t))
NON_COMMERCE_MSG = ("Sadece e-ticaretle ilgili konularda yardımcı oluyorum. Örnekler: "
    "ürün açıklaması, SEO başlık/etiket, fiyatlandırma, varyantlar, kampanya metinleri, yorum analizi…")


# =========================
# LLM (short)
# =========================
@dataclass
class LLMConfig:
    model: str = DEFAULT_MODEL
    temperature: float = 0.25
    max_tokens: int = 1500

def call_llm(messages: List[Dict[str, Any]], model: Optional[str] = None) -> str:
    if OpenAI is None or not OPENAI_SECRET:
        return "DEMO: LLM anahtarı yok. Ürün açıklaması/başlık/etiket/fiyat vb. için anahtar ekleyin."
    try:
        client = OpenAI(api_key=OPENAI_SECRET)
        resp = client.chat.completions.create(
            model=model or DEFAULT_MODEL, messages=messages, temperature=0.25, max_tokens=1500
        )
        return getattr(resp.choices[0].message, "content", resp.choices[0].text)
    except Exception:
        try:
            client = OpenAI(api_key=OPENAI_SECRET)
            resp = client.chat.completions.create(
                model=FALLBACK_MODEL, messages=messages, temperature=0.25, max_tokens=1500
            )
            return getattr(resp.choices[0].message, "content", resp.choices[0].text)
        except Exception as e2:
            print("LLM ERROR:", e2, traceback.format_exc())
            return "Şu an yanıt veremiyorum."

def system_identity(lang: str = "tr") -> str:
    return (f"Adın {BRAND_NAME}. E-ticaret asistanısın. Sadece e-ticaret sorularına cevap ver. "
            "Uydurma yapma; net ve maddelerle yaz. Eksikse kısa sorular sor. Çıktıları iyi biçimlendir.")
def mk_messages(user_content: Any, lang: str = "tr") -> List[Dict[str, Any]]:
    return [{"role":"system","content":system_identity(lang)}, {"role":"user","content":user_content}]


# =========================
# SerpAPI — Google Images
# =========================
def search_backgrounds_serpapi(query: str, num: int = 8) -> List[Tuple[str, str, str]]:
    if not SERPAPI_KEY:
        return []
    url = "https://serpapi.com/search.json"
    params = {"engine":"google_images","q":query,"hl":"tr","gl":"tr","ijn":"0","api_key":SERPAPI_KEY}
    r = requests.get(url, params=params, timeout=40)
    r.raise_for_status()
    data = r.json()
    items = data.get("images_results", [])[:num]
    out: List[Tuple[str,str,str]] = []
    for it in items:
        thumb = it.get("thumbnail")
        org = it.get("original") or it.get("link")
        src = it.get("source") or ""
        if thumb and org:
            out.append((thumb, org, src))
    return out


# =========================
# Studio — Imaging
# =========================
def extract_fg(img: Image.Image) -> Image.Image:
    try:
        return remove(img, alpha_matting=True, alpha_matting_foreground_threshold=250,
                      alpha_matting_background_threshold=5, alpha_matting_erode_size=0)
    except Exception:
        return img.convert("RGBA")

def soft_shadow(alpha: Image.Image, blur: int = 12, strength: float = 0.45) -> Image.Image:
    a = alpha.point(lambda p: int(p * strength))
    a = a.filter(ImageFilter.GaussianBlur(radius=blur))
    sh = Image.new("RGBA", alpha.size, (0,0,0,0))
    sh.paste((0,0,0,140), (3,10), a)
    return sh

def preset_background(name: str, size: int) -> Image.Image:
    w = h = size
    if name == "BRAND":
        grad = Image.new("RGBA", (w, h))
        top = (243,150,105,255); bottom = (255,236,227,255)
        for y in range(h):
            t = y / max(1,h-1)
            r = int(top[0]*(1-t)+bottom[0]*t); g = int(top[1]*(1-t)+bottom[1]*t); b = int(top[2]*(1-t)+bottom[2]*t)
            grad.paste((r,g,b,255), (0,y,w,y+1))
        return grad
    if name == "STUDIO_GRAY":
        grad = Image.new("RGBA", (w, h))
        top = (240,240,240,255); bottom = (210,210,210,255)
        for y in range(h):
            t = y / max(1,h-1)
            val = int(top[0]*(1-t)+bottom[0]*t)
            grad.paste((val,val,val,255),(0,y,w,y+1))
        return grad
    if name == "BLACK":
        return Image.new("RGBA", (w,h), (0,0,0,255))
    if name == "BEIGE":
        return Image.new("RGBA", (w,h), (245,235,220,255))
    return Image.new("RGBA", (w,h), (255,255,255,255))

def load_image_from_url(url: str, size_hint: int) -> Optional[Image.Image]:
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content)).convert("RGBA")
        im = ImageOps.exif_transpose(im)
        im = ImageOps.contain(im, (size_hint, size_hint))
        return im
    except Exception:
        return None

def apply_bg_effects(bg: Image.Image, blur: float, brightness: float, contrast: float) -> Image.Image:
    if blur > 0:
        bg = bg.filter(ImageFilter.GaussianBlur(radius=float(blur)))
    if brightness != 1.0:
        bg = ImageEnhance.Brightness(bg).enhance(brightness)
    if contrast != 1.0:
        bg = ImageEnhance.Contrast(bg).enhance(contrast)
    return bg

def compose(bg: Image.Image, fg_rgba: Image.Image, scale_pct: int, off_x: int, off_y: int, shadow: bool) -> Image.Image:
    W, H = bg.size
    fg = fg_rgba.copy()
    target = int(min(W, H) * (scale_pct/100.0))
    fg.thumbnail((target, target), Image.Resampling.LANCZOS)
    x = (W - fg.width)//2 + int(off_x)
    y = (H - fg.height)//2 + int(off_y)
    base = bg.copy()
    if shadow:
        sh = soft_shadow(fg.split()[-1], blur=12, strength=0.45)
        tmp = Image.new("RGBA", base.size, (0,0,0,0))
        tmp.paste(sh, (x, y), sh)
        base = Image.alpha_composite(base, tmp)
    base.paste(fg, (x, y), fg)
    return base

def apply_crop(img: Image.Image, ratio: str) -> Image.Image:
    W, H = img.size
    if ratio == "1:1":
        side = min(W, H); return ImageOps.fit(img, (side, side), Image.Resampling.LANCZOS, centering=(0.5,0.5))
    ratios = {"4:5": 4/5, "3:4": 3/4, "16:9": 16/9}
    if ratio in ratios:
        target = ratios[ratio]
        cur = W/H
        if cur > target:
            new_w = int(H*target); return ImageOps.fit(img, (new_w, H), Image.Resampling.LANCZOS, centering=(0.5,0.5))
        else:
            new_h = int(W/target); return ImageOps.fit(img, (W, new_h), Image.Resampling.LANCZOS, centering=(0.5,0.5))
    return img

def render_studio() -> Tuple[Optional[bytes], str, Tuple[int,int]]:
    """Returns (bytes, fmt, (W,H)) with export controls applied."""
    ss = st.session_state
    if not ss.get("studio_fg_rgba"):
        return None, "PNG", (0,0)
    size = int(ss["canvas_size"])

    fmt = ss.get("export_format", "PNG").upper()
    transparent = bool(ss.get("export_transparent", False) and fmt == "PNG")  # sadece PNG'de anlamlı

    # background build (şeffaf PNG istenirse BG'yi yok say)
    if transparent:
        bg = Image.new("RGBA", (size, size), (0,0,0,0))
    else:
        mode = ss["bg_mode"]
        if mode == "COLOR":
            color_hex = ss.get("bg_color", "#ffffff").lstrip("#")
            r = int(color_hex[0:2],16); g=int(color_hex[2:4],16); b=int(color_hex[4:6],16)
            bg = Image.new("RGBA", (size,size), (r,g,b,255))
        elif mode == "PRESET":
            bg = preset_background(ss.get("bg_preset","BRAND"), size)
        elif mode == "UPLOAD":
            if not ss.get("bg_upload_bytes"): return None, fmt, (0,0)
            bg = Image.open(io.BytesIO(ss["bg_upload_bytes"])).convert("RGBA")
            bg = ImageOps.exif_transpose(bg)
            bg = ImageOps.fit(bg, (size,size), Image.Resampling.LANCZOS)
        elif mode in ("URL","SEARCH"):
            im = load_image_from_url(ss.get("bg_url",""), size)
            if im is None: return None, fmt, (0,0)
            bg = ImageOps.fit(im, (size,size), Image.Resampling.LANCZOS)
        else:
            bg = Image.new("RGBA", (size,size), (255,255,255,255))
        bg = apply_bg_effects(bg, ss.get("fx_blur",0.0), ss.get("fx_brightness",1.0), ss.get("fx_contrast",1.0))

    comp = compose(
        bg,
        Image.open(io.BytesIO(ss["studio_fg_rgba"])).convert("RGBA"),
        int(ss.get("fg_scale",100)),
        int(ss.get("fg_offset_x",0)),
        int(ss.get("fg_offset_y",0)),
        bool(ss.get("add_shadow",True)),
    )
    comp = apply_crop(comp, ss.get("crop_ratio","1:1"))

    # Export scaling
    export_edge = int(ss.get("export_edge", 1600))
    W, H = comp.size
    if export_edge > 0 and max(W,H) != export_edge:
        scale = export_edge / max(W,H)
        comp = comp.resize((int(W*scale), int(H*scale)), Image.Resampling.LANCZOS)
        W, H = comp.size

    # Save with DPI/quality
    dpi = int(ss.get("export_dpi", 300))
    buf = io.BytesIO()
    if fmt == "PNG":
        comp.save(buf, format="PNG", compress_level=int(ss.get("png_compress",6)), dpi=(dpi, dpi))
    elif fmt == "JPEG":
        comp_rgb = comp.convert("RGB")
        comp_rgb.save(buf, format="JPEG", quality=int(ss.get("jpeg_quality",95)), subsampling=0, optimize=True, dpi=(dpi, dpi))
    elif fmt == "WEBP":
        comp.save(buf, format="WEBP", quality=int(ss.get("jpeg_quality",95)))  # WEBP'de DPI çoğu görüntüleyicide desteklenmez
    else:
        fmt = "PNG"; comp.save(buf, format="PNG", dpi=(dpi, dpi))
    buf.seek(0)
    return buf.getvalue(), fmt, (W,H)


# =========================
# UI — Header / Sidebar
# =========================
def header_ui(dark: bool) -> None:
    with st.container():
        c1, c2 = st.columns([0.15, 0.85], gap="small")
        with c1:
            logo_b64 = LOGO_DARK_B64 if dark else LOGO_LIGHT_B64
            if not logo_b64:
                logo_b64 = LOGO_FALLBACK_B64; mime = "image/svg+xml"
            else:
                mime = "image/png"
            if logo_b64:
                st.markdown(
                    f"<img src='data:{mime};base64,{logo_b64}' style='max-width:160px;width:100%;display:block;'>",
                    unsafe_allow_html=True,
                )
            st.markdown("<div class='logo-subtitle'>E-Ticaret Yapay Zeka</div>", unsafe_allow_html=True)
        with c2:
            st.markdown(
                "<div class='tagline'>Ürün listelemeleri, SEO, fiyatlandırma, varyantlar, reklam ve görsel stüdyo — tek yerde.</div>",
                unsafe_allow_html=True,
            )

def sidebar_nav() -> None:
    st.sidebar.markdown("### 🧠 Shopalm Panel")
    page = st.sidebar.radio(
        "Sayfa",
        ["🖼 Görsel Stüdyo", "💬 Chat", "📊 Analytics", "⚙️ Ayarlar"],
        index=["🖼 Görsel Stüdyo", "💬 Chat", "📊 Analytics", "⚙️ Ayarlar"].index(st.session_state["page"]),
    )
    if page != st.session_state["page"]:
        st.session_state["page"] = page; st.experimental_rerun()

    st.sidebar.markdown("---")
    st.sidebar.caption("Shopalm © 2025 — Sadece e-ticaret odaklı.")


# =========================
# Pages
# =========================
def page_studio() -> None:
    st.markdown("### 🖼 Görsel Stüdyo")
    st.caption("Arka planı değiştir, efekt uygula, konumlandır, kırp, **şeffaf PNG/DPI** ile yüksek çözünürlükte indir.")

    up = st.file_uploader("Ürün görseli yükle", type=["png","jpg","jpeg","webp"], key="studio_up")
    if up is not None:
        st.session_state["studio_src_bytes"] = up.read()
        try:
            im = Image.open(io.BytesIO(st.session_state["studio_src_bytes"]))
            im = ImageOps.exif_transpose(im).convert("RGBA")
            fg = extract_fg(im)
            buf = io.BytesIO(); fg.save(buf, format="PNG"); buf.seek(0)
            st.session_state["studio_fg_rgba"] = buf.getvalue()
            st.success("Ürün ayrıştırıldı.")
        except Exception as e:
            st.error("Görsel işlenemedi."); print("FG ERR:", e)

    left, right = st.columns([0.55, 0.45], gap="large")

    with left:
        st.markdown("#### Önizleme")
        if st.session_state.get("studio_result_bytes"):
            W,H = st.session_state.get("studio_result_size",(0,0))
            st.image(st.session_state["studio_result_bytes"], use_container_width=True, caption=f"Önizleme — {W}×{H}px")
        elif st.session_state.get("studio_fg_rgba"):
            st.image(st.session_state["studio_fg_rgba"], use_container_width=True, caption="Ayrıştırılmış ürün (şeffaf)")

        coldl, coldr = st.columns(2)
        with coldl:
            if st.button("🚀 Uygula / Render", type="primary", use_container_width=True):
                result, fmt, size = render_studio()
                if result:
                    st.session_state["studio_result_bytes"] = result
                    st.session_state["studio_result_fmt"] = fmt
                    st.session_state["studio_result_size"] = size
                    bump("studio_runs")
                else:
                    st.warning("Arka plan veya ürün hazır değil.")
        with coldr:
            if st.session_state.get("studio_result_bytes"):
                W,H = st.session_state.get("studio_result_size",(0,0))
                ext = "jpg" if st.session_state["studio_result_fmt"].upper()=="JPEG" else st.session_state["studio_result_fmt"].lower()
                mime = "image/jpeg" if ext=="jpg" else f"image/{ext}"
                dpi = int(st.session_state.get("export_dpi",300))
                st.download_button(
                    label=f"📥 İndir ({W}x{H}@{dpi}dpi.{ext})",
                    data=st.session_state["studio_result_bytes"],
                    file_name=f"shopalm_{W}x{H}@{dpi}dpi.{ext}",
                    mime=mime,
                    use_container_width=True,
                )

    with right:
        tabs = st.tabs(["Arka plan", "Efektler", "Düzenle", "Kesme"])
        with tabs[0]:
            st.markdown("**Mod**")
            st.session_state["bg_mode"] = st.radio(
                "", ["COLOR","PRESET","UPLOAD","URL","SEARCH"], horizontal=True, index=["COLOR","PRESET","UPLOAD","URL","SEARCH"].index(st.session_state["bg_mode"])
            )
            mode = st.session_state["bg_mode"]
            if mode == "COLOR":
                st.session_state["bg_color"] = st.color_picker("Arka plan rengi", value=st.session_state["bg_color"])
            elif mode == "PRESET":
                st.session_state["bg_preset"] = st.selectbox("Hazır fon", ["WHITE","BLACK","BEIGE","STUDIO_GRAY","BRAND"], index=["WHITE","BLACK","BEIGE","STUDIO_GRAY","BRAND"].index(st.session_state["bg_preset"]))
            elif mode == "UPLOAD":
                upbg = st.file_uploader("Arka plan görseli (png/jpg/webp)", type=["png","jpg","jpeg","webp"], key="bg_up")
                if upbg is not None:
                    st.session_state["bg_upload_bytes"] = upbg.read(); st.success("Arka plan yüklendi.")
            elif mode == "URL":
                st.session_state["bg_url"] = st.text_input("Arka plan URL", value=st.session_state.get("bg_url",""))
            else:  # SEARCH
                q = st.text_input("Google görsel araması", value="studio background bokeh")
                if st.button("Ara", type="primary"):
                    if not SERPAPI_KEY:
                        st.warning("SerpAPI anahtarı ekleyin: st.secrets['SERPAPI_API_KEY']")
                    else:
                        try:
                            results = search_backgrounds_serpapi(q, num=9)
                            st.session_state["bg_search_results"] = results
                        except Exception as e:
                            st.error("Arama başarısız."); print("SERPAPI IMG ERR:", e)
                res = st.session_state.get("bg_search_results", [])
                if res:
                    cols = st.columns(3)
                    for i, (thumb, org, src) in enumerate(res):
                        with cols[i%3]:
                            st.image(thumb, use_container_width=True, caption=src, output_format="PNG")
                            if st.button("Seç", key=f"bgsel_{i}"):
                                st.session_state["bg_url"] = org
                                st.success("Arka plan seçildi.")

        with tabs[1]:
            st.session_state["fx_blur"] = st.slider("Arka plan blur", 0.0, 30.0, float(st.session_state["fx_blur"]), 0.5)
            st.session_state["fx_brightness"] = st.slider("Parlaklık", 0.2, 2.0, float(st.session_state["fx_brightness"]), 0.05)
            st.session_state["fx_contrast"] = st.slider("Kontrast", 0.2, 2.0, float(st.session_state["fx_contrast"]), 0.05)

        with tabs[2]:
            st.session_state["fg_scale"] = st.slider("Ürün ölçeği (%)", 40, 160, int(st.session_state["fg_scale"]), 1)
            st.session_state["fg_offset_x"] = st.slider("X konum", -300, 300, int(st.session_state["fg_offset_x"]), 1)
            st.session_state["fg_offset_y"] = st.slider("Y konum", -300, 300, int(st.session_state["fg_offset_y"]), 1)
            st.session_state["add_shadow"] = st.toggle("Yumuşak gölge", value=bool(st.session_state["add_shadow"]))
            st.session_state["canvas_size"] = st.slider("Kanvas (px)", 800, 3000, int(st.session_state["canvas_size"]), 50)

            st.markdown("---")
            st.markdown("**Dışa aktarma**")
            st.session_state["export_format"] = st.selectbox("Format", ["PNG","JPEG","WEBP"], index=["PNG","JPEG","WEBP"].index(st.session_state["export_format"]))
            st.session_state["export_edge"] = st.slider("Uzun kenar (px)", 800, 4096, int(st.session_state["export_edge"]), 50)
            if st.session_state["export_format"] == "JPEG":
                st.session_state["jpeg_quality"] = st.slider("JPEG kalite", 60, 100, int(st.session_state["jpeg_quality"]), 1)
            if st.session_state["export_format"] == "PNG":
                st.session_state["png_compress"] = st.slider("PNG sıkıştırma (0 hızlı / 9 küçük)", 0, 9, int(st.session_state["png_compress"]), 1)
                st.session_state["export_transparent"] = st.toggle("Şeffaf PNG (arka planı yok say)", value=bool(st.session_state["export_transparent"]))
            # DPI both for PNG/JPEG (WEBP çoğu istemcide yok)
            st.session_state["export_dpi"] = st.number_input("DPI (PNG/JPEG)", min_value=72, max_value=600, value=int(st.session_state["export_dpi"]), step=1, help="Baskı için 300 dpi önerilir.")

        with tabs[3]:
            st.session_state["crop_ratio"] = st.selectbox("Kırpma oranı", ["1:1","4:5","3:4","16:9"], index=["1:1","4:5","3:4","16:9"].index(st.session_state["crop_ratio"]))

def page_chat() -> None:
    inject_voice_button()
    st.markdown("<div class='card'>💬 <b>Chat</b> — Sadece e-ticaret sorularına yanıt verir.</div>", unsafe_allow_html=True)
    st.write("")
    for m in st.session_state["messages"]:
        with st.chat_message(m["role"]): st.write(m["content"])

    with st.container():
        cols = st.columns([0.22,0.78])
        with cols[0]:
            if st.button("➕ Dosya/Görsel", help="Ürün görseli ekle (analiz için)"):
                st.session_state["show_uploader"] = not st.session_state.get("show_uploader", False)
        with cols[1]:
            if st.session_state.get("chat_image_bytes"):
                st.caption("📎 Bir ürün görseli yüklü.")
                try:
                    st.image(Image.open(io.BytesIO(st.session_state["chat_image_bytes"])), width=220, caption="Önizleme")
                except Exception: pass
            else:
                st.caption("İpucu: Görsel yüklersen açıklama/özellikler için analiz edilir.")

    if st.session_state.get("show_uploader", False):
        up = st.file_uploader("Görsel (png/jpg/webp)", type=["png","jpg","jpeg","webp"], key="chat_uploader")
        if up is not None:
            st.session_state["chat_image_bytes"] = up.read(); st.session_state["uploads"] += 1
            try:
                st.image(Image.open(io.BytesIO(st.session_state["chat_image_bytes"])), width=300, caption="Görsel yüklendi (Önizleme)")
            except Exception: st.success("Görsel yüklendi.")
            st.session_state["show_uploader"] = False

    user_input = st.chat_input("E-ticaret sorunu yaz...")
    if not user_input: return

    st.session_state["messages"].append({"role":"user","content":user_input})
    with st.chat_message("user"): st.write(user_input)

    if not is_ecommerce_query(user_input):
        with st.chat_message("assistant"): st.write(NON_COMMERCE_MSG)
        st.session_state["messages"].append({"role":"assistant","content":NON_COMMERCE_MSG})
        return

    if st.session_state.get("chat_image_bytes") and OPENAI_SECRET and OpenAI is not None:
        b64 = base64.b64encode(st.session_state["chat_image_bytes"]).decode("utf-8")
        content: Any = [{"type":"text","text":user_input},{"type":"image_url","image_url":{"url":f"data:image/png;base64,{b64}"}}]
    else:
        content = user_input

    with st.chat_message("assistant"):
        with st.spinner("Shopalm yazıyor…"):
            answer = call_llm(mk_messages(content))
            st.write(answer)
            st.session_state["messages"].append({"role":"assistant","content":answer})

def page_analytics() -> None:
    st.markdown("### 📊 Analytics")
    a = st.session_state["analytics"]; cols = st.columns(3)
    for i,(k,v) in enumerate(a.items()): 
        with cols[i%3]: st.metric(label=k, value=v)

def page_settings() -> None:
    st.markdown("### ⚙️ Ayarlar")
    st.write("**SerpAPI** (Google Images arka plan araması) için `SERPAPI_API_KEY` secrets ekleyin.")
    st.write("**OpenAI** için `OPENAI_API_KEY` secrets ekleyin. Model varsayılanı:", DEFAULT_MODEL)
    if st.button("🔁 Oturumu sıfırla"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        ensure_session(); st.success("Sıfırlandı."); st.experimental_rerun()


# =========================
# App
# =========================
def header_and_nav():
    st.session_state["dark_mode"] = st.toggle("🌙 / ☀️", value=st.session_state.get("dark_mode", True), key="theme_toggle")
    inject_css(theme_vars(st.session_state["dark_mode"]))
    header_ui(st.session_state["dark_mode"])
    sidebar_nav()
    st.divider()

def main() -> None:
    ensure_session()
    header_and_nav()
    page = st.session_state["page"]
    if page == "🖼 Görsel Stüdyo":
        page_studio()
    elif page == "💬 Chat":
        page_chat()
    elif page == "📊 Analytics":
        page_analytics()
    else:
        page_settings()
    st.markdown(
        "<div style='position:fixed;left:0;bottom:0;width:100%;padding:10px 6px;text-align:center;"
        "background:rgba(0,0,0,0.03);backdrop-filter:blur(8px);border-top:1px solid var(--border);' "
        "class='hint'>Shopalm © 2025 — E-Ticaret için üretildi.</div>",
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()
