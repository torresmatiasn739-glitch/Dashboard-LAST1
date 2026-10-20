import streamlit as st

import panel_comun as pc
import sheets_io

st.set_page_config(page_title="Panel de control", layout="wide")

df = sheets_io.load_data()
if df.empty:
    st.warning("Todavía no hay datos cargados. Andá a la pestaña **Cargar datos**.")
    st.stop()

panel = pc.Panel(df)
ronda, alto_css = pc.encabezado(panel, "Panel de control", prefijo="pc1")

S = pc.SECCION_RATIOS
tarjetas_arriba = [
    panel.tarjeta_simple(ronda, "Retorno acum. accionista (p.a.)", S, "Retorno total acumulado del accionista (p.a.), %", pc.SUB_RATIOS, "pct", "pp", 1, "abajo", "izq", ranking=True),
    panel.tarjeta_simple(ronda, "Precio de la acción", S, "Precio de la acción al final de la ronda, USD", pc.SUB_RATIOS, "usd2", "pct", 1, "abajo", "centro"),
    panel.tarjeta_simple(ronda, "Beneficio de la ronda", pc.SECCION_EERR, "Beneficio de la ronda", None, "miles", "pct", 1, "abajo", "centro"),
    panel.tarjeta_wacc(ronda, "abajo", "centro"),
    panel.tarjeta_simple(ronda, "Margen bruto", S, "Margen bruto", pc.SUB_INDICADORES, "pct", "pp", 1, "abajo", "der"),
]
tarjetas_abajo = [
    panel.tarjeta_simple(ronda, "ROCE", S, "Rentabilidad del capital empleado (ROCE)", pc.SUB_INDICADORES, "pct", "pp", 1, "arriba", "izq"),
    panel.tarjeta_simple(ronda, "ROE", S, "Rendimiento de los Fondos Propios (ROE)", pc.SUB_INDICADORES, "pct", "pp", 1, "arriba", "centro"),
    panel.tarjeta_simple(ronda, "Endeudamiento neto / patrimonio", S, "Endeudamiento neto/patrimonio (apalancamiento)", pc.SUB_INDICADORES, "pct", "pp", 0, "arriba", "der"),
]

pc.dibujar(panel, ronda, alto_css, tarjetas_arriba, tarjetas_abajo)