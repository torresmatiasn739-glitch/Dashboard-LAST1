import streamlit as st
import plotly.graph_objects as go

import sheets_io
import style

st.set_page_config(page_title="Demanda", layout="wide")
style.mostrar_logo()
st.title("🥧 Demanda")

MERCADOS = ["Global", "EE.UU.", "Asia", "Europa"]
TECS = ["Tec 1", "Tec 2", "Tec 3", "Tec 4"]
COLOR_TEC = {
    "Tec 1": "#D32F2F",  # rojo
    "Tec 2": "#F9A825",  # amarillo
    "Tec 3": "#2E7D32",  # verde
    "Tec 4": "#1E64C8",  # azul
}

df = sheets_io.load_data()

if df.empty:
    st.warning("Todavía no hay datos cargados. Andá a la pestaña **Cargar datos**.")
    st.stop()

rondas_disponibles = sorted(df["ronda"].dropna().unique().tolist())

col_a, col_b = st.columns(2)
with col_a:
    mercado_sel = st.selectbox("Mercado", options=MERCADOS)
with col_b:
    opciones_ronda = {
        ("Ronda 0 (situación inicial)" if r == 0 else f"Ronda {r}"): r for r in rondas_disponibles
    }
    etiqueta_ronda = st.selectbox("Ronda", options=list(opciones_ronda.keys()), index=len(opciones_ronda) - 1)
    ronda_actual = opciones_ronda[etiqueta_ronda]

ronda_anterior = ronda_actual - 1
regiones = ["EE.UU.", "Asia", "Europa"] if mercado_sel == "Global" else [mercado_sel]


def _datos_de_ronda(ronda: int):
    """Unidades vendidas por (empresa, tec) y el total de mercado, sumado
    sobre las regiones correspondientes a `mercado_sel`. Usamos unidades
    (Ventas, miles unidades) en vez de las filas 'cuotas de mercado, %' del
    Excel porque esas vienen normalizadas DENTRO de cada tecnología (suman
    100% por tec, no por empresa) y no se pueden desagregar directamente
    por empresa. Reconstruir la cuota desde unidades da el mismo resultado
    que reporta el simulador (verificado), con la ventaja de que se puede
    desagregar de forma consistente."""
    if ronda not in rondas_disponibles:
        return None
    unidades = {}
    total = 0.0
    for region in regiones:
        seccion = f"Informe de mercado, {region}"
        sub = df[(df["ronda"] == ronda) & (df["seccion"] == seccion) & (df["metrica"] == "Ventas, miles unidades")]
        for _, fila in sub.iterrows():
            v = fila["valor_numerico"] or 0
            key = (fila["empresa"], fila["subseccion"])  # subseccion = "Tec N"
            unidades[key] = unidades.get(key, 0) + v
            total += v
    return unidades, total


def _armar_pie(unidades: dict, total: float) -> go.Figure:
    cuota_empresa = {}
    cuota_tec = {}
    for (empresa, tec), v in unidades.items():
        share = (v / total * 100) if total else 0
        cuota_empresa[empresa] = cuota_empresa.get(empresa, 0) + share
        cuota_tec[(empresa, tec)] = share

    orden = sorted(cuota_empresa.keys())
    hover = []
    for empresa in orden:
        lineas = [f"<b>{empresa}</b>: {cuota_empresa[empresa]:.1f}% del mercado"]
        for tec in TECS:
            s = cuota_tec.get((empresa, tec), 0)
            if s > 0.001:  # solo tecnologías donde esta empresa vendió algo
                lineas.append(f"{tec}: {s:.1f}%")
        hover.append("<br>".join(lineas))

    fig = go.Figure(
        data=[
            go.Pie(
                labels=orden,
                values=[cuota_empresa[e] for e in orden],
                text=hover,
                hoverinfo="text",
                textinfo="label+percent",
            )
        ]
    )
    fig.update_layout(height=380, margin=dict(t=10, b=10, l=10, r=10), hoverlabel=style.HOVERLABEL_GRANDE)
    return fig


def _armar_barras_tec(unidades: dict):
    totales_tec = {tec: 0.0 for tec in TECS}
    for (empresa, tec), v in unidades.items():
        totales_tec[tec] = totales_tec.get(tec, 0) + v
    tecs_con_datos = [t for t in TECS if totales_tec[t] > 0]

    fig = go.Figure(
        data=[
            go.Bar(
                x=tecs_con_datos,
                y=[totales_tec[t] for t in tecs_con_datos],
                marker_color=[COLOR_TEC[t] for t in tecs_con_datos],
                text=[f"{totales_tec[t]:,.0f}" for t in tecs_con_datos],
                textposition="outside",
            )
        ]
    )
    fig.update_layout(
        height=260,
        yaxis=dict(title="Miles de unidades"),
        margin=dict(t=20, b=20, l=50, r=10),
        hoverlabel=style.HOVERLABEL_GRANDE,
    )
    return fig, sum(totales_tec.values())


col1, col2 = st.columns(2)
secciones = [
    (col1, ronda_actual, "Ronda actual", "Total unidades de mercado"),
    (col2, ronda_anterior, "Ronda anterior", "Total unidades de mercado (ronda anterior)"),
]

for col, ronda, titulo, subtitulo in secciones:
    with col:
        st.subheader(titulo)
        datos = _datos_de_ronda(ronda)

        if ronda not in rondas_disponibles:
            st.info(f"No hay datos cargados para la ronda {ronda}.")
            continue

        unidades, total = datos
        if total == 0:
            st.info("No hay ventas registradas para esta selección.")
            continue

        st.plotly_chart(_armar_pie(unidades, total), use_container_width=True)

        st.markdown(f"**{subtitulo}**")
        fig_barras, total_unidades = _armar_barras_tec(unidades)
        st.plotly_chart(fig_barras, use_container_width=True)
        st.caption(f"Total: {total_unidades:,.0f} miles de unidades")