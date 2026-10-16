import pandas as pd
import streamlit as st
import plotly.graph_objects as go

import sheets_io
import style

st.set_page_config(page_title="Ratios e indicadores financieros clave", layout="wide")
style.mostrar_logo()
st.title("📊 Ratios e indicadores financieros clave")

SECCION_RATIOS = "Ratios e indicadores financieros clave"
SECCION_EERR = "Cuenta de resultados, miles USD, Global"
SECCION_EFE = "Flujo de efectivo de casa matriz, miles USD"
MERCADOS_GLOBAL = ["EE.UU.", "Asia", "Europa"]  # para sumar y obtener el total "Global"

EMPRESA_PROPIA = "LAST1"
EMPRESAS_DEFAULT_DESEADAS = ["LAST1", "JAPON", "IMPUL"]  # LAST1 + competencia directa

df = sheets_io.load_data()

if df.empty:
    st.warning("Todavía no hay datos cargados. Andá a la pestaña **Cargar datos** para subir la primera ronda.")
    st.stop()

sub_ratios = df[df["seccion"] == SECCION_RATIOS].copy()

# Solo ofrecemos en el selector las métricas de Ratios que son numéricas
# (así excluimos automáticamente cosas como "Calificación crediticia", que
# es texto tipo 'AA-' y no se puede graficar como línea).
metricas_validas = (
    sub_ratios.dropna(subset=["valor_numerico"])
    .groupby(["subseccion", "metrica"])
    .size()
    .reset_index()[["subseccion", "metrica"]]
    .drop_duplicates()
    .sort_values(["subseccion", "metrica"])
)

opciones_metrica = {
    f"{row.subseccion} — {row.metrica}": dict(
        tipo="directo", seccion=SECCION_RATIOS, subseccion=row.subseccion, metrica=row.metrica
    )
    for row in metricas_validas.itertuples()
}

# Métricas adicionales (todas a nivel Global), fuera de la sección de Ratios.
opciones_metrica["Resultados — Ingresos por ventas"] = dict(
    tipo="directo", seccion=SECCION_EERR, subseccion=None, metrica="Ingresos por ventas"
)
opciones_metrica["Resultados — EBITDA"] = dict(
    tipo="directo",
    seccion=SECCION_EERR,
    subseccion=None,
    metrica="Beneficio operativo antes de depreciación (EBITDA)",
)
opciones_metrica["Flujo de efectivo — Variación en la caja"] = dict(
    tipo="directo", seccion=SECCION_EFE, subseccion=None, metrica="Cambios en efectivo y equivalentes de efectivo"
)
opciones_metrica["Mercado — Demanda de unidades (todas las tecnologías)"] = dict(tipo="demanda_total")

empresas_disponibles = sorted(df["empresa"].dropna().unique().tolist())
empresas_default = [e for e in EMPRESAS_DEFAULT_DESEADAS if e in empresas_disponibles] or empresas_disponibles[:1]


def _serie(entrada: dict, empresa: str):
    """Devuelve un DataFrame [ronda, valor_numerico] para la empresa dada,
    sin importar si la métrica es una fila directa de los datos o un
    cálculo (como la demanda total sumada entre mercados y tecnologías)."""
    if entrada["tipo"] == "demanda_total":
        secciones = [f"Informe de mercado, {m}" for m in MERCADOS_GLOBAL]
        filas = df[
            (df["empresa"] == empresa) & (df["metrica"] == "Demanda, miles unidades") & (df["seccion"].isin(secciones))
        ]
        if filas.empty:
            return filas[["ronda", "valor_numerico"]]
        return filas.groupby("ronda", as_index=False)["valor_numerico"].sum().sort_values("ronda")

    cond = (df["seccion"] == entrada["seccion"]) & (df["metrica"] == entrada["metrica"]) & (df["empresa"] == empresa)
    if entrada.get("subseccion") is not None:
        cond &= df["subseccion"] == entrada["subseccion"]
    return df[cond][["ronda", "valor_numerico"]].dropna().sort_values("ronda")

col1, col2 = st.columns([2, 2])
with col1:
    etiqueta_metrica = st.selectbox(
        "Métrica",
        options=list(opciones_metrica.keys()),
        index=list(opciones_metrica.keys()).index(
            next((k for k in opciones_metrica if "Retorno total acumulado del accionista" in k), list(opciones_metrica.keys())[0])
        ),
    )
with col2:
    empresas_sel = st.multiselect("Empresas a comparar", options=empresas_disponibles, default=empresas_default)

if not empresas_sel:
    st.info("Seleccioná al menos una empresa.")
    st.stop()

entrada_sel = opciones_metrica[etiqueta_metrica]
titulo_eje_y = etiqueta_metrica.split(" — ", 1)[-1]
es_porcentaje = "%" in titulo_eje_y

datos_por_empresa = {}
for empresa in empresas_sel:
    d = _serie(entrada_sel, empresa).copy()
    d["empresa"] = empresa
    datos_por_empresa[empresa] = d
datos = pd.concat(datos_por_empresa.values(), ignore_index=True) if datos_por_empresa else pd.DataFrame()

fig = go.Figure()
for idx, empresa in enumerate(empresas_sel):
    datos_empresa = datos_por_empresa[empresa]
    fig.add_trace(
        go.Scatter(
            x=datos_empresa["ronda"],
            y=datos_empresa["valor_numerico"],
            mode="lines+markers",
            name=empresa,
            line=dict(width=4 if empresa == EMPRESA_PROPIA else 2, color=style.color_empresa_oscuro(empresa, idx)),
            marker=dict(size=8 if empresa == EMPRESA_PROPIA else 6, color=style.color_empresa_oscuro(empresa, idx)),
        )
    )

ronda_min_cargada = int(df["ronda"].min())
ronda_max_cargada = int(df["ronda"].max())

fig.update_layout(
    height=560,
    xaxis=dict(
        title="Ronda (0 = situación inicial)",
        tickmode="linear",
        dtick=1,
        range=[ronda_min_cargada - 0.5, ronda_max_cargada + 0.5],
    ),
    yaxis=dict(title=titulo_eje_y + (" (%)" if es_porcentaje else "")),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(t=60, b=40, l=50, r=20),
    hovermode="x unified",
    hoverlabel=style.HOVERLABEL_GRANDE,
    **style.FONDO_BLANCO_GRAFICO,
)
fig.update_xaxes(gridcolor="#e5e5e5")
fig.update_yaxes(gridcolor="#e5e5e5")

st.plotly_chart(fig, use_container_width=True)

with st.expander("Ver datos"):
    st.dataframe(
        datos[["ronda", "empresa", "valor_numerico"]].rename(columns={"valor_numerico": "valor"}),
        use_container_width=True,
        hide_index=True,
    )