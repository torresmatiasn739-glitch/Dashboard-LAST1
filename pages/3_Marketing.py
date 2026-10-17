import html as html_lib

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

import sheets_io
import style

st.set_page_config(page_title="Marketing", layout="wide")
style.mostrar_logo()
st.title("📣 Marketing")

EMPRESA_PROPIA = "LAST1"
EMPRESAS_DEFAULT_DESEADAS = ["LAST1", "JAPON", "IMPUL"]  # LAST1 + competencia directa
MERCADOS_CON_PRECIO = ["EE.UU.", "Asia", "Europa"]  # "Global" no tiene precio/características propios
MERCADOS = MERCADOS_CON_PRECIO + ["Global"]
TECS = ["Tec 1", "Tec 2", "Tec 3", "Tec 4"]
MERCADOS_CON_INVENTARIO = ("EE.UU.", "Asia")

COLOR_VENTAS = "#1DB954"
COLOR_DEMANDA = "#2F6FED"
COLOR_INSATISFECHA = "#E3342F"
COLOR_INVENTARIO = "#F2C94C"

df = sheets_io.load_data()

if df.empty:
    st.warning("Todavía no hay datos cargados. Andá a la pestaña **Cargar datos**.")
    st.stop()

rondas_disponibles = sorted(df["ronda"].dropna().unique().tolist())
empresas_disponibles = sorted(df["empresa"].dropna().unique().tolist())


def _etiqueta_ronda(r: int) -> str:
    return "Año 0 (inicial)" if r == 0 else f"Año {r}"


def _valor(seccion: str, metrica: str, empresa: str, ronda: int, subseccion: str | None = None):
    condicion = (
        (df["seccion"] == seccion) & (df["metrica"] == metrica) & (df["empresa"] == empresa) & (df["ronda"] == ronda)
    )
    if subseccion is not None:
        condicion &= df["subseccion"] == subseccion
    fila = df[condicion]
    if fila.empty:
        return None
    v = fila["valor_numerico"].iloc[0]
    return None if pd.isna(v) else float(v)


# ============================================================
# PRECIOS Y CARACTERÍSTICAS POR EQUIPO
# ============================================================
st.header("Precios y características por equipo")

col1, col2 = st.columns(2)
with col1:
    opciones_ronda_m = {_etiqueta_ronda(r): r for r in rondas_disponibles}
    etiqueta_m = st.selectbox(
        "Año", options=list(opciones_ronda_m.keys()), index=len(opciones_ronda_m) - 1, key="ronda_marketing_top"
    )
    ronda_m = opciones_ronda_m[etiqueta_m]
with col2:
    mercado_m = st.selectbox(
        "Mercado", options=MERCADOS_CON_PRECIO, key="mercado_marketing_top",
        help="El precio y las características se definen por mercado; 'Global' no aplica acá.",
    )

seccion_m = f"Informe de mercado, {mercado_m}"

# El nombre de la fila de precio cambia de moneda según el mercado (el
# simulador reporta cada región en su propia moneda, no todo en USD).
METRICA_PRECIO_POR_MERCADO = {
    "EE.UU.": "Precio de venta, USD",
    "Asia": "Precio de venta, RMB",
    "Europa": "Precio de venta, EUR",
}
SIMBOLO_MONEDA_POR_MERCADO = {"EE.UU.": "$", "Asia": "¥", "Europa": "€"}

metrica_precio_m = METRICA_PRECIO_POR_MERCADO[mercado_m]
simbolo_moneda_m = SIMBOLO_MONEDA_POR_MERCADO[mercado_m]


def _grilla_tarjetas(titulo_metrica: str, metrica: str, formatear):
    st.subheader(titulo_metrica)
    tarjetas_html = []
    for empresa in empresas_disponibles:
        lineas = []
        for tec in TECS:
            v = _valor(seccion_m, metrica, empresa, ronda_m, subseccion=tec)
            if v is not None:
                lineas.append(f"{tec}: {formatear(v)}")
        contenido = "<br>".join(lineas) if lineas else '<span style="color:#999;">Sin datos</span>'
        tarjetas_html.append(
            '<div style="background:white; border:1px solid #d9d9d9; border-radius:8px; '
            'padding:12px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);">'
            f'<div style="font-weight:700; margin-bottom:6px; color:#1B2A3A;">{empresa}</div>'
            f'<div style="font-size:0.88rem; color:#333; line-height:1.6;">{contenido}</div>'
            "</div>"
        )
    grid_html = (
        '<div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); '
        'gap:12px; margin-bottom:1.2rem;">' + "".join(tarjetas_html) + "</div>"
    )
    st.markdown(grid_html, unsafe_allow_html=True)


_grilla_tarjetas("Precios de venta", metrica_precio_m, lambda v: f"{simbolo_moneda_m}{v:,.0f}")
_grilla_tarjetas("Cantidad de características", "Cantidad de características ofrecidas", lambda v: f"{v:.0f}")

# La Promoción se reporta siempre en USD (a diferencia del precio, que
# cambia de moneda por mercado) — verificado sumando las 3 regiones contra
# "Promoción" de Cuenta de resultados Global, da exacto.
SECCION_DESGLOSE = "Desglose de margen por tec"

st.markdown(style.CSS_TOOLTIP_GRANDE, unsafe_allow_html=True)


def _linea_con_tooltip(texto_visible: str, texto_tooltip: str) -> str:
    return (
        f'<span class="tt">{html_lib.escape(texto_visible)}'
        f'<span class="tttext">{html_lib.escape(texto_tooltip)}</span></span>'
    )


st.subheader("Promoción")
tarjetas_promo = []
for empresa in empresas_disponibles:
    lineas = []
    for tec in TECS:
        promocion = _valor(SECCION_DESGLOSE, tec, empresa, ronda_m, subseccion=f"Promoción — {mercado_m}")
        if promocion is None:
            continue
        ventas = _valor(seccion_m, "Ventas, miles unidades", empresa, ronda_m, subseccion=tec)
        if ventas:
            # Promoción está en miles de USD y Ventas en miles de unidades:
            # al dividir, el factor "miles" se cancela y queda directo en
            # USD por unidad (no hace falta multiplicar ni dividir por 1000).
            por_unidad = promocion / ventas
            tooltip = f"Promoción por unidad vendida: ${por_unidad:,.2f}"
        else:
            tooltip = "Promoción por unidad vendida: sin ventas registradas"
        texto = f"{tec}: ${promocion:,.0f}"
        lineas.append(_linea_con_tooltip(texto, tooltip))
    contenido = "<br>".join(lineas) if lineas else '<span style="color:#999;">Sin datos</span>'
    tarjetas_promo.append(
        '<div style="background:white; border:1px solid #d9d9d9; border-radius:8px; '
        'padding:12px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);">'
        f'<div style="font-weight:700; margin-bottom:6px; color:#1B2A3A;">{empresa}</div>'
        f'<div style="font-size:0.88rem; color:#333; line-height:1.8;">{contenido}</div>'
        "</div>"
    )
st.markdown(
    '<div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); '
    'gap:12px; margin-bottom:1.2rem;">' + "".join(tarjetas_promo) + "</div>",
    unsafe_allow_html=True,
)
st.caption("Pasá el cursor sobre un valor para ver la promoción por unidad vendida.")

st.divider()

# ============================================================
# BURBUJAS: Precio x Ventas, tamaño = características (una por tecnología)
# ============================================================
st.subheader("Precio, ventas y características por tecnología")
st.caption("Cada burbuja es un equipo. Eje X: precio de venta. Eje Y: unidades vendidas. Tamaño: cantidad de características.")


def _armar_burbuja(tec: str):
    puntos = []
    for idx, empresa in enumerate(empresas_disponibles):
        precio = _valor(seccion_m, metrica_precio_m, empresa, ronda_m, subseccion=tec)
        ventas = _valor(seccion_m, "Ventas, miles unidades", empresa, ronda_m, subseccion=tec)
        caract = _valor(seccion_m, "Cantidad de características ofrecidas", empresa, ronda_m, subseccion=tec)
        if precio is None or ventas is None:
            continue
        puntos.append((empresa, idx, precio, ventas, caract or 0))

    if not puntos:
        return None

    max_caract = max(c for _, _, _, _, c in puntos) or 1
    sizeref = 2.0 * max_caract / (55.0**2)

    fig = go.Figure()
    for empresa, idx, precio, ventas, caract in puntos:
        fig.add_trace(
            go.Scatter(
                x=[precio],
                y=[ventas],
                mode="markers",
                name=empresa,
                marker=dict(
                    size=[caract],
                    sizemode="area",
                    sizeref=sizeref,
                    sizemin=8,
                    color=style.color_empresa(empresa, idx),
                    line=dict(width=1, color="white"),
                ),
                hovertext=[
                    f"<b>{empresa}</b><br>Precio: {simbolo_moneda_m}{precio:,.0f}<br>Ventas: {ventas:,.0f} mil u.<br>Características: {caract:.0f}"
                ],
                hoverinfo="text",
            )
        )

    fig.update_layout(
        height=420,
        xaxis=dict(title=f"Precio de venta ({mercado_m}, {simbolo_moneda_m})", gridcolor="#e5e5e5"),
        yaxis=dict(title="Ventas (miles de unidades)", gridcolor="#e5e5e5"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(t=50, b=40, l=60, r=20),
        hoverlabel=style.HOVERLABEL_GRANDE,
        **style.FONDO_BLANCO_GRAFICO,
    )
    return fig


hubo_burbuja = False
for tec in TECS:
    fig_burbuja = _armar_burbuja(tec)
    if fig_burbuja is None:
        continue
    hubo_burbuja = True
    st.markdown(f"**{tec}**")
    st.plotly_chart(fig_burbuja, use_container_width=True)

if not hubo_burbuja:
    st.info("No hay precio/ventas registrados para ninguna tecnología en esta selección.")

st.divider()

# ============================================================
# VENTAS (gráficos que ya existían en la pestaña)
# ============================================================
st.header("Ventas")

col3, col4, col5 = st.columns([2, 1, 1])
with col3:
    empresas_default = [e for e in EMPRESAS_DEFAULT_DESEADAS if e in empresas_disponibles] or empresas_disponibles[:1]
    empresas_sel = st.multiselect("Empresas", options=empresas_disponibles, default=empresas_default, key="empresas_ventas")
with col4:
    opciones_ronda = {_etiqueta_ronda(r): r for r in rondas_disponibles}
    etiqueta_ronda = st.selectbox(
        "Ronda / año", options=list(opciones_ronda.keys()), index=len(opciones_ronda) - 1, key="ronda_ventas"
    )
    ronda_sel = opciones_ronda[etiqueta_ronda]
with col5:
    mercado_sel = st.selectbox("Mercado", options=MERCADOS, key="mercado_ventas")

if not empresas_sel:
    st.info("Seleccioná al menos una empresa.")
    st.stop()

mercados_a_sumar = ["EE.UU.", "Asia", "Europa"] if mercado_sel == "Global" else [mercado_sel]

st.markdown(
    "".join(
        f'<span style="margin-right:24px;">'
        f'<span style="display:inline-block;width:13px;height:13px;background:{color};'
        f'margin-right:6px;border-radius:2px;"></span>{label}</span>'
        for label, color in [
            ("Ventas", COLOR_VENTAS),
            ("Demanda", COLOR_DEMANDA),
            ("Demanda insatisfecha", COLOR_INSATISFECHA),
            ("Inventario", COLOR_INVENTARIO),
        ]
    ),
    unsafe_allow_html=True,
)
st.write("")


def _sumar_metrica(tec: str, metrica: str, mercados: list[str]) -> dict:
    resultado = {e: 0.0 for e in empresas_sel}
    for mercado in mercados:
        seccion = f"Informe de mercado, {mercado}"
        sub = df[
            (df["ronda"] == ronda_sel)
            & (df["seccion"] == seccion)
            & (df["subseccion"] == tec)
            & (df["metrica"] == metrica)
            & (df["empresa"].isin(empresas_sel))
        ]
        for _, fila in sub.iterrows():
            resultado[fila["empresa"]] += fila["valor_numerico"] or 0
    return resultado


def _sumar_inventario(tec: str, mercados: list[str]) -> dict:
    resultado = {e: 0.0 for e in empresas_sel}
    for mercado in mercados:
        if mercado not in MERCADOS_CON_INVENTARIO:
            continue
        subseccion = f"Inventario, miles unidades — {mercado}"
        sub = df[
            (df["ronda"] == ronda_sel)
            & (df["seccion"] == "Detalles de fabricación")
            & (df["subseccion"] == subseccion)
            & (df["metrica"] == tec)
            & (df["empresa"].isin(empresas_sel))
        ]
        for _, fila in sub.iterrows():
            resultado[fila["empresa"]] += fila["valor_numerico"] or 0
    return resultado


hubo_algo = False

for tec in TECS:
    ventas = _sumar_metrica(tec, "Ventas, miles unidades", mercados_a_sumar)
    demanda = _sumar_metrica(tec, "Demanda, miles unidades", mercados_a_sumar)
    inventario = _sumar_inventario(tec, mercados_a_sumar)

    if all(v == 0 for v in ventas.values()) and all(v == 0 for v in demanda.values()):
        continue

    hubo_algo = True
    insatisfecha = {e: max(demanda[e] - ventas[e], 0) for e in empresas_sel}

    st.subheader(tec)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=empresas_sel,
            y=[ventas[e] for e in empresas_sel],
            name="Ventas",
            marker_color=COLOR_VENTAS,
            offsetgroup="ventas_demanda",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Bar(
            x=empresas_sel,
            y=[insatisfecha[e] for e in empresas_sel],
            name="Demanda insatisfecha",
            marker_color=COLOR_INSATISFECHA,
            offsetgroup="ventas_demanda",
            base=[ventas[e] for e in empresas_sel],
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Bar(
            x=empresas_sel,
            y=[demanda[e] for e in empresas_sel],
            name="Demanda",
            marker_color=COLOR_DEMANDA,
            offsetgroup="demanda",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Bar(
            x=empresas_sel,
            y=[inventario[e] for e in empresas_sel],
            name="Inventario",
            marker_color=COLOR_INVENTARIO,
            offsetgroup="inventario",
            showlegend=False,
        )
    )

    fig.update_layout(
        barmode="group",
        height=360,
        xaxis=dict(gridcolor="#e5e5e5"),
        yaxis=dict(title="Miles de unidades", gridcolor="#e5e5e5"),
        margin=dict(t=20, b=30, l=50, r=20),
        hoverlabel=style.HOVERLABEL_GRANDE,
        **style.FONDO_BLANCO_GRAFICO,
    )

    st.plotly_chart(fig, use_container_width=True)

if not hubo_algo:
    st.info("No hay ventas ni demanda registradas para ninguna tecnología con esta selección.")