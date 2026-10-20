import streamlit as st
import plotly.graph_objects as go

import produccion_comun as pr
import sheets_io
import style


st.set_page_config(page_title="Producción", layout="wide")

col_logo, col_titulo = st.columns([1, 5])
with col_logo:
    style.mostrar_logo(ancho=130)
with col_titulo:
    st.title("Producción")

EMPRESA_PROPIA = "LAST1"

EMPRESAS_DEFAULT_DESEADAS = ["LAST1", "JAPON", "IMPUL"]
MERCADOS = ["EE.UU.", "Asia", "Europa", "Global"]
MERCADOS_CON_INVENTARIO = ("EE.UU.", "Asia")
TECS = pr.TECS

COLOR_VENTAS = "#1DB954"
COLOR_DEMANDA = "#2F6FED"
COLOR_INSATISFECHA = "#E3342F"
COLOR_INVENTARIO = "#F2C94C"


def _etiqueta_ronda(r: int) -> str:
    return "Año 0 (inicial)" if r == 0 else f"Año {r}"


df = sheets_io.load_data()
if df.empty:
    st.warning("Todavía no hay datos cargados. Andá a la pestaña **Cargar datos**.")
    st.stop()

rondas = sorted(int(r) for r in df["ronda"].dropna().unique())
empresas = sorted(df["empresa"].dropna().unique().tolist())
if not rondas or not empresas:
    st.warning("No hay rondas o empresas válidas en los datos cargados.")
    st.stop()

col_empresa, col_ronda = st.columns([2, 1])
with col_empresa:
    empresa = st.selectbox(
        "Empresa", options=empresas,
        index=empresas.index(EMPRESA_PROPIA) if EMPRESA_PROPIA in empresas else 0,
        key="produccion_empresa",
    )
with col_ronda:
    ronda = st.selectbox(
        "Ronda", options=rondas, index=len(rondas) - 1,
        format_func=lambda r: "Año 0 (inicial)" if r == 0 else f"Año {r}",
        key="produccion_ronda",
    )

estados = [pr.leer_region(df, empresa, ronda, region) for region in pr.REGIONES]
st.markdown(pr.grilla_produccion(estados), unsafe_allow_html=True)
st.caption(
    "Pasá el cursor sobre cada fábrica (o tocala) para ver la cantidad de plantas "
    "y el costo de producción interna por tecnología, en USD/unidad."
)

if any(not estado.capacidad_cargada for estado in estados):
    st.info(
        "Esta selección no tiene los nuevos campos de capacidad. "
        "Volvé a subir el Excel de esta ronda desde **Cargar datos** para incorporarlos. "
        "Los datos ausentes se muestran como N/D, no como capacidad cero "
        "(salvo cuando no hay fábricas operativas)."
    )
if any(
    not estado.costos_cargados and (estado.utilizacion or 0) > 0
    for estado in estados
):
    st.info(
        "No está cargado el bloque de costos internos de esta ronda. "
        "Volvé a subir su Excel desde **Cargar datos** para completar los tooltips."
    )

st.divider()

# ============================================================
# VENTAS, DEMANDA E INVENTARIO (trasladado desde Marketing)
# ============================================================
st.header("Ventas")

col3, col4, col5 = st.columns([2, 1, 1])
with col3:
    empresas_default = [e for e in EMPRESAS_DEFAULT_DESEADAS if e in empresas] or empresas[:1]
    empresas_sel = st.multiselect("Empresas", options=empresas, default=empresas_default, key="produccion_ventas_empresas")
with col4:
    opciones_ronda = {_etiqueta_ronda(r): r for r in rondas}
    etiqueta_ronda = st.selectbox(
        "Ronda / año", options=list(opciones_ronda.keys()), index=len(opciones_ronda) - 1, key="produccion_ventas_ronda"
    )
    ronda_sel = opciones_ronda[etiqueta_ronda]
with col5:
    mercado_sel = st.selectbox("Mercado", options=MERCADOS, key="produccion_ventas_mercado")

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

    st.plotly_chart(fig, use_container_width=True, key=f"produccion_ventas_{tec}")

if not hubo_algo:
    st.info("No hay ventas ni demanda registradas para ninguna tecnología con esta selección.")