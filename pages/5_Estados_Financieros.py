import html as html_lib

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import sheets_io
import style

st.set_page_config(page_title="Estados financieros", layout="wide")
style.mostrar_logo()
st.title("📑 Estados financieros")

EMPRESA_PROPIA = "LAST1"
SECCION_EERR = "Cuenta de resultados, miles USD, Global"
SECCION_BALANCE = "Hoja de Balance, miles USD, Global"
SECCION_EFE = "Flujo de efectivo de casa matriz, miles USD"

COLOR_INGRESO = "#1DB954"
COLOR_COSTO = "#E3342F"
COLOR_EBITDA = "#2F6FED"

# Líneas de costo que van del Ingreso al EBITDA, en el orden del estado de resultados.
FILAS_COSTOS_EBITDA = [
    "Costos de fabricación interna",
    "Costos de características",
    "Costos de fabricación contratada",
    "Costos de transporte y aranceles",
    "I+D",
    "Promoción",
    "Administración",
]

# Cada fila de las tablas se describe como:
# (etiqueta mostrada, es_subtotal, metrica real en los datos, subseccion para
#  desambiguar (None si el nombre de la métrica ya es único), base de
#  análisis vertical: "activo" | "ppn" | None)

FILAS_EERR = [
    ("Ingresos por ventas", False, "Ingresos por ventas", None, None),
    ("Costos de fabricación interna", False, "Costos de fabricación interna", None, None),
    ("Costos de características", False, "Costos de características", None, None),
    ("Costos de fabricación contratada", False, "Costos de fabricación contratada", None, None),
    ("Costos de transporte y aranceles", False, "Costos de transporte y aranceles", None, None),
    ("I+D", False, "I+D", None, None),
    ("Promoción", False, "Promoción", None, None),
    ("Administración", False, "Administración", None, None),
    ("Costos y gastos totales", True, "Costos y gastos totales", None, None),
    ("Beneficio operativo antes de depreciación (EBITDA)", True, "Beneficio operativo antes de depreciación (EBITDA)", None, None),
    ("Depreciación de Activos Fijos", False, "Depreciación de Activos Fijos", None, None),
    ("Beneficio operativo (EBIT)", True, "Beneficio operativo (EBIT)", None, None),
    ("Gastos financieros netos", False, "Gastos financieros netos", None, None),
    ("Beneficio antes de impuestos", True, "Beneficio antes de impuestos", None, None),
    ("Impuesto sobre el beneficio", False, "Impuesto sobre el beneficio", None, None),
    ("Beneficio de la ronda", True, "Beneficio de la ronda", None, None),
]

FILAS_BALANCE = [
    ("Activo fijo", False, "Activo fijo", None, "activo"),
    ("Inventario", False, "Inventario", None, "activo"),
    ("Cuentas por Cobrar", False, "Cuentas por Cobrar", None, "activo"),
    ("Efectivo y equivalentes de efectivo", False, "Efectivo y equivalentes de efectivo", None, "activo"),
    ("Activos Totales", True, "Activos Totales", None, "activo"),
    ("Capital social", False, "Capital social", None, "ppn"),
    ("Capital adicional desembolsado", False, "Capital adicional desembolsado", None, "ppn"),
    ("Beneficio de la ronda", False, "Beneficio de la ronda", None, "ppn"),
    ("Ganancias acumuladas", False, "Ganancias acumuladas", None, "ppn"),
    ("Total patrimonio neto", True, "Total patrimonio neto", None, "ppn"),
    ("Deudas a largo plazo", False, "Deudas a largo plazo", None, "ppn"),
    ("Deudas a corto plazo (no planificadas)", False, "Deudas a corto plazo (no planificadas)", None, "ppn"),
    ("Cuentas por pagar", False, "Cuentas por pagar", None, "ppn"),
    ("Pasivos Totales", True, "Pasivos Totales", None, "ppn"),
    ("Total de patrimonio neto y pasivo de los accionistas", True, "Total de patrimonio neto y pasivo de los accionistas", None, "ppn"),
]

# La etiqueta "Total" se repite dos veces en el Excel (cierre de actividades
# operativas y cierre de actividades financieras) -> hace falta la
# subsección para saber a cuál de las dos nos referimos.
FILAS_EFE = [
    ("Beneficio operativo antes de depreciación (EBITDA)", False, "Beneficio operativo antes de depreciación (EBITDA)", None, None),
    ("Cambio en cuentas por cobrar (incr + / disminuir -)", False, "Cambio en cuentas por cobrar (incr + / disminuir -)", None, None),
    ("Variación en los stocks (aum - / dism +)", False, "Variación en los stocks (aum - / dism +)", None, None),
    ("Cambios en cuentas por pagar (incr+ / disminuir -)", False, "Cambios en cuentas por pagar (incr+ / disminuir -)", None, None),
    ("Gastos financieros netos (gastos - / ingresos +)", False, "Gastos financieros netos (gastos - / ingresos +)", None, None),
    ("Impuesto sobre el beneficio", False, "Impuesto sobre el beneficio", None, None),
    ("Total actividades operativas", True, "Total", "Efectivo proveniente de actividades operativas", None),
    ("Inversiones en fábricas (-) / desinversiones (+)", False, "Inversiones en fábricas (-) / desinversiones (+)", None, None),
    ("Flujo de efectivo antes de las actividades financieras", True, "Flujo de efectivo antes de las actividades financieras", None, None),
    ("Dividendos", False, "Dividendos", None, None),
    ("Recaudación de emisión de patrimonio neto y recompras", False, "Recaudación de emisión de patrimonio neto y recompras", None, None),
    ("Dividendos percibidos de las filiales", False, "Dividendos percibidos de las filiales", None, None),
    ("Cambio de deuda a largo plazo (incr+ / dism-)", False, "Cambio de deuda a largo plazo (incr+ / dism-)", None, None),
    ("Cambio en deuda a corto plazo (incr+ /dism - )", False, "Cambio en deuda a corto plazo (incr+ /dism - )", None, None),
    ("Cambio en préstamos internos", False, "Cambio en préstamos internos", None, None),
    ("Total actividades financieras", True, "Total", "Efectivo proveniente de actividades financieras", None),
    ("Cambios en efectivo y equivalentes de efectivo", True, "Cambios en efectivo y equivalentes de efectivo", None, None),
    ("Efectivo 1.1.", False, "Efectivo 1.1.", None, None),
    ("Efectivo 31.12.", True, "Efectivo 31.12.", None, None),
]

COMPONENTES_ACTIVO = [
    ("Activo fijo", "#1F3B57"),
    ("Inventario", "#3FA7A0"),
    ("Cuentas por Cobrar", "#8BC34A"),
    ("Efectivo y equivalentes de efectivo", "#4CAF50"),
]
COMPONENTES_PPN = [
    ("Total patrimonio neto", "#2F6FED"),
    ("Deudas a largo plazo", "#FF9800"),
    ("Deudas a corto plazo (no planificadas)", "#E53935"),
    ("Cuentas por pagar", "#FFC107"),
]

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


def _moneda(v) -> str:
    if v is None:
        return "—"
    signo = "-" if v < 0 else ""
    return f"{signo}${abs(v):,.0f}"


def _ronda_anterior_en_lista(ronda: int):
    """Busca la ronda inmediatamente anterior DENTRO de las rondas cargadas
    (no resta 1 a lo bruto, para no romperse si falta cargar alguna ronda
    intermedia)."""
    idx = rondas_disponibles.index(ronda)
    return rondas_disponibles[idx - 1] if idx > 0 else None


# ============================================================
# EBITDA DESAGREGADO
# ============================================================
st.header("EBITDA desagregado")

col1, col2 = st.columns(2)
with col1:
    opciones_ronda = {_etiqueta_ronda(r): r for r in rondas_disponibles}
    etiqueta_sel = st.selectbox(
        "Ronda", options=list(opciones_ronda.keys()), index=len(opciones_ronda) - 1, key="ronda_waterfall"
    )
    ronda_w = opciones_ronda[etiqueta_sel]
with col2:
    otras_empresas = [e for e in empresas_disponibles if e != EMPRESA_PROPIA]
    empresa_comparar = st.selectbox(
        "Comparar con", options=otras_empresas, index=0 if otras_empresas else None, key="empresa_comparar"
    )


def _armar_waterfall(empresa: str, ronda: int):
    ingresos = _valor(SECCION_EERR, "Ingresos por ventas", empresa, ronda)
    ebitda = _valor(SECCION_EERR, "Beneficio operativo antes de depreciación (EBITDA)", empresa, ronda)
    if ingresos is None or ebitda is None:
        return None

    labels = ["Ingresos<br>por ventas"]
    valores = [ingresos]
    hover = [f"Ingresos por ventas: {_moneda(ingresos)}"]

    for costo in FILAS_COSTOS_EBITDA:
        v = _valor(SECCION_EERR, costo, empresa, ronda) or 0
        etiqueta = costo if len(costo) <= 16 else costo.replace(" de ", "<br>de ", 1)
        labels.append(etiqueta)
        valores.append(-v)
        hover.append(f"{costo}: -{_moneda(v)}")

    labels.append("EBITDA")
    hover.append(f"EBITDA: {_moneda(ebitda)}")

    fig = go.Figure(
        go.Waterfall(
            x=labels,
            y=valores + [ebitda],
            measure=["relative"] * len(valores) + ["total"],
            hovertext=hover,
            hoverinfo="text",
            textposition="none",  # sin esto, Plotly repite las etiquetas DENTRO de cada barra
            increasing=dict(marker=dict(color=COLOR_INGRESO)),
            decreasing=dict(marker=dict(color=COLOR_COSTO)),
            totals=dict(marker=dict(color=COLOR_EBITDA)),
            connector=dict(line=dict(color="#BBBBBB", width=1, dash="dot")),
        )
    )
    fig.update_layout(
        height=430,
        margin=dict(t=10, b=90, l=55, r=20),
        yaxis=dict(title="USD"),
        showlegend=False,
        hoverlabel=style.HOVERLABEL_GRANDE,
    )
    return fig


colA, colB = st.columns(2)
with colA:
    st.markdown(f"**{EMPRESA_PROPIA}**")
    fig_a = _armar_waterfall(EMPRESA_PROPIA, ronda_w)
    if fig_a is not None:
        st.plotly_chart(fig_a, use_container_width=True)
    else:
        st.info(f"Sin datos para {EMPRESA_PROPIA} en esta ronda.")
with colB:
    if empresa_comparar:
        st.markdown(f"**{empresa_comparar}**")
        fig_b = _armar_waterfall(empresa_comparar, ronda_w)
        if fig_b is not None:
            st.plotly_chart(fig_b, use_container_width=True)
        else:
            st.info(f"Sin datos para {empresa_comparar} en esta ronda.")
    else:
        st.info("No hay otra empresa disponible para comparar.")

st.divider()

# ============================================================
# Estilos compartidos para las tablas con tooltip (CSS puro, sin JS)
# ============================================================
st.markdown(style.CSS_TOOLTIP_GRANDE, unsafe_allow_html=True)


def _celda_con_tooltip(texto_visible: str, lineas_tooltip: list) -> str:
    tooltip = "<br>".join(html_lib.escape(l) for l in lineas_tooltip)
    return f'<span class="tt">{html_lib.escape(texto_visible)}<span class="tttext">{tooltip}</span></span>'


def _tabla_html(seccion: str, filas: list, empresa: str) -> str:
    """Genera la tabla HTML (con scroll horizontal, columna 'Concepto' fija,
    y tooltip de variación % / análisis vertical) para EERR, Balance o EFE."""
    partes = ['<div class="tabla-ef-wrap"><table class="tabla-ef"><tr><th>Concepto</th>']
    for r in rondas_disponibles:
        partes.append(f"<th>{_etiqueta_ronda(r)}</th>")
    partes.append("</tr>")

    for etiqueta, es_subtotal, metrica, subseccion, base_vertical in filas:
        clase = ' class="subtotal"' if es_subtotal else ""
        partes.append(f"<tr{clase}><td>{html_lib.escape(etiqueta)}</td>")
        for r in rondas_disponibles:
            valor = _valor(seccion, metrica, empresa, r, subseccion)
            texto = _moneda(valor)
            tooltip_lineas = []

            if valor is None:
                tooltip_lineas.append("Sin datos")
            else:
                r_prev = _ronda_anterior_en_lista(r)
                if r_prev is None:
                    tooltip_lineas.append("Primer año disponible")
                else:
                    valor_prev = _valor(seccion, metrica, empresa, r_prev, subseccion)
                    if valor_prev in (None, 0):
                        tooltip_lineas.append("Variación vs. año anterior: N/D")
                    else:
                        variacion = (valor - valor_prev) / abs(valor_prev) * 100
                        signo = "+" if variacion >= 0 else ""
                        tooltip_lineas.append(f"Variación vs. {_etiqueta_ronda(r_prev)}: {signo}{variacion:.1f}%")

                if base_vertical is not None:
                    if base_vertical == "activo":
                        total_base = _valor(SECCION_BALANCE, "Activos Totales", empresa, r)
                        etiqueta_base = "% del Activo"
                    else:
                        total_base = _valor(
                            SECCION_BALANCE, "Total de patrimonio neto y pasivo de los accionistas", empresa, r
                        )
                        etiqueta_base = "% del Pasivo + Patrimonio Neto"
                    if total_base:
                        pct_vertical = valor / total_base * 100
                        tooltip_lineas.append(f"{etiqueta_base}: {pct_vertical:.1f}%")

            partes.append(f"<td>{_celda_con_tooltip(texto, tooltip_lineas)}</td>")
        partes.append("</tr>")
    partes.append("</table></div>")
    return "".join(partes)


# ============================================================
# ANÁLISIS EERR
# ============================================================
st.header(f"Análisis EERR — {EMPRESA_PROPIA} (Global)")
st.caption("Pasá el cursor sobre un valor para ver la variación % respecto al año anterior.")
st.markdown(_tabla_html(SECCION_EERR, FILAS_EERR, EMPRESA_PROPIA), unsafe_allow_html=True)

st.divider()

# ============================================================
# ANÁLISIS VERTICAL ESP (balance)
# ============================================================
st.header(f"Análisis vertical ESP — {EMPRESA_PROPIA} (Global)")
st.caption(
    "Pasá el cursor sobre un valor para ver la variación % respecto al año anterior "
    "y el análisis vertical (% del Activo o % del Pasivo + Patrimonio Neto)."
)
st.markdown(_tabla_html(SECCION_BALANCE, FILAS_BALANCE, EMPRESA_PROPIA), unsafe_allow_html=True)

st.divider()

# ============================================================
# HOJA DE BALANCE — estructura por equipo
# ============================================================
st.header("Hoja de Balance")
st.caption("Composición del Activo y del Pasivo + Patrimonio Neto de cada equipo, para la ronda seleccionada.")

opciones_ronda_bal = {_etiqueta_ronda(r): r for r in rondas_disponibles}
etiqueta_bal = st.selectbox(
    "Ronda", options=list(opciones_ronda_bal.keys()), index=len(opciones_ronda_bal) - 1, key="ronda_balance_chart"
)
ronda_bal = opciones_ronda_bal[etiqueta_bal]


def _armar_balance_chart(ronda: int) -> go.Figure:
    empresas = empresas_disponibles
    fig = go.Figure()

    acumulado_activo = {e: 0.0 for e in empresas}
    for nombre, color in COMPONENTES_ACTIVO:
        valores = [_valor(SECCION_BALANCE, nombre, e, ronda) or 0 for e in empresas]
        fig.add_trace(
            go.Bar(
                x=empresas,
                y=valores,
                name=nombre,
                marker_color=color,
                offsetgroup="activo",
                base=[acumulado_activo[e] for e in empresas],
                legendgroup="activo",
                # Hover explícito con el valor PROPIO de este rubro (no lo que
                # queda acumulado por el "base" al apilar los segmentos).
                hovertext=[f"<b>{e}</b><br>{nombre}: ${v:,.0f}k" for e, v in zip(empresas, valores)],
                hoverinfo="text",
            )
        )
        for e, v in zip(empresas, valores):
            acumulado_activo[e] += v

    acumulado_ppn = {e: 0.0 for e in empresas}
    for nombre, color in COMPONENTES_PPN:
        valores = [_valor(SECCION_BALANCE, nombre, e, ronda) or 0 for e in empresas]
        fig.add_trace(
            go.Bar(
                x=empresas,
                y=valores,
                name=nombre,
                marker_color=color,
                offsetgroup="ppn",
                base=[acumulado_ppn[e] for e in empresas],
                legendgroup="ppn",
                hovertext=[f"<b>{e}</b><br>{nombre}: ${v:,.0f}k" for e, v in zip(empresas, valores)],
                hoverinfo="text",
            )
        )
        for e, v in zip(empresas, valores):
            acumulado_ppn[e] += v

    fig.update_layout(
        barmode="group",
        height=480,
        # tickformat fijo (sin notación "k"/"M" automática de Plotly, que
        # cambiaba de unidad sola a medida que las barras crecían).
        yaxis=dict(title="Miles USD (k)", tickformat=",.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(t=60, b=40, l=60, r=20),
        hoverlabel=style.HOVERLABEL_GRANDE,
    )
    return fig


st.plotly_chart(_armar_balance_chart(ronda_bal), use_container_width=True)
st.caption("La barra izquierda de cada equipo es el Activo; la derecha, el Pasivo + Patrimonio Neto (ambas deberían sumar lo mismo).")

st.divider()

# ============================================================
# ANÁLISIS EFE (estado de flujo de efectivo)
# ============================================================
st.header(f"Análisis EFE — {EMPRESA_PROPIA} (Global)")
st.caption("Pasá el cursor sobre un valor para ver la variación % respecto al año anterior.")
st.markdown(_tabla_html(SECCION_EFE, FILAS_EFE, EMPRESA_PROPIA), unsafe_allow_html=True)