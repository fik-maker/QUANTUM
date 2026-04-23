import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import requests
from pathlib import Path

st.set_page_config(
    page_title="Quantum Post Generator",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #111318; }
  [data-testid="stHeader"] { background: transparent; }
  h1, h2, h3 { color: #FFE600 !important; }
  label { color: #e0e0e0 !important; }
  .stButton > button {
    background: #FFE600 !important; color: #111 !important;
    font-weight: 800; border: none; border-radius: 10px; font-size: 16px;
  }
  .stButton > button:hover { background: #FFD000 !important; }
  [data-testid="stDownloadButton"] > button {
    background: #2A9A2A !important; color: #fff !important;
    font-weight: 700; border: none; border-radius: 10px;
  }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
W, H = 1080, 1350
MARGIN = 55
FONT_DIR = Path("fonts")
FONT_PATH = FONT_DIR / "FredokaOne.ttf"
FONT_URL = "https://cdn.jsdelivr.net/gh/google/fonts/ofl/fredokaone/FredokaOne-Regular.ttf"

# ── Presets basados en los diseños reales ──────────────────────────────────────
PRESETS = {
    "🟢🔵  Verde + Azul  (DUOS)": {
        "bg_top": "#1B6B1B", "bg_bottom": "#4B90D5", "divider": "",
        "intro": "#FFFFFF",  "title": "#FFE600",
        "tagline": "#FFFFFF","badge_bg": "#1B6B1B", "badge_txt": "#FFFFFF",
    },
    "🟢  Verde oscuro  (Fruit Fight / No Thanks)": {
        "bg_top": "#1E6E1E", "bg_bottom": "#1E6E1E", "divider": "",
        "intro": "#FFE600",  "title": "#FFE600",
        "tagline": "#C8E84A","badge_bg": "#2A9A2A", "badge_txt": "#FFFFFF",
    },
    "🟤  Marrón  (Figment)": {
        "bg_top": "#6B2A15", "bg_bottom": "#6B2A15", "divider": "#3DB53D",
        "intro": "#FFE600",  "title": "#3DB53D",
        "tagline": "#FFFFFF","badge_bg": "#3DB53D", "badge_txt": "#FFFFFF",
    },
    "🟡  Amarillo  (Fives)": {
        "bg_top": "#FFE600", "bg_bottom": "#FFE600", "divider": "",
        "intro": "#E91E8C",  "title": "#1A5C1A",
        "tagline": "#E91E8C","badge_bg": "#2A9A2A", "badge_txt": "#FFFFFF",
    },
    "🩷  Rosa": {
        "bg_top": "#E91E8C", "bg_bottom": "#E91E8C", "divider": "",
        "intro": "#FFFFFF",  "title": "#FFE600",
        "tagline": "#FFFFFF","badge_bg": "#FFE600", "badge_txt": "#E91E8C",
    },
    "🔵  Azul oscuro": {
        "bg_top": "#1A3A8C", "bg_bottom": "#1A3A8C", "divider": "",
        "intro": "#FFE600",  "title": "#FFE600",
        "tagline": "#FFFFFF","badge_bg": "#FFE600", "badge_txt": "#1A3A8C",
    },
    "⚫  Negro": {
        "bg_top": "#1A1A1A", "bg_bottom": "#1A1A1A", "divider": "",
        "intro": "#FFE600",  "title": "#FFE600",
        "tagline": "#FFFFFF","badge_bg": "#2A9A2A", "badge_txt": "#FFFFFF",
    },
}

# ── Font ───────────────────────────────────────────────────────────────────────
@st.cache_resource
def load_font():
    FONT_DIR.mkdir(exist_ok=True)
    # Borra archivo corrupto/vacío de intentos previos
    if FONT_PATH.exists() and FONT_PATH.stat().st_size < 1000:
        FONT_PATH.unlink()

    if not FONT_PATH.exists():
        try:
            r = requests.get(FONT_URL, timeout=15)
            r.raise_for_status()
            FONT_PATH.write_bytes(r.content)
        except Exception as e:
            return None, str(e)
    return str(FONT_PATH), None

_font_path, _font_err = load_font()

def fnt(size: int) -> ImageFont.FreeTypeFont:
    if _font_path:
        try:
            return ImageFont.truetype(_font_path, size)
        except Exception:
            pass
    return ImageFont.load_default()

# ── Drawing helpers ────────────────────────────────────────────────────────────
def hex_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rounded_rect(draw, xy, r, fill):
    x1, y1, x2, y2 = xy
    draw.rectangle([x1+r, y1, x2-r, y2], fill=fill)
    draw.rectangle([x1, y1+r, x2, y2-r], fill=fill)
    for cx, cy in [(x1, y1), (x2-2*r, y1), (x1, y2-2*r), (x2-2*r, y2-2*r)]:
        draw.ellipse([cx, cy, cx+2*r, cy+2*r], fill=fill)

def wrap_text(text, f, draw, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textbbox((0, 0), test, font=f)[2] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]

def best_size(text, draw, max_w, max_h, hi=190, lo=45, step=4):
    for sz in range(hi, lo - 1, -step):
        f = fnt(sz)
        lines = wrap_text(text, f, draw, max_w)
        lh = max(draw.textbbox((0,0), l, font=f)[3] for l in lines) + 10
        if lh * len(lines) <= max_h:
            return f, lines
    f = fnt(lo)
    return f, wrap_text(text, f, draw, max_w)

def draw_centered(draw, lines, f, y, fill):
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=f)
        lw, lh = bb[2]-bb[0], bb[3]-bb[1]
        draw.text(((W-lw)//2, y), line, font=f, fill=fill)
        y += lh + 8
    return y

# ── Post generator ─────────────────────────────────────────────────────────────
def generate_post(img, game_name, intro, tagline, split,
                  bg_top, bg_bottom, divider,
                  c_intro, c_title, c_tagline,
                  badge_bg, badge_txt, show_badge, badge_label,
                  remove_bg):

    if img and remove_bg:
        try:
            from rembg import remove as rembg_remove
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            img = Image.open(io.BytesIO(rembg_remove(buf.getvalue()))).convert("RGBA")
        except ImportError:
            st.warning("rembg no está instalado — se saltó la remoción de fondo.")
        except Exception as e:
            st.warning(f"Error al quitar fondo: {e}")

    canvas = Image.new("RGB", (W, H), hex_rgb(bg_top))
    draw = ImageDraw.Draw(canvas)

    if bg_top.upper() != bg_bottom.upper():
        draw.rectangle([(0, split), (W, H)], fill=hex_rgb(bg_bottom))

    if divider:
        sh = 16
        draw.rectangle([(0, split-sh//2), (W, split+sh//2)], fill=hex_rgb(divider))

    if img:
        photo = img.convert("RGBA")
        ar = photo.width / photo.height
        tw, th = W, split
        if ar > tw/th:
            nw, nh = int(th*ar), th
        else:
            nw, nh = tw, int(tw/ar)
        photo = photo.resize((nw, nh), Image.LANCZOS)
        xo, yo = (nw-tw)//2, (nh-th)//2
        photo = photo.crop((xo, yo, xo+tw, yo+th))
        canvas.paste(photo, (0, 0), mask=photo.split()[3])

    draw = ImageDraw.Draw(canvas)
    tw = W - 2*MARGIN
    badge_space = 90 if show_badge else 0
    y = split + 28

    if intro.strip():
        f = fnt(42)
        y = draw_centered(draw, wrap_text(intro, f, draw, tw), f, y, hex_rgb(c_intro))
        y += 8

    if game_name.strip():
        avail = H - y - badge_space - 55
        f, lines = best_size(game_name, draw, tw, avail)
        y = draw_centered(draw, lines, f, y, hex_rgb(c_title))
        y += 14

    if tagline.strip():
        f = fnt(40)
        y = draw_centered(draw, wrap_text(tagline, f, draw, tw), f, y, hex_rgb(c_tagline))

    if show_badge and badge_label.strip():
        f = fnt(44)
        bb = draw.textbbox((0, 0), badge_label, font=f)
        bw = bb[2]-bb[0]+70
        bh = bb[3]-bb[1]+28
        bx = (W-bw)//2
        by = H - bh - 38
        rounded_rect(draw, (bx, by, bx+bw, by+bh), r=20, fill=hex_rgb(badge_bg))
        draw.text((bx+35, by+14), badge_label, font=f, fill=hex_rgb(badge_txt))

    return canvas

# ── UI ─────────────────────────────────────────────────────────────────────────
st.title("🎲 Quantum Post Generator")
st.caption("Generador automático de posts · Quantum Boardgames")

if _font_err:
    st.warning(f"No se pudo cargar fuente Fredoka One: {_font_err}")

left, right = st.columns(2)

# ── COLUMNA IZQUIERDA ──────────────────────────────────────────────────────────
with left:
    st.subheader("Imagen del juego")

    img_input = None
    tab_up, tab_paste = st.tabs(["📁 Subir archivo", "📋 Pegar (Ctrl+V)"])

    with tab_up:
        uploaded = st.file_uploader(
            "img", type=["png","jpg","jpeg","webp"],
            label_visibility="collapsed"
        )
        if uploaded:
            img_input = Image.open(uploaded)

    with tab_paste:
        try:
            from streamlit_paste_button import paste_image_button
            r = paste_image_button("📋 Clic aquí y luego Ctrl+V",
                                   background_color="#1e2130",
                                   hover_background_color="#2a2f45")
            if r and r.image_data:
                img_input = r.image_data
        except ImportError:
            st.info("Instalá `streamlit-paste-button` para pegar imágenes directamente.")

    if img_input:
        st.image(img_input, use_container_width=True)
        remove_bg = st.checkbox("✂️ Quitar fondo automáticamente",
                                help="Primera ejecución descarga ~100 MB de modelo IA.")
    else:
        remove_bg = False
        st.caption("Sin imagen se genera solo con color de fondo.")

    st.divider()
    st.subheader("Textos")
    game_name    = st.text_input("Nombre del juego *",      placeholder="Ej: Ticket to Ride")
    intro_text   = st.text_input("Intro (sobre el título)", placeholder="Ej: Regla #1 de")
    tagline_text = st.text_area( "Tagline (bajo el título)",
                                  placeholder="Ej: Cuantas más rutas, más traición...",
                                  height=85)

    st.divider()
    st.subheader("Colores")
    preset_key = st.selectbox("Preset de color", list(PRESETS.keys()))
    p  = PRESETS[preset_key]
    pk = preset_key  # key suffix — resetea pickers al cambiar preset

    with st.expander("🎨 Personalizar colores"):
        ca, cb = st.columns(2)
        with ca:
            bg_top    = st.color_picker("Fondo superior",  p["bg_top"],    key=f"bgt_{pk}")
            c_title   = st.color_picker("Color título",    p["title"],     key=f"ct_{pk}")
            badge_bg  = st.color_picker("Fondo badge",     p["badge_bg"],  key=f"bb_{pk}")
        with cb:
            bg_bottom = st.color_picker("Fondo inferior",  p["bg_bottom"], key=f"bgb_{pk}")
            c_tagline = st.color_picker("Color tagline",   p["tagline"],   key=f"cta_{pk}")
            badge_txt = st.color_picker("Texto badge",     p["badge_txt"], key=f"bt_{pk}")
        c_intro      = st.color_picker("Color intro",      p["intro"],     key=f"ci_{pk}")
        div_on       = st.checkbox("Franja divisora horizontal",
                                   value=bool(p["divider"]),                key=f"don_{pk}")
        if div_on:
            div_color = st.color_picker("Color franja",
                                        p["divider"] or "#3DB53D",          key=f"dc_{pk}")
        else:
            div_color = ""

    # Si el expander no fue abierto las variables ya tienen los valores del preset
    # (Streamlit sí renderiza widgets colapsados — los valores están disponibles)

    st.divider()
    st.subheader("Opciones")
    oc1, oc2 = st.columns(2)
    with oc1:
        show_badge  = st.checkbox("Mostrar badge",   value=True)
        split_pct   = st.slider("Altura foto (%)",   45, 75, 60)
    with oc2:
        badge_label = st.text_input("Texto badge", value="QUANTUMENDACIÓN")

# ── COLUMNA DERECHA ────────────────────────────────────────────────────────────
with right:
    st.subheader("Previsualización")
    gen = st.button("✨  Generar post", use_container_width=True)

    if gen:
        if not game_name.strip():
            st.warning("Ingresá el nombre del juego.")
        else:
            with st.spinner("Generando post..."):
                post = generate_post(
                    img=img_input,
                    game_name=game_name.strip(),
                    intro=intro_text.strip()   if intro_text   else "",
                    tagline=tagline_text.strip() if tagline_text else "",
                    split=int(H * split_pct / 100),
                    bg_top=bg_top,
                    bg_bottom=bg_bottom,
                    divider=div_color,
                    c_intro=c_intro,
                    c_title=c_title,
                    c_tagline=c_tagline,
                    badge_bg=badge_bg,
                    badge_txt=badge_txt,
                    show_badge=show_badge,
                    badge_label=badge_label,
                    remove_bg=remove_bg,
                )

            st.image(post, use_container_width=True)

            buf = io.BytesIO()
            post.save(buf, format="PNG")
            buf.seek(0)
            st.download_button(
                "⬇️  Descargar PNG (1080×1350)",
                data=buf,
                file_name=f"quantum_{game_name.lower().replace(' ','_')}.png",
                mime="image/png",
                use_container_width=True,
            )
    else:
        st.markdown("""
        <div style='background:#1e2130;border-radius:14px;padding:70px 30px;
                    text-align:center;color:#666;margin-top:10px'>
          <div style='font-size:72px'>🎲</div>
          <div style='font-size:17px;margin-top:14px;line-height:1.6'>
            Completá los campos de la izquierda<br>y presioná
            <strong style='color:#FFE600'>✨ Generar post</strong>
          </div>
        </div>""", unsafe_allow_html=True)
