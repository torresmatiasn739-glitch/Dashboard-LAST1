"""
panel_comun.py
--------------
Lógica compartida por las pestañas "Panel de control" y "Tablero de control 2":
acceso a los datos de la empresa propia, tarjetas con tooltip, gráficos
(EBITDA desagregado, estructura patrimonial, market share), cálculo del FCF
y encabezado de la página. Cada página solo define QUÉ tarjetas muestra y en
qué orden; todo lo demás vive acá para no duplicarlo.
"""

import html as html_lib

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import style

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

# Estado de flujo de efectivo por región (EE.UU. = casa matriz)
SECCION_EFE = {
    "EE.UU.": "Flujo de efectivo de casa matriz, miles USD",
    "Asia": "Estado de flujo de efectivo, miles USD, Asia",
    "Europa": "Estado de flujo de efectivo, miles USD, Europa",
}
SUB_EFE_OPERATIVAS = "Efectivo proveniente de actividades operativas"

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

# (nombre real en los datos, etiqueta corta, color, color del texto)
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

# Alto de los gráficos: lo define el navegador con CSS (100vh - ALTO_FIJO_PX), así se adapta
# a cualquier pantalla. ALTO_FIJO_PX es todo lo que NO son gráficos (logo/título, filas de
# tarjetas y separaciones). Si aparece scroll, subilo unos px. El ⚙️ permite un alto manual.
ALTO_GRAFICOS_DEFAULT = 460  # solo para el modo manual
ALTO_FIJO_PX = 290
ALTO_MIN, ALTO_MAX = 280, 900
ALTO_TARJETA = 72

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

NB = "\u00a0"  # espacio de no separación (para alinear las tablas de los hover)
HOVER = dict(style.HOVERLABEL_GRANDE, font_color=style.COLOR_TEXTO, align="left")


# ------------------------------------------------------------------
# Formato
# ------------------------------------------------------------------
def etiqueta_ronda(r: int) -> str:
    return "Año 0 (inicial)" if r == 0 else f"Año {r}"


def _h(texto) -> str:
    """Escapa HTML y neutraliza '$' (st.markdown lo interpreta como LaTeX)."""
    return html_lib.escape(str(texto)).replace("$", "&#36;")


def fmt(v, tipo: str) -> str:
    if v is None:
        return "—"
    if tipo == "pct":
        return f"{v:,.1f}%"
    if tipo == "pct2":
        return f"{v:,.2f}%"
    if tipo == "usd2":
        return f"${v:,.2f}"
    if tipo == "miles":
        return f"{'-' if v < 0 else ''}${abs(v):,.0f}k"
    return f"{v:,.2f}"


def _tabla_hover(columnas: list[str], filas: list[tuple[str, list[str]]], ancho_etiqueta=7, ancho_col=10) -> str:
    """Tabla alineada para un hover de Plotly (texto monoespaciado con espacios de no separación)."""

    def _linea(c0: str, celdas: list[str]) -> str:
        txt = c0.ljust(ancho_etiqueta) + "".join(c.rjust(ancho_col) for c in celdas)
        return '<span style="font-family:monospace">' + txt.replace(" ", NB) + "</span>"

    return "<br>".join([_linea("", columnas)] + [_linea(e, c) for e, c in filas])


# ------------------------------------------------------------------
# Datos de la empresa propia
# ------------------------------------------------------------------
class Panel:
    def __init__(self, df: pd.DataFrame, empresa: str = EMPRESA_PROPIA):
        self.df = df
        self.empresa = empresa
        self.rondas = sorted(df["ronda"].dropna().unique().tolist())

        # Índice en memoria de la empresa propia: (sección, subsección, métrica, ronda) -> (numérico, raw).
        # La clave con subsección None guarda la primera coincidencia (igual que filtrar sin subsección).
        self._idx = {}
        dfp = df[df["empresa"] == empresa]
        for sec, sub, met, r, vn, vr in zip(
            dfp["seccion"], dfp["subseccion"], dfp["metrica"], dfp["ronda"], dfp["valor_numerico"], dfp["valor_raw"]
        ):
            if pd.isna(r):
                continue
            sub = "" if pd.isna(sub) else sub
            val = (None if pd.isna(vn) else float(vn), None if pd.isna(vr) else str(vr).strip())
            self._idx.setdefault((sec, sub, met, int(r)), val)
            self._idx.setdefault((sec, None, met, int(r)), val)
        self._costo_unitario_cargado = {}

    # --- acceso ---
    def valor(self, seccion, metrica, ronda, subseccion=None):
        if ronda is None:
            return None
        hit = self._idx.get((seccion, subseccion, metrica, int(ronda)))
        return hit[0] if hit else None

    def texto(self, seccion, metrica, ronda, subseccion=None):
        if ronda is None:
            return None
        hit = self._idx.get((seccion, subseccion, metrica, int(ronda)))
        return hit[1] if hit and hit[1] else None

    def existe(self, seccion, metrica, ronda, subseccion=None) -> bool:
        return ronda is not None and (seccion, subseccion, metrica, int(ronda)) in self._idx

    def ronda_anterior(self, ronda: int):
        """Ronda inmediatamente anterior DENTRO de las cargadas (no resta 1 a lo bruto)."""
        idx = self.rondas.index(ronda)
        return self.rondas[idx - 1] if idx > 0 else None

    # --------------------------------------------------------------
    # Tarjetas con tooltip
    # --------------------------------------------------------------
    def _linea_variacion(self, ronda, v, previo, tipo: str, polaridad: int, formato: str) -> list[str]:
        """Líneas HTML del tooltip: variación vs. ronda anterior.
        tipo: 'pp' (puntos porcentuales) | 'pct' (variación %). polaridad: +1 subir es bueno, -1 malo, 0 neutro."""
        r_prev = self.ronda_anterior(ronda)
        if v is None:
            return ["Sin datos"]
        if r_prev is None:
            return ["Primer año disponible"]
        et_prev = etiqueta_ronda(r_prev)
        if previo is None or (tipo == "pct" and previo == 0):
            return [f"Variación vs. {_h(et_prev)}: N/D"]
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
            f'<span style="color:{color};font-weight:700;">{flecha} {txt}</span> vs. {_h(et_prev)}',
            f'<span class="sub">{_h(et_prev)}: {_h(fmt(previo, formato))}</span>',
        ]

    @staticmethod
    def _tarjeta(etiqueta, valor_txt, lineas, posicion, alineacion) -> str:
        return (
            f'<div class="kpi {posicion} {alineacion}"><div class="k-et">{_h(etiqueta)}</div>'
            f'<div class="k-val">{_h(valor_txt)}</div><div class="k-tip">{"<br>".join(lineas)}</div></div>'
        )

    def tarjeta_simple(self, ronda, etiqueta, seccion, metrica, subseccion, formato, tipo, polaridad, posicion, alineacion):
        v = self.valor(seccion, metrica, ronda, subseccion)
        previo = self.valor(seccion, metrica, self.ronda_anterior(ronda), subseccion)
        return self._tarjeta(
            etiqueta, fmt(v, formato), self._linea_variacion(ronda, v, previo, tipo, polaridad, formato), posicion, alineacion
        )

    def tarjeta_wacc(self, ronda, posicion, alineacion):
        r_prev = self.ronda_anterior(ronda)
        v = self.valor(SECCION_VALUACION, "WACC, %", ronda, SUB_DCF)
        previo = self.valor(SECCION_VALUACION, "WACC, %", r_prev, SUB_DCF)
        lineas = self._linea_variacion(ronda, v, previo, "pp", -1, "pct2")

        def _extra(nombre, metrica, formato, es_pp):
            x = self.valor(SECCION_VALUACION, metrica, ronda, SUB_DCF)
            if x is None:
                return None
            xp = self.valor(SECCION_VALUACION, metrica, r_prev, SUB_DCF)
            resto = ""
            if xp is not None:
                resto = f' <span class="sub">({x - xp:+.2f}{" p.p." if es_pp else ""} vs. {_h(etiqueta_ronda(r_prev))})</span>'
            return f"{nombre}: <b>{_h(fmt(x, formato))}</b>{resto}"

        lineas.append("&nbsp;")
        for linea in (
            _extra("Beta", "Beta", "num2", False),
            _extra("Ke (rend. esperado del patrimonio)", "Rendimiento esperado del patrimonio, %", "pct2", True),
        ):
            if linea:
                lineas.append(linea)

        def _rating(r):
            return self.texto(SECCION_RATIOS, "Calificación crediticia", r, SUB_INDICADORES) or self.texto(
                SECCION_VALUACION, "Calificación crediticia", r
            )

        rating = _rating(ronda)
        if rating:
            rating_prev = _rating(r_prev) if r_prev is not None else None
            if rating_prev is None:
                nota = ""
            elif rating_prev == rating:
                nota = ' <span class="sub">(sin cambios)</span>'
            else:
                nota = f' <span class="sub">(antes: {_h(rating_prev)})</span>'
            lineas.append(f"Calificación crediticia: <b>{_h(rating)}</b>{nota}")
        return self._tarjeta("WACC", fmt(v, "pct2"), lineas, posicion, alineacion)

    def tarjeta_fcf(self, ronda, posicion, alineacion):
        d = self.fcf(ronda)
        if d is None:
            return self._tarjeta("FCF (flujo de caja libre)", "—", ["Sin datos de flujo de efectivo para esta ronda"], posicion, alineacion)
        d_prev = self.fcf(self.ronda_anterior(ronda))
        lineas = self._linea_variacion(ronda, d["fcf"], d_prev["fcf"] if d_prev else None, "pct", 1, "miles")
        lineas += [
            "&nbsp;",
            f"NOPAT = EBIT × (1 − t): <b>{_h(fmt(d['nopat'], 'miles'))}</b> <span class=\"sub\">(t = {d['tasa'] * 100:.1f}%)</span>",
            f"(+) Depreciación: <b>{_h(fmt(d['da'], 'miles'))}</b>",
            f"(−) Capex: <b>{_h(fmt(d['capex'], 'miles'))}</b>",
            f"(−) Δ Capital de trabajo: <b>{_h(fmt(d['dkt'], 'miles'))}</b>",
            '<span class="sub">Detalle por año: botón 🧮 de arriba</span>',
        ]
        return self._tarjeta("FCF (flujo de caja libre)", fmt(d["fcf"], "miles"), lineas, posicion, alineacion)

    # --------------------------------------------------------------
    # FCF = EBIT × (1 − t) + D&A − Capex − ΔCapital de trabajo
    # --------------------------------------------------------------
    def fcf(self, ronda):
        """Devuelve un dict con todos los valores usados (miles USD) o None si faltan datos.
        - t: tasa efectiva global = Impuesto sobre el beneficio / Beneficio antes de impuestos
          (0% si el BAI es <= 0, porque no hay una tasa definida).
        - Capex y ΔKT salen del estado de flujo de efectivo de las 3 regiones (EE.UU. = casa matriz).
          Las líneas del EFE vienen con signo de caja; acá se pasan a 'aumento = +'.
        """
        if ronda is None:
            return None
        ebit = self.valor(SECCION_EERR, "Beneficio operativo (EBIT)", ronda)
        bai = self.valor(SECCION_EERR, "Beneficio antes de impuestos", ronda)
        imp = self.valor(SECCION_EERR, "Impuesto sobre el beneficio", ronda)
        da = self.valor(SECCION_EERR, "Depreciación de Activos Fijos", ronda)
        fin = self.valor(SECCION_EERR, "Gastos financieros netos", ronda)
        if None in (ebit, bai, imp, da):
            return None
        # sin estado de flujo de efectivo (ej. situación inicial) no se puede calcular
        if not any(self.existe(SECCION_EFE[r], "Efectivo 31.12.", ronda) for r in REGIONES):
            return None

        def suma_efe(metrica, subseccion=None):
            return sum(self.valor(SECCION_EFE[r], metrica, ronda, subseccion) or 0.0 for r in REGIONES)

        cf_cxc = suma_efe("Cambio en cuentas por cobrar (incr + / disminuir -)")
        cf_stock = suma_efe("Variación en los stocks (aum - / dism +)")
        cf_cxp = suma_efe("Cambios en cuentas por pagar (incr+ / disminuir -)")
        cf_inv = suma_efe("Inversiones en fábricas (-) / desinversiones (+)")
        cf_oper = suma_efe("Total", SUB_EFE_OPERATIVAS)

        tasa = imp / bai if bai > 0 else 0.0
        nopat = ebit * (1 - tasa)
        capex = -cf_inv
        d_cxc, d_inv, d_cxp = -cf_cxc, -cf_stock, cf_cxp
        dkt = d_cxc + d_inv - d_cxp
        fcf = nopat + da - capex - dkt

        # Control 1: efectivo operativo (EFE) - capex + gastos financieros netos x (1 - t)  == FCF
        control_efe = cf_oper - capex + (fin or 0.0) * (1 - tasa)

        # Control 2 y 3: lo mismo, pero desde los balances Global (necesita la ronda anterior cargada)
        r_prev = self.ronda_anterior(ronda)
        dkt_bal = capex_bal = None
        if r_prev is not None:

            def kt(r):
                partes = [
                    self.valor(SECCION_BALANCE, "Inventario", r),
                    self.valor(SECCION_BALANCE, "Cuentas por Cobrar", r),
                    self.valor(SECCION_BALANCE, "Cuentas por pagar", r),
                ]
                return None if None in partes else partes[0] + partes[1] - partes[2]

            kt_a, kt_p = kt(ronda), kt(r_prev)
            if kt_a is not None and kt_p is not None:
                dkt_bal = kt_a - kt_p
            af_a = self.valor(SECCION_BALANCE, "Activo fijo", ronda)
            af_p = self.valor(SECCION_BALANCE, "Activo fijo", r_prev)
            if af_a is not None and af_p is not None:
                capex_bal = af_a - af_p + da

        dif_efe = fcf - control_efe
        if abs(dif_efe) < 0.5:  # ruido de redondeo de punto flotante
            dif_efe = 0.0

        return dict(
            ebit=ebit, bai=bai, imp=imp, tasa=tasa, tasa_pct=tasa * 100, nopat=nopat, da=da, capex=capex,
            d_cxc=d_cxc, d_inv=d_inv, d_cxp=d_cxp, dkt=dkt, fcf=fcf,
            cf_oper=cf_oper, fin=fin or 0.0, control_efe=control_efe, dif_efe=dif_efe,
            dkt_bal=dkt_bal, capex_bal=capex_bal,
        )

    def tabla_fcf(self) -> pd.DataFrame:
        """Tabla Concepto x Año con todos los valores usados en el FCF, más la fuente en el Excel."""
        M, P = "miles", "pct"
        filas = [
            ("EBIT", "ebit", M, "Cuenta de resultados Global › Beneficio operativo (EBIT)"),
            ("Beneficio antes de impuestos (BAI)", "bai", M, "Cuenta de resultados Global › Beneficio antes de impuestos"),
            ("Impuesto sobre el beneficio", "imp", M, "Cuenta de resultados Global › Impuesto sobre el beneficio"),
            ("Tasa impositiva efectiva t = Impuesto / BAI", "tasa_pct", P, "Calculado (0% si BAI ≤ 0)"),
            ("NOPAT = EBIT × (1 − t)", "nopat", M, "Calculado"),
            ("(+) Depreciación de activos fijos", "da", M, "Cuenta de resultados Global › Depreciación de Activos Fijos"),
            ("(−) Capex (inversiones en fábricas, neto)", "capex", M, "EFE EE.UU. + Asia + Europa › Inversiones en fábricas (signo invertido)"),
            ("     Δ Cuentas por cobrar (aumento +)", "d_cxc", M, "EFE 3 regiones › Cambio en cuentas por cobrar (signo invertido)"),
            ("     Δ Inventario (aumento +)", "d_inv", M, "EFE 3 regiones › Variación en los stocks (signo invertido)"),
            ("     Δ Cuentas por pagar (aumento +)", "d_cxp", M, "EFE 3 regiones › Cambios en cuentas por pagar"),
            ("(−) Δ Capital de trabajo = ΔCxC + ΔInv − ΔCxP", "dkt", M, "Calculado"),
            ("FCF = NOPAT + Deprec. − Capex − ΔKT", "fcf", M, "Calculado"),
            ("Control 1: efectivo operativo − capex + gastos fin. × (1 − t)", "control_efe", M, "EFE 3 regiones › Total actividades operativas (debe ser = FCF)"),
            ("     Diferencia FCF − Control 1", "dif_efe", M, "Debe ser 0"),
            ("Control 2: Δ KT según balances (Inv + CxC − CxP)", "dkt_bal", M, "Balance Global año actual − año anterior (≈ ΔKT)"),
            ("Control 3: Capex según balances (Δ Activo fijo + deprec.)", "capex_bal", M, "Balance Global año actual − año anterior + depreciación (≈ Capex)"),
        ]
        cols = {}
        for r in self.rondas:
            d = self.fcf(r)
            cols[etiqueta_ronda(r)] = [fmt(d[k], f) if d and d.get(k) is not None else "—" for _, k, f, _ in filas]
        out = pd.DataFrame(cols, index=[f[0] for f in filas])
        out["Fuente en el Excel"] = [f[3] for f in filas]
        return out

    # --------------------------------------------------------------
    # Datos para los hover especiales
    # --------------------------------------------------------------
    def _hover_costo_unitario(self, ronda) -> str:
        """Costo unitario de fabricación interna (USD/unidad) por tecnología y región."""
        datos = {
            (t, r): self.valor("Informe de costos", t, ronda, f"Costo de producción interna por unidad, USD — {r}")
            for t in TECS
            for r in REGIONES
        }
        cols = [r for r in REGIONES if any(datos[(t, r)] is not None for t in TECS)]
        filas = [
            (t, [fmt(datos[(t, r)], "usd2") for r in cols]) for t in TECS if any(datos[(t, r)] is not None for r in cols)
        ]
        if filas:
            return "Costo unitario de fabricación (USD/u.)<br>" + _tabla_hover(cols, filas)
        # ¿el bloque existe para esta ronda en los datos cargados? (si no, hay que volver a subir el Excel)
        if ronda not in self._costo_unitario_cargado:
            d = self.df
            self._costo_unitario_cargado[ronda] = bool(
                (
                    (d["ronda"] == ronda)
                    & d["subseccion"].astype(str).str.startswith("Costo de producción interna por unidad")
                ).any()
            )
        if self._costo_unitario_cargado[ronda]:
            return "Costo unitario de fabricación: sin producción interna"
        return "Costo unitario: dato no cargado<br>(volvé a subir esta ronda en «Cargar datos»)"

    def _hover_caracteristicas(self, ronda) -> str:
        """Cantidad de características ofrecidas por región y tecnología."""
        datos = {
            (t, r): self.valor(f"Informe de mercado, {r}", "Cantidad de características ofrecidas", ronda, t)
            for t in TECS
            for r in REGIONES
        }
        filas = [
            (t, [f"{datos[(t, r)]:.0f}" if datos[(t, r)] is not None else "—" for r in REGIONES])
            for t in TECS
            if any(datos[(t, r)] is not None for r in REGIONES)
        ]
        if not filas:
            return "Características ofrecidas: sin datos"
        return "Características ofrecidas por región<br>" + _tabla_hover(REGIONES, filas)

    def _hover_inventario(self, ronda) -> str:
        """Unidades en stock por tecnología (suma de las regiones donde se mantiene inventario).
        Tabla angosta a propósito: el gráfico de estructura patrimonial es chico y el hover se cortaría."""
        por_tec = {}
        for t in TECS:
            total = 0.0
            for r in REGIONES:
                v = self.valor("Detalles de fabricación", t, ronda, f"Inventario, miles unidades — {r}")
                total += (v or 0.0) * 1000  # el simulador reporta miles de unidades
            if total > 0.5:
                por_tec[t] = total
        if not por_tec:
            return "Unidades en stock: ninguna"
        filas = [(t, [f"{u:,.0f}"]) for t, u in por_tec.items()]
        if len(filas) > 1:
            filas.append(("Total", [f"{sum(por_tec.values()):,.0f}"]))
        return "Unidades en stock por tecnología<br>" + _tabla_hover(["Unidades"], filas, ancho_col=11)

    # --------------------------------------------------------------
    # Gráficos
    # --------------------------------------------------------------
    def fig_ebitda(self, ronda):
        ingresos = self.valor(SECCION_EERR, "Ingresos por ventas", ronda)
        ebitda = self.valor(SECCION_EERR, "Beneficio operativo antes de depreciación (EBITDA)", ronda)
        if ingresos is None or ebitda is None:
            return None

        # El eje va en millones de USD (los datos vienen en miles); el hover muestra el valor exacto en miles.
        etiquetas, valores = ["Ingresos"], [ingresos / 1000]
        hover = [f"<b>Ingresos por ventas: ${ingresos:,.0f}k</b>"]
        for nombre, corta in COSTOS_EBITDA:
            v = self.valor(SECCION_EERR, nombre, ronda) or 0
            etiquetas.append(corta)
            valores.append(-v / 1000)
            texto = f"<b>{nombre}: -${v:,.0f}k</b>"
            if nombre == "Costos de fabricación interna":
                texto += "<br>" + self._hover_costo_unitario(ronda)
            elif nombre == "Costos de características":
                texto += "<br>" + self._hover_caracteristicas(ronda)
            hover.append(texto)
        etiquetas.append("EBITDA")
        hover.append(f"<b>EBITDA: {'-' if ebitda < 0 else ''}${abs(ebitda):,.0f}k</b>")

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
            hoverlabel=HOVER,
            **style.FONDO_BLANCO_GRAFICO,
        )
        return fig

    def fig_estructura(self, ronda):
        barras = [("Activo", COMPONENTES_ACTIVO), ("Pasivo + PN", COMPONENTES_PPN)]
        totales = {cat: sum(self.valor(SECCION_BALANCE, n, ronda) or 0 for n, *_ in comps) for cat, comps in barras}
        if not any(totales.values()):
            return None

        fig = go.Figure()
        for cat, comps in barras:
            total = totales[cat]
            for nombre, corta, color, color_texto in comps:
                v = self.valor(SECCION_BALANCE, nombre, ronda) or 0
                pct = v / total * 100 if total else 0
                hover = f"<b>{nombre}</b><br>${v:,.0f}k ({pct:.1f}% de {cat})"
                if nombre == "Inventario":
                    hover += "<br>" + self._hover_inventario(ronda)
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
                        hovertext=[hover],
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
            hoverlabel=HOVER,
            **style.FONDO_BLANCO_GRAFICO,
        )
        return fig

    def fig_market_share(self, ronda):
        # Cuota calculada desde unidades vendidas (igual que la pestaña Demanda): las filas
        # "cuotas de mercado, %" del Excel vienen normalizadas por tecnología, no por empresa.
        unidades = {}  # (empresa, región) -> unidades
        for region in REGIONES:
            sub = self.df[
                (self.df["ronda"] == ronda)
                & (self.df["seccion"] == f"Informe de mercado, {region}")
                & (self.df["metrica"] == "Ventas, miles unidades")
                & (self.df["subseccion"].isin(TECS))
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
                pull=[0.07 if e == self.empresa else 0 for e in empresas],
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
            hoverlabel=HOVER,
            **style.FONDO_BLANCO_GRAFICO,
        )
        return fig


# ------------------------------------------------------------------
# Diálogo con el cálculo del FCF año por año
# ------------------------------------------------------------------
@st.dialog("Cálculo del FCF año por año (miles USD)", width="large")
def _dialogo_fcf(panel: Panel):
    st.caption(
        "FCF = EBIT × (1 − t) + Depreciación − Capex − Δ Capital de trabajo. "
        "Capex y ΔKT se suman sobre las 3 regiones (EE.UU. = casa matriz). "
        "Los controles 1, 2 y 3 sirven para validar el cálculo."
    )
    tabla = panel.tabla_fcf()
    negrita = ["NOPAT = EBIT × (1 − t)", "FCF = NOPAT + Deprec. − Capex − ΔKT"]
    st.dataframe(
        tabla.style.apply(lambda fila: ["font-weight: 700" if fila.name in negrita else "" for _ in fila], axis=1),
        use_container_width=True,
        height=min(35 * (len(tabla) + 1) + 3, 620),
    )


# ------------------------------------------------------------------
# Encabezado y disposición (iguales en las dos pestañas)
# ------------------------------------------------------------------
def encabezado(panel: Panel, titulo: str, prefijo: str, con_boton_fcf: bool = False):
    """Logo | título | ronda | (🧮 FCF) | ⚙️. Devuelve (ronda elegida, alto CSS de los gráficos)."""
    anchos = [1.1, 3.0, 1.5, 0.9, 0.35] if con_boton_fcf else [1.1, 3.9, 1.5, 0.35]
    cols = st.columns(anchos, vertical_alignment="center")
    c_logo, c_tit, c_ronda, c_cfg = cols[0], cols[1], cols[2], cols[-1]

    with c_logo:
        style.mostrar_logo(ancho=130)
    with c_tit:
        st.markdown(
            f'<div style="font-size:1.7rem;font-weight:700;color:{style.COLOR_TEXTO};">{_h(titulo)} — {_h(panel.empresa)}</div>',
            unsafe_allow_html=True,
        )
    with c_ronda:
        opciones = {etiqueta_ronda(r): r for r in panel.rondas}
        sel = st.selectbox(
            "Ronda", options=list(opciones.keys()), index=len(opciones) - 1,
            key=f"{prefijo}_ronda", label_visibility="collapsed",
        )
        ronda = opciones[sel]
    if con_boton_fcf:
        with cols[3]:
            if st.button("🧮 FCF", key=f"{prefijo}_btn_fcf", help="Ver cómo se calcula el FCF año por año"):
                _dialogo_fcf(panel)
    with c_cfg:
        with st.popover("⚙️"):
            auto = st.checkbox(
                "Ajustar los gráficos al alto de la ventana", value=True, key=f"{prefijo}_auto",
                help="Desmarcalo para fijar un alto manual en px.",
            )
            alto_manual = st.slider(
                "Alto de los gráficos (px)", min_value=ALTO_MIN, max_value=ALTO_MAX, value=ALTO_GRAFICOS_DEFAULT,
                step=20, key=f"{prefijo}_alto", disabled=auto,
            )
    alto_css = (
        f"clamp({ALTO_MIN}px, calc(100vh - {ALTO_FIJO_PX}px), {ALTO_MAX}px)" if auto else f"{alto_manual}px"
    )
    return ronda, alto_css


def _mostrar(fig, vacio: str, key: str):
    if fig is None:
        st.info(vacio)
    else:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=key)


def dibujar(panel: Panel, ronda: int, alto_css: str, tarjetas_arriba: list[str], tarjetas_abajo: list[str]):
    """Fila de tarjetas | EBITDA + estructura + tarjetas de abajo | torta de market share."""
    # El CSS va pegado a la primera fila de tarjetas para no agregar un elemento vacío (y su espacio) a la página.
    st.markdown(
        CSS_PANEL.replace("ALTO_G_VALOR", alto_css) + '<div class="kpi-grid g5">' + "".join(tarjetas_arriba) + "</div>",
        unsafe_allow_html=True,
    )
    col_izq, col_der = st.columns([3, 2])
    with col_izq:
        c_eb, c_bal = st.columns([2, 1])
        with c_eb:
            _mostrar(panel.fig_ebitda(ronda), f"Sin datos de EBITDA para {panel.empresa} en esta ronda.", "fig_ebitda")
        with c_bal:
            _mostrar(panel.fig_estructura(ronda), f"Sin datos de balance para {panel.empresa} en esta ronda.", "fig_estructura")
        st.markdown('<div class="kpi-grid g3">' + "".join(tarjetas_abajo) + "</div>", unsafe_allow_html=True)
    with col_der:
        _mostrar(panel.fig_market_share(ronda), "No hay ventas registradas en esta ronda.", "fig_market_share")