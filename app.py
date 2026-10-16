import streamlit as st

import style

st.set_page_config(page_title="Control de Gestión - Simulador", layout="wide")
style.mostrar_logo()

EMPRESA_PROPIA = "LAST1"

st.title("Control de Gestión — Equipo LAST1")

st.markdown(
    """
Usá el menú de la izquierda para navegar entre pestañas:

- **Cargar datos** → Subí el Excel de cada ronda nueva del simulador.
- **Ratios e indicadores financieros clave** → Evolución de ratios por ronda y empresa.
- **Ventas** → Composición de las ventas versus demanda, demanda insatisfecha y stock.
- **Demanda** → Market share global y por region, desagregado por tecnologia.
- **Estados Financieros** → Situacion financiera al final de ronda, con varaiacion entre años y analisis vertical.

Se irán agregando más pestañas a medida que las vayamos armando.
"""
)

st.info(f"Empresa propia configurada: **{EMPRESA_PROPIA}** (aparece destacada en los gráficos)")