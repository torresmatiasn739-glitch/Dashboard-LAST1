"""Datos y visuales de la pestana Produccion (sin dependencias adicionales)."""

import base64
from dataclasses import dataclass
import html
import math

import pandas as pd


REGIONES = ("EE.UU.", "Asia")
TECS = ("Tec 1", "Tec 2", "Tec 3", "Tec 4")
COLORES = {"EE.UU.": "#2F6FED", "Asia": "#E3342F"}
SECCION = "Detalles de fabricación"
SUB_CAPACIDAD = "Capacidad empleada, %"
SUB_FABRICAS = "Número de fábricas — Ronda actual"
SUB_COSTOS = "Costo de producción interna por unidad, USD"


@dataclass(frozen=True)
class EstadoRegion:
    region: str
    utilizacion: float | None
    fabricas: float | None
    costos: dict[str, float | None]
    capacidad_cargada: bool
    costos_cargados: bool


def _numero(valor) -> float | None:
    """Un dato ausente o no finito nunca se convierte automaticamente en cero."""
    try:
        numero = float(valor)
    except (TypeError, ValueError, OverflowError):
        return None
    return numero if math.isfinite(numero) else None


def leer_region(df: pd.DataFrame, empresa: str, ronda: int, region: str) -> EstadoRegion:
    """Lee solo la empresa y la ronda elegidas; las plantas futuras no se suman."""
    if region not in REGIONES:
        raise ValueError(f"Region de produccion no reconocida: {region}")
    datos_ronda = df[df["ronda"] == ronda]
    datos = datos_ronda[datos_ronda["empresa"] == empresa]

    def valor(seccion: str, subseccion: str, metrica: str) -> float | None:
        filas = datos[
            (datos["seccion"] == seccion)
            & (datos["subseccion"] == subseccion)
            & (datos["metrica"] == metrica)
        ]
        if filas.empty:
            return None
        # Una fila repetida en el historico no debe duplicar la capacidad.
        return _numero(filas["valor_numerico"].iloc[0])

    fabricas = valor(SECCION, SUB_FABRICAS, region)
    if fabricas is None:
        # En el historico anterior, las filas vacias de tecnologias podian
        # dejar una seccion incorrecta (por ejemplo, "Tec 4"). La combinacion
        # Ronda actual + region es exclusiva de este bloque del Excel.
        anteriores = datos[
            (datos["subseccion"] == "Ronda actual") & (datos["metrica"] == region)
        ]
        unicos = pd.to_numeric(anteriores["valor_numerico"], errors="coerce").dropna().unique()
        if len(unicos) == 1:
            fabricas = _numero(unicos[0])

    sub_cap = f"{SUB_CAPACIDAD} — {region}"
    capacidad_cargada = bool(
        ((datos["seccion"] == SECCION) & (datos["subseccion"] == sub_cap)).any()
    )
    capacidades = [valor(SECCION, sub_cap, tec) for tec in TECS]
    capacidades = [v for v in capacidades if v is not None]
    disponible = valor(SECCION, sub_cap, "Capacidad Disponible")

    # Cada tecnologia ocupa una parte de la misma capacidad regional:
    # se SUMAN los porcentajes del Excel, no se promedian.
    if capacidades:
        utilizacion = math.fsum(capacidades)
    elif fabricas == 0:
        utilizacion = 0.0
    elif disponible is not None:
        utilizacion = 100.0 - disponible
    else:
        utilizacion = None

    # El extractor de costos ya existente guarda solo las celdas informadas.
    # Comprobar el bloque en toda la ronda evita tratar una tecnologia inactiva
    # de una empresa como una ronda que nunca se volvio a cargar.
    costos_cargados = bool(
        (
            (datos_ronda["seccion"] == "Informe de costos")
            & datos_ronda["subseccion"].fillna("").str.startswith(SUB_COSTOS + " — ")
        ).any()
    )
    costos = {
        tec: valor("Informe de costos", f"{SUB_COSTOS} — {region}", tec)
        for tec in TECS
    }
    return EstadoRegion(region, utilizacion, fabricas, costos, capacidad_cargada, costos_cargados)


def _h(texto) -> str:
    return html.escape(str(texto), quote=True).replace("$", "&#36;")


def _porcentaje(valor: float | None) -> str:
    return "N/D" if valor is None else f"{valor:,.1f}%"


def _cantidad(valor: float | None) -> str:
    if valor is None:
        return "N/D"
    return f"{valor:,.0f}" if float(valor).is_integer() else f"{valor:,.1f}"


def _fabrica_svg(utilizacion: float | None, color: str) -> str:
    """Silueta vectorial: el color sube desde la base y no tapa los contornos.

    El humo queda blanco; el nivel mide la altura del edificio y chimeneas.
    Se acota SOLO el dibujo a 0-100, conservando el dato real en el porcentaje.
    """
    if color not in COLORES.values():
        raise ValueError("Color no permitido para la fabrica")
    nivel = max(0.0, min(100.0, _numero(utilizacion) or 0.0))
    techo, base = 223.0, 545.0
    alto = (base - techo) * nivel / 100.0
    y = base - alto
    silueta = (
        "M18 545 L16 400 H53 L65 223 H93 L111 400 H123 "
        "L132 263 H160 L174 400 H212 V447 L318 403 L320 445 "
        "L406 409 V545 Z"
    )
    # La imagen se incrusta como SVG en un <img>, no como HTML SVG inline.
    # Asi el recorte conserva sus IDs y no depende del sanitizador de Streamlit.
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 45 425 515">'
        '<defs><clipPath id="interior-fabrica">'
        f'<path d="{silueta}"/></clipPath></defs>'
        '<g fill="white" stroke="#111111" stroke-width="3" stroke-linejoin="round">'
        '<path d="M139 106 C146 71 179 51 212 73 '
        'C249 53 298 76 293 125 C285 158 253 175 218 177 '
        'C190 191 161 206 136 193 C119 215 93 215 78 197 '
        'C61 175 76 145 102 141 C105 123 119 109 139 106 Z"/>'
        '<path d="M185 192 C188 174 202 161 220 160 '
        'C224 130 257 111 285 131 C309 115 338 123 355 146 '
        'C372 172 356 204 326 213 C323 245 281 268 248 242 '
        'C235 250 224 243 214 240 C195 264 165 256 158 238 '
        'C151 219 160 201 185 192 Z"/></g>'
        f'<path d="{silueta}" fill="white"/>'
        f'<rect x="0" y="{y:.4f}" width="425" height="{alto:.4f}" '
        f'fill="{color}" clip-path="url(#interior-fabrica)"/>'
        '<g stroke="#111111" stroke-width="5.5" fill="none" '
        'stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="{silueta}"/>'
        '<path d="M16 400 H212 M212 400 V545"/></g>'
        '<g stroke="#111111" stroke-width="3.2" fill="white" '
        'stroke-linejoin="round">'
        '<path d="M66 545 V470 H167 V545 Z"/>'
        '<path d="M235 464 L304 462 L305 514 H236 Z"/>'
        '<path d="M321 464 L390 463 L391 514 H321 Z"/></g>'
        '<path d="M115 470 V545 M18 545 H406" stroke="#111111" '
        'stroke-width="3.5" fill="none"/>'
        '</svg>'
    )


CSS_PRODUCCION = """
<style>
.produccion-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px; margin: 8px 0 16px; }
.produccion-card { background: #fff; color: #1B2A3A; border: 1px solid #cfd3d6; border-radius: 12px; padding: 20px 20px 22px; text-align: center; box-sizing: border-box; }
.produccion-region { font-size: 1.35rem; font-weight: 700; line-height: 1.4; margin-bottom: 6px; }
.produccion-region-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: var(--prod-color); margin-right: 9px; vertical-align: middle; }
.produccion-fabrica { position: relative; width: 100%; max-width: 480px; margin: 0 auto; border-radius: 8px; cursor: help; }
.produccion-fabrica:focus-visible { outline: 2px solid var(--prod-color); outline-offset: 3px; }
.produccion-fabrica img { display: block; width: 100%; height: 310px; object-fit: contain; margin: 0 auto; }
.produccion-porcentaje { color: var(--prod-color); font-size: clamp(2.1rem, 3.6vw, 2.8rem); font-weight: 750; line-height: 1.15; margin-top: 14px; font-variant-numeric: tabular-nums; }
.produccion-etiqueta { color: #526170; font-size: 0.93rem; margin-top: 4px; }
.produccion-estado { min-height: 1.4em; color: #6b7280; font-size: 0.82rem; line-height: 1.4; margin-top: 7px; }
.produccion-tip { visibility: hidden; opacity: 0; position: absolute; z-index: 100; bottom: 8px; left: 50%; transform: translateX(-50%); width: min(340px, calc(100% - 16px)); box-sizing: border-box; background: #222; color: #fff; border-radius: 9px; padding: 16px 18px; text-align: left; font-size: 1rem; line-height: 1.45; box-shadow: 0 5px 18px rgba(0,0,0,0.22); pointer-events: none; transition: opacity 0.12s; }
.produccion-fabrica:hover .produccion-tip, .produccion-fabrica:focus .produccion-tip, .produccion-fabrica:focus-within .produccion-tip { visibility: visible; opacity: 1; }
.produccion-tip-titulo { color: #fff; font-size: 1.04rem; font-weight: 700; margin-bottom: 9px; }
.produccion-tip-subtitulo { color: #e5e7eb; margin: 12px 0 6px; font-size: 0.93rem; }
.produccion-tip table { width: 100%; border-collapse: collapse; margin: 0; font-size: 0.96rem; color: #fff; }
.produccion-tip th, .produccion-tip td { border: 0; padding: 4px 0; background: transparent; text-align: right; font-variant-numeric: tabular-nums; }
.produccion-tip th { color: #cbd5e1; font-size: 0.82rem; border-bottom: 1px solid #555; }
.produccion-tip td:first-child, .produccion-tip th:first-child { text-align: left; }
.produccion-tip-nota { color: #cbd5e1; margin-top: 9px; font-size: 0.8rem; }
@media (max-width: 700px) {
  .produccion-grid { grid-template-columns: minmax(0, 1fr); gap: 16px; }
  .produccion-card { padding: 16px 12px 18px; }
  .produccion-fabrica img { height: 275px; }
  .produccion-tip { padding: 12px 14px; font-size: 0.9rem; }
  .produccion-tip-titulo { font-size: 0.95rem; margin-bottom: 6px; }
  .produccion-tip-subtitulo { font-size: 0.85rem; margin: 8px 0 4px; }
  .produccion-tip table { font-size: 0.88rem; }
  .produccion-tip th, .produccion-tip td { padding: 3px 0; }
  .produccion-tip-nota { font-size: 0.74rem; margin-top: 7px; }
}
</style>
"""


def _tarjeta(estado: EstadoRegion) -> str:
    color = COLORES[estado.region]
    porcentaje = _porcentaje(estado.utilizacion)
    svg = _fabrica_svg(estado.utilizacion, color)
    imagen = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    ident = "produccion-tooltip-eeuu" if estado.region == "EE.UU." else "produccion-tooltip-asia"

    if estado.fabricas == 0:
        nota = "Sin fábricas operativas en esta ronda"
    elif estado.utilizacion is None:
        nota = "Sin datos de capacidad para esta selección"
    elif estado.utilizacion < -1e-6 or estado.utilizacion > 100.0 + 1e-6:
        nota = "Capacidad informada fuera del rango 0–100%"
    else:
        nota = "Capacidad total de la región"

    filas = "".join(
        f'<tr><td>{_h(tec)}</td><td>'
        + (f'{estado.costos[tec]:,.2f}' if estado.costos.get(tec) is not None else "—")
        + '</td></tr>'
        for tec in TECS
    )
    texto_alt = f"Fábrica en {estado.region}. Capacidad utilizada: {porcentaje}."
    tooltip = (
        f'<div class="produccion-tip" role="tooltip" id="{ident}">'
        f'<div class="produccion-tip-titulo">{_h(estado.region)}</div>'
        f'<div>Fábricas en esta ronda: <strong>{_h(_cantidad(estado.fabricas))}</strong></div>'
        '<div class="produccion-tip-subtitulo">Costo de producción interna por unidad</div>'
        '<table aria-label="Costo interno por tecnología"><thead><tr>'
        '<th>Tecnología</th><th>USD/unidad</th></tr></thead>'
        f'<tbody>{filas}</tbody></table>'
        '<div class="produccion-tip-nota">— = sin costo informado para esa tecnología.</div>'
        '</div>'
    )
    return (
        f'<section class="produccion-card" style="--prod-color:{color};" '
        f'aria-label="Producción en {_h(estado.region)}">'
        '<div class="produccion-region"><span class="produccion-region-dot" aria-hidden="true"></span>'
        f'{_h(estado.region)}</div>'
        f'<div class="produccion-fabrica" tabindex="0" aria-describedby="{ident}" '
        f'aria-label="{_h(texto_alt)} Ver cantidad de fábricas y costos por tecnología.">'
        f'<img src="data:image/svg+xml;base64,{imagen}" alt="{_h(texto_alt)}"/>'
        f'{tooltip}</div>'
        f'<div class="produccion-porcentaje">{_h(porcentaje)}</div>'
        '<div class="produccion-etiqueta">Capacidad utilizada</div>'
        f'<div class="produccion-estado">{_h(nota)}</div>'
        '</section>'
    )


def grilla_produccion(estados: list[EstadoRegion]) -> str:
    return CSS_PRODUCCION + '<div class="produccion-grid">' + ''.join(_tarjeta(e) for e in estados) + '</div>'
