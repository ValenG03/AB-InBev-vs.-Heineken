import base64
from io import BytesIO
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image, ImageChops

# =========================================================
# CONFIGURACIÓN
# =========================================================
st.set_page_config(
    page_title="AB InBev vs Heineken | Datos oficiales",
    page_icon="🍺",
    layout="wide",
)

ABI = "#FFD60A"   # amarillo neón AB InBev
HEI = "#39FF6A"   # verde neón Heineken
BG = "#07080A"
CARD = "#111318"
BORDER = "#23262E"
TEXT = "#F2F2F2"
MUTED = "#8A8F98"

PERIODOS = ["2025", "1S 2026", "2025 + 1S 2026"]

# Tipo de cambio promedio EUR/USD (referencia diaria del Banco Central Europeo)
FX = {"2025": 1.1300, "1S 2026": 1.1666}

# =========================================================
# DATOS OFICIALES (comunicados de resultados de cada compañía)
# AB InBev en millones de USD · Heineken en millones de EUR · Volumen en millones de hl
# ingresos      -> ABI: Revenue | HEI: Net revenue (IFRS). Ambos netos de impuestos especiales
# op            -> Ganancia operativa: ABI Normalized EBIT | HEI Operating profit (beia)
# base_margen   -> Base del margen operativo: ABI Revenue | HEI Net revenue (beia)
# neto          -> ABI Underlying Profit | HEI Net profit (beia)
# mkt           -> ABI inversión en sales & marketing | HEI Marketing and selling expenses
# vol           -> ABI Total volumes | HEI Total volume
# =========================================================
BASE = {
    "AB InBev": {
        "2025":    {"ingresos": 59320, "op": 15854, "base_margen": 59320, "neto": 7410, "mkt": 7400, "vol": 561.1},
        "1S 2026": {"ingresos": 31927, "op": 8677,  "base_margen": 31927, "neto": 4314, "mkt": 4100, "vol": 280.4},
    },
    "Heineken": {
        "2025":    {"ingresos": 28753, "op": 4385, "base_margen": 28890, "neto": 2662, "mkt": 2855, "vol": 281.6},
        "1S 2026": {"ingresos": 14841, "op": 2170, "base_margen": 14834, "neto": 1256, "mkt": 1492, "vol": 142.8},
    },
}
MONEDA = {"AB InBev": "USD", "Heineken": "EUR"}
COLOR = {"AB InBev": ABI, "Heineken": HEI}
MONETARIOS = ["ingresos", "op", "base_margen", "neto", "mkt"]

AB_EMPRESAS = [
    ("Anheuser-Busch", "Estados Unidos", "Budweiser, Bud Light, Michelob Ultra, Busch"),
    ("Grupo Modelo", "México", "Corona, Modelo Especial, Pacifico, Victoria"),
    ("Ambev", "Brasil y Sudamérica (incluye Quilmes, Argentina)", "Brahma, Skol, Antarctica, Quilmes"),
    ("Budweiser APAC", "China, Corea del Sur e India", "Harbin, Cass, Budweiser China"),
    ("SAB (South African Breweries)", "Sudáfrica y África", "Castle, Castle Lite, Carling Black Label"),
]

# =========================================================
# ESTILO
# =========================================================
st.markdown(f"""
<style>
    .stApp {{ background-color: {BG}; color: {TEXT}; }}
    [data-testid="stSidebar"] {{ background-color: #0D0F13; border-right: 1px solid {BORDER}; }}
    [data-testid="stHeader"] {{ background: transparent; }}
    h1, h2, h3, h4, p, span, label, li {{ color: {TEXT}; }}
    .block-container {{ padding-top: 2rem; max-width: 1400px; }}
    .titulo {{ font-size: 2.6rem; font-weight: 800; letter-spacing: -1px; margin-bottom: 0; }}
    .sub {{ color: {MUTED}; font-size: 1rem; margin-top: 4px; }}
    .card {{
        background: {CARD}; border: 1px solid {BORDER}; border-radius: 14px;
        padding: 18px 20px; height: 100%;
    }}
    .card-label {{ color: {MUTED}; font-size: .78rem; text-transform: uppercase; letter-spacing: 1px; }}
    .card-value {{ font-size: clamp(1.1rem, 1.6vw, 1.75rem); white-space: nowrap; font-weight: 800; margin-top: 6px; }}
    .card-delta {{ font-size: .85rem; margin-top: 4px; color: {MUTED}; }}
    .tag {{
        display: inline-block; padding: 3px 12px; border-radius: 20px;
        font-weight: 700; font-size: .85rem; margin-bottom: 10px; color: #000;
    }}
    .seccion {{ font-size: 1.35rem; font-weight: 700; margin: 30px 0 6px 0;
               border-left: 4px solid {ABI}; padding-left: 10px; }}
    .nota {{ color: {MUTED}; font-size: .8rem; }}
    .logos {{
        display: flex; align-items: center; justify-content: center; gap: 28px;
        flex-wrap: wrap; margin: 4px 0 26px 0;
    }}
    .logo-box {{
        background: {CARD}; border: 1px solid {BORDER}; border-radius: 16px;
        height: 132px; width: 340px; padding: 0 24px;
        display: flex; align-items: center; justify-content: center;
    }}
    .logo-vs {{ font-size: 1.6rem; font-weight: 800; color: {MUTED}; letter-spacing: 2px; }}
    @media (max-width: 700px) {{
        .logo-box {{ width: 100%; }}
        .logo-vs {{ width: 100%; text-align: center; }}
    }}
    div[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 10px; }}
</style>
""", unsafe_allow_html=True)


# =========================================================
# FUNCIONES
# =========================================================
def datos(empresa, periodo, a_usd=False):
    """Devuelve los datos de un período. La suma 2025 + 1S 2026 se calcula sumando ambos períodos."""
    partes = ["2025", "1S 2026"] if periodo == "2025 + 1S 2026" else [periodo]
    out = {k: 0.0 for k in BASE[empresa]["2025"]}
    for per in partes:
        fx = FX[per] if (a_usd and empresa == "Heineken") else 1
        for k, v in BASE[empresa][per].items():
            out[k] += v * fx if k in MONETARIOS else v
    out["margen"] = out["op"] / out["base_margen"] * 100
    out["pct_mkt"] = out["mkt"] / out["ingresos"] * 100
    out["pct_neto"] = out["neto"] / out["ingresos"] * 100
    return out


def fmt_money(v, moneda):
    simbolo = "US$" if moneda == "USD" else "€"
    return f"{simbolo} {v/1000:,.1f} B" if v >= 1000 else f"{simbolo} {v:,.0f} M"


def card(label, valor, detalle, color):
    st.markdown(f"""
    <div class='card' style='border-top:3px solid {color}'>
        <div class='card-label'>{label}</div>
        <div class='card-value' style='color:{color}'>{valor}</div>
        <div class='card-delta'>{detalle}</div>
    </div>""", unsafe_allow_html=True)


def layout_fig(fig, titulo, ysuffix=""):
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=16, color=TEXT)),
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        font=dict(color=TEXT, family="Inter, sans-serif"),
        legend=dict(orientation="h", y=1.12, x=0, bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT)),
        margin=dict(l=20, r=20, t=70, b=20), height=380,
        hovermode="x unified", barmode="group", bargap=0.3,
    )
    fig.update_xaxes(showgrid=False, linecolor=BORDER, type="category")
    fig.update_yaxes(gridcolor=BORDER, zeroline=False, ticksuffix=ysuffix)
    return fig


def barras(clave, titulo, sufijo="", decimales=0, convertir=True):
    fig = go.Figure()
    for emp in ["AB InBev", "Heineken"]:
        a_usd = convertir and moneda_vista == "USD"
        valores = [datos(emp, per, a_usd)[clave] for per in PERIODOS]
        fig.add_bar(
            x=PERIODOS, y=valores, name=emp, marker_color=COLOR[emp],
            text=[f"{v:,.{decimales}f}{sufijo}" for v in valores],
            textposition="outside", textfont=dict(color=TEXT, size=11),
        )
    return layout_fig(fig, titulo, sufijo)


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown("### ⚙️ Controles")
    periodo = st.radio("Período de las tarjetas", PERIODOS, index=2)
    moneda_vista = st.radio(
        "Moneda de Heineken en los gráficos",
        ["USD", "EUR"],
        help="AB InBev reporta en USD y Heineken en EUR. En 'USD' se convierte Heineken "
             "con el tipo de cambio promedio del BCE de cada período.",
    )
    st.markdown("---")
    st.markdown("**Tipo de cambio EUR/USD (promedio BCE)**")
    for a, v in FX.items():
        st.markdown(f"<span class='nota'>{a}: {v}</span>", unsafe_allow_html=True)
    st.markdown("<span class='nota'>2025 + 1S 2026 = 18 meses (enero 2025 a junio 2026).</span>",
                unsafe_allow_html=True)

# =========================================================
# LOGOS (archivos en la raíz del repo, junto a app.py)
# =========================================================
LOGO_ABI = "ABinveb.png"
LOGO_HEI = "heineken_beer-logo-brandlogos.net_.png"


@st.cache_data
def logo_b64(archivo):
    """Recorta el logo a su contenido, quita el fondo y lo devuelve en base64."""
    ruta = Path(__file__).parent / archivo
    if not ruta.exists():
        return None
    img = Image.open(ruta).convert("RGBA")
    if img.getchannel("A").getextrema()[0] == 255:   # sin transparencia: quitar el fondo liso
        rgb = img.convert("RGB")
        fondo = Image.new("RGB", rgb.size, rgb.getpixel((2, 2)))
        dif = ImageChops.difference(rgb, fondo).convert("L")
        img.putalpha(dif.point(lambda p: min(255, int(p * 1.6))))
    caja = img.getbbox()
    if caja:
        img = img.crop(caja)
    img.thumbnail((600, 400))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def logo_html(archivo, alt, alto):
    b64 = logo_b64(archivo)
    if b64 is None:
        return f"<span style='font-weight:800;font-size:1.4rem'>{alt}</span>"
    return (f"<img src='data:image/png;base64,{b64}' alt='{alt}' "
            f"style='max-height:{alto}px;max-width:100%;width:auto;display:block'>")


st.markdown(f"""
<div class='logos'>
    <div class='logo-box' style='border-top:3px solid {ABI}'>{logo_html(LOGO_ABI, "AB InBev", 60)}</div>
    <div class='logo-vs'>VS</div>
    <div class='logo-box' style='border-top:3px solid {HEI}'>{logo_html(LOGO_HEI, "Heineken", 112)}</div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# HEADER
# =========================================================
st.markdown("<div class='titulo'>🍺 AB InBev <span style='color:#FFD60A'>vs</span> Heineken</div>",
            unsafe_allow_html=True)
st.markdown("<div class='sub'>Los dos mayores cerveceros del mundo · Períodos analizados: 2025 · "
            "1er semestre 2026 · Acumulado 2025 + 1S 2026 · Datos oficiales de los reportes de resultados</div>",
            unsafe_allow_html=True)
st.write("")

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"<span class='tag' style='background:{ABI}'>AB InBev · #1 mundial</span>",
                unsafe_allow_html=True)
    st.markdown("<span class='nota'>Lovaina, Bélgica · +400 marcas · ~137.000 empleados · "
                "Reporta en USD</span>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<span class='tag' style='background:{HEI}'>Heineken · #2 mundial</span>",
                unsafe_allow_html=True)
    st.markdown("<span class='nota'>Ámsterdam, Países Bajos · +340 marcas · +85.000 empleados · "
                "Reporta en EUR</span>", unsafe_allow_html=True)

# =========================================================
# TARJETAS (5 PARÁMETROS)
# =========================================================
st.markdown(f"<div class='seccion'>Indicadores clave · {periodo}</div>", unsafe_allow_html=True)
vol_total = sum(datos(e, periodo)["vol"] for e in BASE)

for emp in ["AB InBev", "Heineken"]:
    d = datos(emp, periodo)
    color, moneda = COLOR[emp], MONEDA[emp]
    st.markdown(f"<span style='color:{color};font-weight:700'>{emp}</span>", unsafe_allow_html=True)
    cols = st.columns(5)
    with cols[0]:
        por_hl = d["ingresos"] * 1e6 / (d["vol"] * 1e6)
        simb = "US$" if moneda == "USD" else "€"
        card("Ingresos", fmt_money(d["ingresos"], moneda), f"{simb} {por_hl:,.0f} por hectolitro", color)
    with cols[1]:
        card("Margen operativo", f"{d['margen']:.1f}%",
             f"Ganancia operativa {fmt_money(d['op'], moneda)}", color)
    with cols[2]:
        card("Beneficio neto ajustado", fmt_money(d["neto"], moneda),
             f"{d['pct_neto']:.1f}% de los ingresos", color)
    with cols[3]:
        card("Volumen", f"{d['vol']:,.1f} M hl",
             f"{d['vol'] / vol_total * 100:.0f}% del volumen de ambas", color)
    with cols[4]:
        card("Ventas y marketing", fmt_money(d["mkt"], moneda),
             f"{d['pct_mkt']:.1f}% de los ingresos", color)
    st.write("")

# =========================================================
# GRÁFICOS
# =========================================================
st.markdown("<div class='seccion'>Comparación por período</div>", unsafe_allow_html=True)
suf = "M US$" if moneda_vista == "USD" else "M · AB InBev en US$ · Heineken en €"

g1, g2 = st.columns(2)
with g1:
    st.plotly_chart(barras("ingresos", f"1 · Ingresos ({suf})"), width="stretch")
with g2:
    st.plotly_chart(barras("margen", "2 · Margen operativo (%)", "%", 1, convertir=False), width="stretch")

g3, g4 = st.columns(2)
with g3:
    st.plotly_chart(barras("neto", f"3 · Beneficio neto ajustado ({suf})"), width="stretch")
with g4:
    st.plotly_chart(barras("vol", "4 · Volumen total (millones de hl)", "", 1, convertir=False),
                    width="stretch")

g5, g6 = st.columns(2)
with g5:
    st.plotly_chart(barras("mkt", f"5 · Inversión en ventas y marketing ({suf})"), width="stretch")
with g6:
    st.plotly_chart(barras("pct_mkt", "Ventas y marketing como % de los ingresos", "%", 1, convertir=False),
                    width="stretch")

st.markdown("<p class='nota'>El acumulado 2025 + 1S 2026 suma 18 meses de resultados. Los márgenes "
            "y porcentajes del acumulado se recalculan sobre los totales sumados.</p>",
            unsafe_allow_html=True)

# =========================================================
# QUIÉN ES AB INBEV
# =========================================================
st.markdown("<div class='seccion'>¿Qué empresas conforman AB InBev? (principales 5)</div>",
            unsafe_allow_html=True)
ec = st.columns(5)
for col, (nombre, region, marcas) in zip(ec, AB_EMPRESAS):
    with col:
        st.markdown(f"""
        <div class='card' style='border-top:3px solid {ABI}'>
            <div style='font-weight:800;color:{ABI};font-size:1.05rem'>{nombre}</div>
            <div class='nota' style='margin:6px 0'>{region}</div>
            <div style='font-size:.85rem'>{marcas}</div>
        </div>""", unsafe_allow_html=True)
st.markdown("<p class='nota'>AB InBev es la casa matriz que consolida estas compañías. Se comparan "
            "los resultados consolidados de las dos corporaciones madre (AB InBev y Heineken N.V.).</p>",
            unsafe_allow_html=True)

# =========================================================
# TABLA
# =========================================================
st.markdown("<div class='seccion'>Tabla de datos</div>", unsafe_allow_html=True)
filas = ["Ingresos (M)", "Ganancia operativa (M)", "Margen operativo (%)",
         "Beneficio neto ajustado (M)", "Ventas y marketing (M)", "Volumen (M hl)"]
tabla = pd.DataFrame({"Indicador": filas})
for emp, simb in [("AB InBev", "US$"), ("Heineken", "€")]:
    for per in PERIODOS:
        d = datos(emp, per)
        tabla[f"{emp} · {per} ({simb})"] = [
            round(d["ingresos"]), round(d["op"]), round(d["margen"], 1),
            round(d["neto"]), round(d["mkt"]), round(d["vol"], 1),
        ]
st.dataframe(tabla.set_index("Indicador"), width="stretch")

# =========================================================
# NOTAS Y FUENTES
# =========================================================
with st.expander("📌 Notas metodológicas y fuentes"):
    st.markdown("""
- **Períodos:** año 2025 completo, primer semestre 2026 (enero a junio) y el acumulado de ambos (18 meses).
- **Ingresos:** AB InBev *Revenue* (ya neto de impuestos especiales) y Heineken *Net revenue* (IFRS, neto de impuestos especiales), para que sean comparables.
- **Margen operativo:** AB InBev *Normalized EBIT* sobre *Revenue*. Heineken *Operating profit (beia)* sobre *Net revenue (beia)*. Ambos excluyen partidas extraordinarias.
- **Beneficio neto ajustado:** AB InBev *Underlying Profit*; Heineken *Net profit (beia)*.
- **Ventas y marketing:** AB InBev informa su inversión total en *sales and marketing* (US$ 7,4 B en 2025 y US$ 4,1 B en 1S 2026). Heineken: *Marketing and selling expenses* (IFRS).
- **Volumen:** AB InBev *Total volumes* (cerveza + no cerveza, propios). Heineken *Total volume* (incluye volumen licenciado).
- **Conversión:** Heineken en USD con el tipo de cambio promedio EUR/USD del BCE de cada período (2025: 1,1300 · 1S 2026: 1,1666, promedio de las cotizaciones diarias de enero a junio).
- **Fuentes:** AB InBev – comunicados de resultados FY2025 y 2Q/HY2026 (ab-inbev.com / SEC Form 6-K). Heineken N.V. – comunicados FY2025 y HY2026 (theheinekencompany.com). Tipo de cambio: Banco Central Europeo.
""")

st.markdown("<p class='nota' style='text-align:center;margin-top:30px'>Dashboard comparativo · "
            "AB InBev vs Heineken · 2025, 1S 2026 y acumulado</p>", unsafe_allow_html=True)
