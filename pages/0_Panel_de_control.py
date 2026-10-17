import html as html_lib

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import sheets_io
import style

st.set_page_config(page_title="Panel de control", layout="wide")

EMPRESA_PROPIA = "LAST1"

# ------------------------------------------------------------------
# Secciones / subsecciones del Excel (tal como las deja parser.py)
# ------------------------------------------------------------------
SECCION_RATIOS = "Ratios e indicadores financieros clave"
SUB_RATIOS = "Ratios"
SUB_INDICADORES = "Indicadores Financieros Claves, %"
SECCION_EERR = "Cuenta de resultados, miles USD, Global"
SECCION_BALANCE = "Hoja de Balance, miles USD, Global"
SECCION_VALUACION = "Valuación - Global"
SUB_DCF = "Valoración flujos de fondos descontados"
REGIONES = ["EE.UU.", "Asia", "Europa"]
TECS = ["Tec 1", "Tec 2", "Tec 3", "Tec 4"]

COLOR_INGRESO = "#1DB954"
COLOR_COSTO = "#E3342F"
COLOR_EBITDA = "#2F6FED"

# Costos que van del Ingreso al EBITDA (mismo orden que en Estados financieros).
# (nombre real en los datos, etiqueta corta para el eje X)
COSTOS_EBITDA = [
    ("Costos de fabricación interna", "Fab.<br>interna"),
    ("Costos de características", "Caract."),
    ("Costos de fabricación contratada", "Fab.<br>contrat."),
    ("Costos de transporte y aranceles", "Transp. y<br>aranceles"),
    ("I+D", "I+D"),
    ("Promoción", "Promoc."),
    ("Administración", "Admin."),
]

# (nombre real en los datos, etiqueta corta, color)
COMPONENTES_ACTIVO = [
    ("Activo fijo", "Activo fijo", "#1F3B57", "white"),
    ("Inventario", "Inventario", "#3FA7A0", "white"),
    ("Cuentas por Cobrar", "Ctas. cobrar", "#8BC34A", "#1B2A3A"),
    ("Efectivo y equivalentes de efectivo", "Efectivo", "#4CAF50", "white"),
]
COMPONENTES_PPN = [
    ("Total patrimonio neto", "Patrimonio neto", "#2F6FED", "white"),
    ("Deudas a largo plazo", "Deuda LP", "#FF9800", "#1B2A3A"),
    ("Deudas a corto plazo (no planificadas)", "Deuda CP", "#E53935", "white"),
    ("Cuentas por pagar", "Ctas. pagar", "#FFC107", "#1B2A3A"),
]

# Alto de los gráficos del cuadro central. Por defecto lo define el navegador con CSS:
# alto de la ventana (100vh) - ALTO_FIJO_PX, que es todo lo que NO son gráficos (logo/título,
# filas de tarjetas y separaciones). Así se adapta solo a cualquier pantalla, incluso si
# cambiás el tamaño de la ventana. Si algún día aparece scroll, subí ALTO_FIJO_PX unos px.
# El ⚙️ permite fijar un alto manual en px.
ALTO_GRAFICOS_DEFAULT = 460  # solo para el modo manual
ALTO_FIJO_PX = 290
ALTO_MIN, ALTO_MAX = 280, 900
ALTO_TARJETA = 72

# ------------------------------------------------------------------
# CSS: compacta la página para que entre en una pantalla + estilo de tarjetas
# ------------------------------------------------------------------
CSS_PANEL = f"""
<style>
header[data-testid="stHeader"] {{ height: 2.2rem; background: transparent; }}
div.block-container, div[data-testid="stMainBlockContainer"] {{
    padding: 2.4rem 1.2rem 0.4rem 1.2rem; max-width: 100%;
}}
[data-testid="stMain"] [data-testid="stVerticalBlock"] {{ gap: 0.5rem; }}
[data-testid="stMain"] [data-testid="stHorizontalBlock"] {{ gap: 10px; }}
:root {{ --alto-g: ALTO_G_VALOR; }}
/* Streamlit envuelve cada gráfico en un contenedor con alto propio: hay que fijarlo ahí (clase st-key-NOMBRE). */
.st-key-fig_ebitda, .st-key-fig_estructura {{ height: var(--alto-g) !important; flex: 0 0 var(--alto-g) !important; }}
/* La torta ocupa el alto de los gráficos + la fila de tarjetas de abajo + una separación */
.st-key-fig_market_share {{ height: calc(var(--alto-g) + {ALTO_TARJETA + 8}px) !important; flex: 0 0 calc(var(--alto-g) + {ALTO_TARJETA + 8}px) !important; }}
div[data-testid="stPlotlyChart"] {{
    height: 100% !important;
    border: 1px solid #cfd3d6; border-radius: 8px; overflow: hidden; background: white;
}}
div[data-testid="stPlotlyChart"] > div, div[data-testid="stPlotlyChart"] .js-plotly-plot,
div[data-testid="stPlotlyChart"] .plot-container, div[data-testid="stPlotlyChart"] .svg-container {{ height: 100% !important; }}
.kpi-grid {{ display: grid; gap: 10px; margin-bottom: 16px; }}
.kpi-grid.g5 {{ grid-template-columns: repeat(5, 1fr); }}
.kpi-grid.g3 {{ grid-template-columns: repeat(3, 1fr); }}
.kpi {{
    position: relative; background: white; border: 1px solid #cfd3d6; border-left: 4px solid {style.COLOR_AZUL};
    border-radius: 8px; padding: 6px 12px; height: {ALTO_TARJETA}px; box-sizing: border-box;
    display: flex; flex-direction: column; justify-content: center; cursor: default;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}
.kpi .k-et {{ font-size: 0.72rem; color: #5b6773; text-transform: uppercase; letter-spacing: 0.03em; line-height: 1.15; }}
.kpi .k-val {{ font-size: 1.6rem; font-weight: 700; color: {style.COLOR_TEXTO}; line-height: 1.25; }}
.kpi .k-tip {{
    visibility: hidden; opacity: 0; transition: opacity 0.12s; position: absolute; z-index: 1000;
    background: #222; color: #fff; padding: 10px 14px; border-radius: 6px; white-space: nowrap;
    font-size: 0.95rem; line-height: 1.5; box-shadow: 0 2px 10px rgba(0,0,0,0.3); pointer-events: none;
}}
.kpi:hover {{ z-index: 1000; }}
.kpi:hover .k-tip {{ visibility: visible; opacity: 1; }}
.kpi.abajo .k-tip {{ top: calc(100% + 6px); }}
.kpi.arriba .k-tip {{ bottom: calc(100% + 6px); }}
.kpi.izq .k-tip {{ left: 0; }}
.kpi.centro .k-tip {{ left: 50%; transform: translateX(-50%); }}
.kpi.der .k-tip {{ right: 0; }}
.k-tip .sub {{ color: #bbb; }}
</style>
"""

df = sheets_io.load_data()

if df.empty:
    st.warning("Todavía no hay datos cargados. Andá a la pestaña **Cargar datos**.")
    st.stop()

rondas_disponibles = sorted(df["ronda"].dropna().unique().tolist())
dfp = df[df["empresa"] == EMPRESA_PROPIA]


def _etiqueta_ronda(r: int) -> str:
    return "Año 0 (inicial)" if r == 0 else f"Año {r}"


def _ronda_anterior(ronda: int):
    """Ronda inmediatamente anterior DENTRO de las cargadas (no resta 1 a lo bruto)."""
    idx = rondas_disponibles.index(ronda)
    return rondas_disponibles[idx - 1] if idx > 0 else None


def _fila(seccion: str, metrica: str, ronda: int, subseccion: str | None = None):
    cond = (dfp["seccion"] == seccion) & (dfp["metrica"] == metrica) & (dfp["ronda"] == ronda)
    if subseccion is not None:
        cond &= dfp["subseccion"] == subseccion
    f = dfp[cond]
    return None if f.empty else f.iloc[0]


def _valor(seccion: str, metrica: str, ronda: int, subseccion: str | None = None):
    f = _fila(seccion, metrica, ronda, subseccion)
    if f is None or pd.isna(f["valor_numerico"]):
        return None
    return float(f["valor_numerico"])


def _texto(seccion: str, metrica: str, ronda: int, subseccion: str | None = None):
    f = _fila(seccion, metrica, ronda, subseccion)
    if f is None or pd.isna(f["valor_raw"]) or str(f["valor_raw"]).strip() == "":
        return None
    return str(f["valor_raw"]).strip()


# ------------------------------------------------------------------
# Encabezado: logo | título | ronda | ⚙️ alto de gráficos
# ------------------------------------------------------------------
c_logo, c_tit, c_ronda, c_cfg = st.columns([1.1, 4, 1.5, 0.35], vertical_alignment="center")
with c_logo:
    style.mostrar_logo(ancho=130)
with c_tit:
    st.markdown(
        f'<div style="font-size:1.7rem;font-weight:700;color:{style.COLOR_TEXTO};">Panel de control — {EMPRESA_PROPIA}</div>',
        unsafe_allow_html=True,
    )
with c_ronda:
    opciones_ronda = {_etiqueta_ronda(r): r for r in rondas_disponibles}
    etiqueta_sel = st.selectbox(
        "Ronda", options=list(opciones_ronda.keys()), index=len(opciones_ronda) - 1,
        key="ronda_panel", label_visibility="collapsed",
    )
    ronda = opciones_ronda[etiqueta_sel]
with c_cfg:
    with st.popover("⚙️"):
        auto = st.checkbox(
            "Ajustar los gráficos al alto de la ventana", value=True, key="alto_auto",
            help="Desmarcalo para fijar un alto manual en px.",
        )
        alto_manual = st.slider(
            "Alto de los gráficos (px)", min_value=ALTO_MIN, max_value=ALTO_MAX, value=ALTO_GRAFICOS_DEFAULT,
            step=20, key="alto_panel", disabled=auto,
        )

if auto:
    alto_css = f"clamp({ALTO_MIN}px, calc(100vh - {ALTO_FIJO_PX}px), {ALTO_MAX}px)"
else:
    alto_css = f"{alto_manual}px"

ronda_prev = _ronda_anterior(ronda)
etiqueta_prev = _etiqueta_ronda(ronda_prev) if ronda_prev is not None else None


# ------------------------------------------------------------------
# Tarjetas (etiquetas) con tooltip de variación vs. año anterior
# ------------------------------------------------------------------
def _h(texto: str) -> str:
    """Escapa HTML y neutraliza '$' (st.markdown lo interpreta como LaTeX)."""
    return html_lib.escape(str(texto)).replace("$", "&#36;")


def _fmt(v, fmt: str) -> str:
    if v is None:
        return "—"
    if fmt == "pct":
        return f"{v:,.1f}%"
    if fmt == "pct2":
        return f"{v:,.2f}%"
    if fmt == "usd2":
        return f"${v:,.2f}"
    if fmt == "miles":
        return f"{'-' if v < 0 else ''}${abs(v):,.0f}k"
    return f"{v:,.2f}"


def _linea_variacion(v, previo, tipo: str, polaridad: int, fmt: str) -> list[str]:
    """Líneas HTML del tooltip: variación vs. ronda anterior.
    tipo: 'pp' (diferencia en puntos porcentuales) | 'pct' (variación %).
    polaridad: +1 = subir es bueno, -1 = subir es malo, 0 = neutro."""
    if v is None:
        return ["Sin datos"]
    if etiqueta_prev is None:
        return ["Primer año disponible"]
    if previo is None or (tipo == "pct" and previo == 0):
        return [f"Variación vs. {_h(etiqueta_prev)}: N/D"]
    if tipo == "pp":
        delta, txt = v - previo, f"{v - previo:+.1f} p.p."
    else:
        delta = (v - previo) / abs(previo) * 100
        txt = f"{delta:+.1f}%"
    flecha = "▲" if delta > 0 else ("▼" if delta < 0 else "■")
    if polaridad == 0 or delta == 0:
        color = "#ffffff"
    else:
        color = "#6fdc8c" if (delta > 0) == (polaridad > 0) else "#ff8a80"
    return [
        f'<span style="color:{color};font-weight:700;">{flecha} {txt}</span> vs. {_h(etiqueta_prev)}',
        f'<span class="sub">{_h(etiqueta_prev)}: {_h(_fmt(previo, fmt))}</span>',
    ]


def _tarjeta(etiqueta: str, valor_txt: str, lineas_tooltip: list[str], posicion: str, alineacion: str) -> str:
    return (
        f'<div class="kpi {posicion} {alineacion}"><div class="k-et">{_h(etiqueta)}</div>'
        f'<div class="k-val">{_h(valor_txt)}</div><div class="k-tip">{"<br>".join(lineas_tooltip)}</div></div>'
    )


def _tarjeta_simple(etiqueta, seccion, metrica, subseccion, fmt, tipo, polaridad, posicion, alineacion):
    v = _valor(seccion, metrica, ronda, subseccion)
    previo = _valor(seccion, metrica, ronda_prev, subseccion) if ronda_prev is not None else None
    return _tarjeta(etiqueta, _fmt(v, fmt), _linea_variacion(v, previo, tipo, polaridad, fmt), posicion, alineacion)


def _tarjeta_wacc(posicion: str, alineacion: str) -> str:
    met = "WACC, %"
    v = _valor(SECCION_VALUACION, met, ronda, SUB_DCF)
    previo = _valor(SECCION_VALUACION, met, ronda_prev, SUB_DCF) if ronda_prev is not None else None
    lineas = _linea_variacion(v, previo, "pp", -1, "pct2")

    def _extra(nombre: str, metrica: str, fmt: str, tipo: str) -> str | None:
        x = _valor(SECCION_VALUACION, metrica, ronda, SUB_DCF)
        if x is None:
            return None
        xp = _valor(SECCION_VALUACION, metrica, ronda_prev, SUB_DCF) if ronda_prev is not None else None
        resto = ""
        if xp is not None:
            resto = f' <span class="sub">({x - xp:+.2f}{" p.p." if tipo == "pp" else ""} vs. {_h(etiqueta_prev)})</span>'
        return f"{nombre}: <b>{_h(_fmt(x, fmt))}</b>{resto}"

    lineas.append("&nbsp;")
    for linea in (
        _extra("Beta", "Beta", "num2", "abs"),
        _extra("Ke (rend. esperado del patrimonio)", "Rendimiento esperado del patrimonio, %", "pct2", "pp"),
    ):
        if linea:
            lineas.append(linea)

    rating = _texto(SECCION_RATIOS, "Calificación crediticia", ronda, SUB_INDICADORES) or _texto(
        SECCION_VALUACION, "Calificación crediticia", ronda
    )
    if rating:
        rating_prev = (
            _texto(SECCION_RATIOS, "Calificación crediticia", ronda_prev, SUB_INDICADORES)
            or _texto(SECCION_VALUACION, "Calificación crediticia", ronda_prev)
            if ronda_prev is not None
            else None
        )
        if rating_prev is None:
            nota = ""
        elif rating_prev == rating:
            nota = ' <span class="sub">(sin cambios)</span>'
        else:
            nota = f' <span class="sub">(antes: {_h(rating_prev)})</span>'
        lineas.append(f"Calificación crediticia: <b>{_h(rating)}</b>{nota}")

    return _tarjeta("WACC", _fmt(v, "pct2"), lineas, posicion, alineacion)


# ------------------------------------------------------------------
# Gráficos
# ------------------------------------------------------------------
def _fig_ebitda():
    ingresos = _valor(SECCION_EERR, "Ingresos por ventas", ronda)
    ebitda = _valor(SECCION_EERR, "Beneficio operativo antes de depreciación (EBITDA)", ronda)
    if ingresos is None or ebitda is None:
        return None

    # El eje va en millones de USD (los datos vienen en miles); el hover muestra el valor exacto en miles.
    etiquetas, valores = ["Ingresos"], [ingresos / 1000]
    hover = [f"Ingresos por ventas: ${ingresos:,.0f}k"]
    for nombre, corta in COSTOS_EBITDA:
        v = _valor(SECCION_EERR, nombre, ronda) or 0
        etiquetas.append(corta)
        valores.append(-v / 1000)
        hover.append(f"{nombre}: -${v:,.0f}k")
    etiquetas.append("EBITDA")
    hover.append(f"EBITDA: {'-' if ebitda < 0 else ''}${abs(ebitda):,.0f}k")

    fig = go.Figure(
        go.Waterfall(
            x=etiquetas,
            y=valores + [ebitda / 1000],
            measure=["relative"] * len(valores) + ["total"],
            hovertext=hover,
            hoverinfo="text",
            textposition="none",
            increasing=dict(marker=dict(color=COLOR_INGRESO)),
            decreasing=dict(marker=dict(color=COLOR_COSTO)),
            totals=dict(marker=dict(color=COLOR_EBITDA)),
            connector=dict(line=dict(color="#BBBBBB", width=1, dash="dot")),
        )
    )
    fig.update_layout(
        title=dict(text="<b>EBITDA desagregado</b> (M USD)", x=0.01, y=0.97, font=dict(size=14)),
        autosize=True,
        margin=dict(t=38, b=50, l=50, r=10),
        yaxis=dict(tickformat=",.0f", gridcolor="#e5e5e5"),
        xaxis=dict(tickfont=dict(size=10)),
        showlegend=False,
        hoverlabel=style.HOVERLABEL_GRANDE,
        **style.FONDO_BLANCO_GRAFICO,
    )
    return fig


def _fig_estructura():
    barras = [("Activo", COMPONENTES_ACTIVO), ("Pasivo + PN", COMPONENTES_PPN)]
    totales = {}
    for cat, comps in barras:
        totales[cat] = sum(_valor(SECCION_BALANCE, n, ronda) or 0 for n, *_ in comps)
    if not any(totales.values()):
        return None

    fig = go.Figure()
    for cat, comps in barras:
        total = totales[cat]
        for nombre, corta, color, color_texto in comps:
            v = _valor(SECCION_BALANCE, nombre, ronda) or 0
            pct = v / total * 100 if total else 0
            fig.add_trace(
                go.Bar(
                    x=[cat],
                    y=[v / 1000],
                    name=corta,
                    marker=dict(color=color, line=dict(width=1, color="white")),
                    text=[f"{corta}<br>{pct:.0f}%" if pct >= 7 else ""],
                    textposition="inside",
                    textangle=0,
                    insidetextanchor="middle",
                    textfont=dict(size=11, color=color_texto),
                    hovertext=[f"<b>{nombre}</b><br>${v:,.0f}k ({pct:.1f}% de {cat})"],
                    hoverinfo="text",
                    showlegend=False,
                )
            )
        fig.add_annotation(
            x=cat, y=total / 1000, text=f"<b>${total / 1000:,.0f} M</b>", showarrow=False, yshift=12,
            font=dict(size=12, color=style.COLOR_TEXTO),
        )
    fig.update_layout(
        title=dict(text="<b>Estructura patrimonial</b> (M USD)", x=0.02, y=0.97, font=dict(size=14)),
        barmode="stack",
        autosize=True,
        margin=dict(t=38, b=30, l=50, r=10),
        yaxis=dict(tickformat=",.0f", gridcolor="#e5e5e5", range=[0, max(totales.values()) / 1000 * 1.1]),
        hoverlabel=style.HOVERLABEL_GRANDE,
        **style.FONDO_BLANCO_GRAFICO,
    )
    return fig


def _fig_market_share():
    # Cuota calculada desde unidades vendidas (igual que la pestaña Demanda): las filas
    # "cuotas de mercado, %" del Excel vienen normalizadas por tecnología, no por empresa.
    unidades = {}  # (empresa, región) -> unidades
    for region in REGIONES:
        sub = df[
            (df["ronda"] == ronda)
            & (df["seccion"] == f"Informe de mercado, {region}")
            & (df["metrica"] == "Ventas, miles unidades")
            & (df["subseccion"].isin(TECS))
        ]
        for empresa, v in sub.groupby("empresa")["valor_numerico"].sum().items():
            unidades[(empresa, region)] = float(v)

    total_region = {r: sum(v for (e, rr), v in unidades.items() if rr == r) for r in REGIONES}
    total_global = sum(total_region.values())
    if total_global == 0:
        return None

    empresas = sorted({e for e, _ in unidades})
    cuota_global = {e: sum(unidades.get((e, r), 0) for r in REGIONES) / total_global * 100 for e in empresas}
    hover = []
    for e in empresas:
        lineas = [f"<b>{e}</b>: {cuota_global[e]:.1f}% global"]
        for r in REGIONES:
            share = unidades.get((e, r), 0) / total_region[r] * 100 if total_region[r] else 0
            lineas.append(f"{r}: {share:.1f}%")
        hover.append("<br>".join(lineas))

    fig = go.Figure(
        go.Pie(
            labels=empresas,
            values=[cuota_global[e] for e in empresas],
            marker=dict(colors=[style.color_empresa(e, i) for i, e in enumerate(empresas)], line=dict(color="white", width=2)),
            pull=[0.07 if e == EMPRESA_PROPIA else 0 for e in empresas],
            sort=False,
            text=hover,
            hoverinfo="text",
            textinfo="label+percent",
            textfont=dict(size=13),
            showlegend=False,
        )
    )
    fig.update_layout(
        title=dict(text="<b>Market share global</b> (unidades vendidas)", x=0.02, y=0.97, font=dict(size=14)),
        autosize=True,
        margin=dict(t=45, b=15, l=15, r=15),
        hoverlabel=style.HOVERLABEL_GRANDE,
        **style.FONDO_BLANCO_GRAFICO,
    )
    return fig


def _mostrar(fig, vacio: str, key: str):
    if fig is None:
        st.info(vacio)
    else:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=key)


# ------------------------------------------------------------------
# Disposición
# ------------------------------------------------------------------
tarjetas_arriba = [
    _tarjeta_simple("Retorno acum. accionista (p.a.)", SECCION_RATIOS, "Retorno total acumulado del accionista (p.a.), %", SUB_RATIOS, "pct", "pp", 1, "abajo", "izq"),
    _tarjeta_simple("Precio de la acción", SECCION_RATIOS, "Precio de la acción al final de la ronda, USD", SUB_RATIOS, "usd2", "pct", 1, "abajo", "centro"),
    _tarjeta_simple("ROCE", SECCION_RATIOS, "Rentabilidad del capital empleado (ROCE)", SUB_INDICADORES, "pct", "pp", 1, "abajo", "centro"),
    _tarjeta_simple("ROE", SECCION_RATIOS, "Rendimiento de los Fondos Propios (ROE)", SUB_INDICADORES, "pct", "pp", 1, "abajo", "centro"),
    _tarjeta_simple("Margen bruto", SECCION_RATIOS, "Margen bruto", SUB_INDICADORES, "pct", "pp", 1, "abajo", "der"),
]
tarjetas_abajo = [
    _tarjeta_simple("Beneficio de la ronda", SECCION_EERR, "Beneficio de la ronda", None, "miles", "pct", 1, "arriba", "izq"),
    _tarjeta_wacc("arriba", "centro"),
    _tarjeta_simple("Endeudamiento neto / patrimonio", SECCION_RATIOS, "Endeudamiento neto/patrimonio (apalancamiento)", SUB_INDICADORES, "pct", "pp", 0, "arriba", "der"),
]

# El CSS va pegado a la primera fila de tarjetas para no agregar un elemento vacío (y su espacio) a la página.
st.markdown(CSS_PANEL.replace("ALTO_G_VALOR", alto_css) + '<div class="kpi-grid g5">' + "".join(tarjetas_arriba) + "</div>", unsafe_allow_html=True)

col_izq, col_der = st.columns([3, 2])
with col_izq:
    c_eb, c_bal = st.columns([2, 1])
    with c_eb:
        _mostrar(_fig_ebitda(), f"Sin datos de EBITDA para {EMPRESA_PROPIA} en esta ronda.", "fig_ebitda")
    with c_bal:
        _mostrar(_fig_estructura(), f"Sin datos de balance para {EMPRESA_PROPIA} en esta ronda.", "fig_estructura")
    st.markdown('<div class="kpi-grid g3">' + "".join(tarjetas_abajo) + "</div>", unsafe_allow_html=True)
with col_der:
    _mostrar(_fig_market_share(), "No hay ventas registradas en esta ronda.", "fig_market_share")