import streamlit as st
import pandas as pd
import plotly.graph_objects as go

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

# Tipo de cambio promedio anual EUR/USD (Banco Central Europeo)
FX = {"2023": 1.0813, "2024": 1.0824, "2025": 1.1300}

# =========================================================
# DATOS OFICIALES (comunicados de resultados de cada compañía)
# AB InBev: millones USD | Heineken: millones EUR | Volumen: millones hl
# =========================================================
ANUAL = pd.DataFrame({
    "Año": ["2023", "2024", "2025"],
    # Ingresos (netos de impuestos especiales)
    "ABI_ingresos": [59380, 59768, 59320],
    "HEI_ingresos": [30362, 29821, 28753],
    # EBITDA normalizado (ABI) / EBITDA beia (Heineken)
    "ABI_ebitda": [19976, 20958, 21223],
    "HEI_ebitda": [6541, 6685, 6560],
    # Margen EBITDA (%)
    "ABI_margen": [33.6, 35.1, 35.8],
    "HEI_margen": [21.6, 22.3, 22.7],
    # Beneficio neto ajustado: Underlying Profit (ABI) / Net profit beia (Heineken)
    "ABI_neto": [6158, 7061, 7410],
    "HEI_neto": [2632, 2739, 2662],
    # Inversión en ventas y marketing
    "ABI_mkt": [7200, 7200, 7400],
    "HEI_mkt": [2767, 2940, 2855],
    # Volumen total (millones de hectolitros)
    "ABI_vol": [None, 575.7, 561.1],
    "HEI_vol": [None, 286.2, 281.6],
})

SEMESTRE = {
    "AB InBev": {
        "moneda": "USD",
        "Ingresos": (28632, 31927),
        "EBITDA": (10156, 11375),
        "Beneficio neto ajustado": (3556, 4314),
        "Volumen (M hl)": (279.6, 280.4),
        "Marketing": (None, 4100),
    },
    "Heineken": {
        "moneda": "EUR",
        "Ingresos": (14180, 14841),
        "EBITDA": (3088, 3295),
        "Beneficio neto ajustado": (1164, 1256),
        "Volumen (M hl)": (138.6, 142.8),
        "Marketing": (1444, 1492),
    },
}

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
    .card-delta {{ font-size: .85rem; margin-top: 4px; }}
    .pos {{ color: {HEI}; }}
    .neg {{ color: #FF4D6D; }}
    .tag {{
        display: inline-block; padding: 3px 12px; border-radius: 20px;
        font-weight: 700; font-size: .85rem; margin-bottom: 10px; color: #000;
    }}
    .seccion {{ font-size: 1.35rem; font-weight: 700; margin: 30px 0 6px 0;
               border-left: 4px solid {ABI}; padding-left: 10px; }}
    .nota {{ color: {MUTED}; font-size: .8rem; }}
    div[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 10px; }}
</style>
""", unsafe_allow_html=True)


# =========================================================
# FUNCIONES
# =========================================================
def fmt_money(v, moneda):
    simbolo = "US$" if moneda == "USD" else "€"
    return f"{simbolo} {v/1000:,.1f} B" if v >= 1000 else f"{simbolo} {v:,.0f} M"


def delta_html(actual, previo):
    if actual is None or previo in (None, 0):
        return "<div class='card-delta' style='color:#8A8F98'>—</div>"
    d = (actual - previo) / previo * 100
    clase = "pos" if d >= 0 else "neg"
    flecha = "▲" if d >= 0 else "▼"
    return f"<div class='card-delta {clase}'>{flecha} {d:+.1f}% vs anterior</div>"


def card(label, valor, delta, color):
    st.markdown(f"""
    <div class='card' style='border-top:3px solid {color}'>
        <div class='card-label'>{label}</div>
        <div class='card-value' style='color:{color}'>{valor}</div>
        {delta}
    </div>""", unsafe_allow_html=True)


def layout_fig(fig, titulo, ysuffix=""):
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=16, color=TEXT)),
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        font=dict(color=TEXT, family="Inter, sans-serif"),
        legend=dict(orientation="h", y=1.12, x=0, bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT)),
        margin=dict(l=20, r=20, t=70, b=20), height=380,
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor=BORDER, type="category")
    fig.update_yaxes(gridcolor=BORDER, zeroline=False, ticksuffix=ysuffix)
    return fig


def barras(col, titulo, sufijo, convertir=True, decimales=0):
    df = ANUAL.copy()
    hei = df[f"HEI_{col}"]
    if convertir and moneda_vista == "USD":
        hei = [v * FX[a] if v is not None else None for v, a in zip(hei, df["Año"])]
    fig = go.Figure()
    for nombre, valores, color in [("AB InBev", df[f"ABI_{col}"], ABI), ("Heineken", hei, HEI)]:
        fig.add_bar(
            x=df["Año"], y=valores, name=nombre, marker_color=color,
            text=[f"{v:,.{decimales}f}" if pd.notna(v) else "" for v in valores],
            textposition="outside", textfont=dict(color=TEXT, size=11),
        )
    fig.update_layout(barmode="group", bargap=0.3)
    return layout_fig(fig, titulo, sufijo)


def lineas(col, titulo, sufijo="%"):
    fig = go.Figure()
    for nombre, color in [("AB InBev", ABI), ("Heineken", HEI)]:
        fig.add_scatter(
            x=ANUAL["Año"], y=ANUAL[f"{'ABI' if nombre == 'AB InBev' else 'HEI'}_{col}"],
            name=nombre, mode="lines+markers+text", line=dict(color=color, width=4),
            marker=dict(size=11), text=[f"{v:.1f}%" for v in ANUAL[f"{'ABI' if nombre == 'AB InBev' else 'HEI'}_{col}"]],
            textposition="top center", textfont=dict(color=color),
        )
    return layout_fig(fig, titulo, sufijo)


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown("### ⚙️ Controles")
    moneda_vista = st.radio(
        "Moneda de Heineken en los gráficos",
        ["USD", "EUR"],
        help="AB InBev reporta en USD y Heineken en EUR. En 'USD' se convierte Heineken "
             "con el tipo de cambio promedio anual del BCE.",
    )
    anio = st.selectbox("Año para las tarjetas", ["2025", "2024", "2023"])
    st.markdown("---")
    st.markdown("**Tipo de cambio EUR/USD (prom. anual BCE)**")
    for a, v in FX.items():
        st.markdown(f"<span class='nota'>{a}: {v}</span>", unsafe_allow_html=True)

# =========================================================
# HEADER
# =========================================================
st.markdown("<div class='titulo'>🍺 AB InBev <span style='color:#FFD60A'>vs</span> Heineken</div>",
            unsafe_allow_html=True)
st.markdown("<div class='sub'>Los dos mayores cerveceros del mundo · Análisis temporal 2023 – 2025 "
            "y primer semestre 2026 · Datos oficiales de los reportes de resultados</div>",
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
st.markdown(f"<div class='seccion'>Indicadores clave · {anio}</div>", unsafe_allow_html=True)
i = ANUAL.index[ANUAL["Año"] == anio][0]
p = i - 1 if i > 0 else None


def prev(col):
    return ANUAL.loc[p, col] if p is not None else None


for emp, pref, color, moneda in [("AB InBev", "ABI", ABI, "USD"), ("Heineken", "HEI", HEI, "EUR")]:
    st.markdown(f"<span style='color:{color};font-weight:700'>{emp}</span>", unsafe_allow_html=True)
    cols = st.columns(5)
    with cols[0]:
        card("Ingresos", fmt_money(ANUAL.loc[i, f"{pref}_ingresos"], moneda),
             delta_html(ANUAL.loc[i, f"{pref}_ingresos"], prev(f"{pref}_ingresos")), color)
    with cols[1]:
        card("EBITDA", fmt_money(ANUAL.loc[i, f"{pref}_ebitda"], moneda),
             f"<div class='card-delta' style='color:#8A8F98'>Margen {ANUAL.loc[i, f'{pref}_margen']:.1f}%</div>",
             color)
    with cols[2]:
        card("Beneficio neto ajustado", fmt_money(ANUAL.loc[i, f"{pref}_neto"], moneda),
             delta_html(ANUAL.loc[i, f"{pref}_neto"], prev(f"{pref}_neto")), color)
    with cols[3]:
        v = ANUAL.loc[i, f"{pref}_vol"]
        card("Volumen", f"{v:,.1f} M hl" if pd.notna(v) else "s/d",
             delta_html(v if pd.notna(v) else None,
                        prev(f"{pref}_vol") if p is not None and pd.notna(prev(f"{pref}_vol")) else None),
             color)
    with cols[4]:
        mkt = ANUAL.loc[i, f"{pref}_mkt"]
        pct = mkt / ANUAL.loc[i, f"{pref}_ingresos"] * 100
        card("Ventas y marketing", fmt_money(mkt, moneda),
             f"<div class='card-delta' style='color:#8A8F98'>{pct:.1f}% de los ingresos</div>", color)
    st.write("")

# =========================================================
# GRÁFICOS
# =========================================================
st.markdown("<div class='seccion'>Evolución 2023 – 2025</div>", unsafe_allow_html=True)
suf = "M US$" if moneda_vista == "USD" else "M (ABI en US$ · HEI en €)"

g1, g2 = st.columns(2)
with g1:
    st.plotly_chart(barras("ingresos", f"1 · Ingresos ({suf})", ""), width="stretch")
with g2:
    st.plotly_chart(lineas("margen", "2 · Margen EBITDA (%)"), width="stretch")

g3, g4 = st.columns(2)
with g3:
    st.plotly_chart(barras("neto", f"3 · Beneficio neto ajustado ({suf})", ""), width="stretch")
with g4:
    st.plotly_chart(barras("vol", "4 · Volumen total (millones de hl)", "", convertir=False, decimales=1),
                    width="stretch")

g5, g6 = st.columns(2)
with g5:
    st.plotly_chart(barras("mkt", f"5 · Inversión en ventas y marketing ({suf})", ""), width="stretch")
with g6:
    share = go.Figure()
    for nombre, pref, color in [("AB InBev", "ABI", ABI), ("Heineken", "HEI", HEI)]:
        pct = ANUAL[f"{pref}_mkt"] / ANUAL[f"{pref}_ingresos"] * 100
        share.add_scatter(x=ANUAL["Año"], y=pct, name=nombre, mode="lines+markers+text",
                          line=dict(color=color, width=4, dash="dot"), marker=dict(size=11),
                          text=[f"{v:.1f}%" for v in pct], textposition="top center",
                          textfont=dict(color=color))
    st.plotly_chart(layout_fig(share, "Marketing como % de los ingresos", "%"), width="stretch")

# =========================================================
# ÚLTIMO SEMESTRE
# =========================================================
st.markdown("<div class='seccion'>Último dato: 1er semestre 2026 vs 1er semestre 2025</div>",
            unsafe_allow_html=True)
s1, s2 = st.columns(2)
for col, emp, color in [(s1, "AB InBev", ABI), (s2, "Heineken", HEI)]:
    with col:
        d = SEMESTRE[emp]
        st.markdown(f"<span style='color:{color};font-weight:700'>{emp} · 1S 2026</span>",
                    unsafe_allow_html=True)
        cc = st.columns(3)
        items = ["Ingresos", "EBITDA", "Beneficio neto ajustado"]
        for k, item in enumerate(items):
            prev_v, act = d[item]
            with cc[k]:
                card(item, fmt_money(act, d["moneda"]), delta_html(act, prev_v), color)
        st.write("")
        cc2 = st.columns(2)
        with cc2[0]:
            pv, av = d["Volumen (M hl)"]
            card("Volumen", f"{av:,.1f} M hl", delta_html(av, pv), color)
        with cc2[1]:
            pv, av = d["Marketing"]
            extra = delta_html(av, pv) if pv else "<div class='card-delta pos'>▲ +9% vs 1S 2025 (dato oficial)</div>"
            card("Ventas y marketing", fmt_money(av, d["moneda"]), extra, color)

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
tabla = pd.DataFrame({
    "Indicador": ["Ingresos (M)", "EBITDA (M)", "Margen EBITDA (%)", "Beneficio neto ajustado (M)",
                  "Ventas y marketing (M)", "Volumen (M hl)"],
})
for _, r in ANUAL.iterrows():
    a = r["Año"]
    tabla[f"AB InBev {a} (US$)"] = [r.ABI_ingresos, r.ABI_ebitda, r.ABI_margen, r.ABI_neto, r.ABI_mkt, r.ABI_vol]
    tabla[f"Heineken {a} (€)"] = [r.HEI_ingresos, r.HEI_ebitda, r.HEI_margen, r.HEI_neto, r.HEI_mkt, r.HEI_vol]
st.dataframe(tabla.set_index("Indicador"), width="stretch")

# =========================================================
# NOTAS Y FUENTES
# =========================================================
with st.expander("📌 Notas metodológicas y fuentes"):
    st.markdown("""
- **Ingresos:** AB InBev *Revenue* (ya neto de impuestos especiales) y Heineken *Net revenue* (IFRS, neto de impuestos especiales), para que sean comparables.
- **EBITDA:** AB InBev *Normalized EBITDA*; Heineken *EBITDA (beia)*. El margen de Heineken se calcula sobre *Net revenue (beia)*.
- **Beneficio neto ajustado:** AB InBev *Underlying Profit*; Heineken *Net profit (beia)*. Ambos excluyen partidas extraordinarias.
- **Ventas y marketing:** AB InBev informa la inversión total en *sales and marketing* (US$ 7,2 B en 2023 y 2024, US$ 7,4 B en 2025, US$ 4,1 B en 1S 2026). Heineken: *Marketing and selling expenses* (IFRS).
- **Volumen:** AB InBev *Total volumes* (cerveza + no cerveza, propios). Heineken *Total volume* (incluye volumen licenciado). Volumen 2023 no incluido por cambio de criterio de reporte de Heineken.
- **Conversión:** Heineken en USD con tipo de cambio promedio anual EUR/USD del BCE. Los datos semestrales se muestran en moneda original.
- **Fuentes:** AB InBev – comunicados de resultados FY2023, FY2024, FY2025 y 2Q/HY2026 (ab-inbev.com / SEC Form 6-K). Heineken N.V. – comunicados FY2024, FY2025 y HY2026 (theheinekencompany.com). Tipo de cambio: Banco Central Europeo.
""")

st.markdown(f"<p class='nota' style='text-align:center;margin-top:30px'>Dashboard comparativo · "
            f"AB InBev vs Heineken · Datos al 1er semestre 2026</p>", unsafe_allow_html=True)
