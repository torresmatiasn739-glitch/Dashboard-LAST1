"""
style.py
--------
Elementos de estética compartidos por todas las páginas: logo, paleta de
colores de marca (sacada del logo) y configuración de tooltips más grandes
(tanto los nativos de Plotly como los tooltips CSS hechos a mano en
Estados financieros). Cada página llama a `mostrar_logo()` justo después
de `st.set_page_config(...)`.

El fondo gris claro de toda la app se configura en `.streamlit/config.toml`
(tema nativo de Streamlit) en vez de CSS a mano acá, para que aplique de
forma consistente a widgets, sidebar, etc. sin tener que repetir estilos
en cada página.
"""

from pathlib import Path

import streamlit as st

LOGO_PATH = Path(__file__).parent / "assets" / "logo.png"

# Colores tomados directamente del logo
COLOR_AZUL = "#07468D"
COLOR_NARANJA = "#FF5900"
COLOR_FONDO = "#D6D9DB"
COLOR_TEXTO = "#1B2A3A"

# Tamaño de letra más grande para los tooltips nativos de Plotly (hover),
# reutilizado en todos los gráficos de todas las páginas.
HOVERLABEL_GRANDE = dict(
    font_size=16,
    font_family="inherit",
    bgcolor="white",
    bordercolor=COLOR_AZUL,
)

# CSS para los tooltips hechos a mano en Estados financieros (EERR / ESP / EFE).
CSS_TOOLTIP_GRANDE = """
<style>
.tabla-ef-wrap { overflow-x: auto; border: 1px solid #ccc; border-radius: 8px; margin-bottom: 1rem; background: white; }
.tabla-ef { border-collapse: collapse; font-size: 1rem; }
.tabla-ef th {
    background: #333; color: white; padding: 10px 16px; text-align: right;
    min-width: 140px; white-space: nowrap; position: sticky; top: 0;
}
.tabla-ef th:first-child { text-align: left; left: 0; z-index: 3; min-width: 260px; }
.tabla-ef td {
    padding: 8px 16px; text-align: right; border-bottom: 1px solid #e5e5e5; white-space: nowrap;
}
.tabla-ef td:first-child {
    text-align: left; position: sticky; left: 0; background: white; z-index: 1;
}
.tabla-ef tr.subtotal td { font-weight: 700; background: #eef1f9; }
.tabla-ef tr.subtotal td:first-child { background: #eef1f9; }
.tt { position: relative; cursor: default; border-bottom: 1px dotted #999; }
.tt .tttext {
    visibility: hidden; opacity: 0; transition: opacity 0.12s;
    position: absolute; bottom: 135%; right: 0; background: #222; color: #fff;
    padding: 10px 14px; border-radius: 6px; white-space: nowrap; font-size: 1rem;
    line-height: 1.5; z-index: 10; box-shadow: 0 2px 10px rgba(0,0,0,0.25);
}
.tt:hover .tttext { visibility: visible; opacity: 1; }
</style>
"""


# Sidebar un poco más angosta que la default de Streamlit, y en un gris
# más claro que el fondo general de la app (que es COLOR_FONDO, #D6D9DB).
COLOR_SIDEBAR = "#EAEDEF"
ANCHO_SIDEBAR_PX = 230

CSS_SIDEBAR = f"""
<style>
section[data-testid="stSidebar"] {{
    background-color: {COLOR_SIDEBAR};
    min-width: {ANCHO_SIDEBAR_PX}px !important;
    max-width: {ANCHO_SIDEBAR_PX}px !important;
}}
</style>
"""


# Paleta fija por empresa, para que el mismo equipo tenga siempre el mismo
# color en los gráficos que distinguen series por empresa (ej. burbujas de
# Marketing). LAST1 usa el naranja de marca para destacarse.
COLORES_EMPRESA = {
    "IMPUL": "#4C78A8",
    "JAPON": "#E45756",
    "KAIRO": "#54A24B",
    "KAIZE": "#9D7BBD",
    "KINET": "#17A2A2",
    "LAST1": COLOR_NARANJA,
    "TECNO": "#9C9C9C",
}
_PALETA_RESERVA = ["#4C78A8", "#E45756", "#54A24B", "#9D7BBD", "#17A2A2", "#F2B701", "#9C9C9C"]


def color_empresa(nombre: str, indice_reserva: int = 0) -> str:
    """Color fijo para una empresa conocida; si es una empresa no prevista,
    cae a una paleta de reserva cíclica en vez de romper."""
    if nombre in COLORES_EMPRESA:
        return COLORES_EMPRESA[nombre]
    return _PALETA_RESERVA[indice_reserva % len(_PALETA_RESERVA)]


# Fondo blanco para gráficos puntuales que lo piden (contraste contra el
# gris del fondo general de la app). Se mezcla dentro de fig.update_layout(...).
FONDO_BLANCO_GRAFICO = dict(plot_bgcolor="white", paper_bgcolor="white")

# Variante más oscura de la paleta por empresa, para gráficos de líneas
# sobre fondo blanco donde se necesita más contraste que los colores
# "de marca" (más saturados/claros) de COLORES_EMPRESA.
COLORES_EMPRESA_OSCURO = {
    "IMPUL": "#1F4E79",
    "JAPON": "#8B1A1A",
    "KAIRO": "#2E7D32",
    "KAIZE": "#5B2C83",
    "KINET": "#006064",
    "LAST1": "#CC4400",
    "TECNO": "#4A4A4A",
}
_PALETA_RESERVA_OSCURA = ["#1F4E79", "#8B1A1A", "#2E7D32", "#5B2C83", "#006064", "#B8860B", "#4A4A4A"]


def color_empresa_oscuro(nombre: str, indice_reserva: int = 0) -> str:
    if nombre in COLORES_EMPRESA_OSCURO:
        return COLORES_EMPRESA_OSCURO[nombre]
    return _PALETA_RESERVA_OSCURA[indice_reserva % len(_PALETA_RESERVA_OSCURA)]


def mostrar_logo(ancho: int = 320) -> None:
    """Aplica el estilo de la sidebar y muestra el logo arriba a la izquierda
    de la página actual."""
    st.markdown(CSS_SIDEBAR, unsafe_allow_html=True)
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=ancho)
    else:
        st.warning(f"No se encontró el logo en: `{LOGO_PATH}`. Revisá que exista la carpeta `assets/` con `logo.png` adentro, al mismo nivel que `app.py`.")