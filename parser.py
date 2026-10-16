"""
parser.py
---------
Convierte el Excel crudo que exporta el simulador (una sola hoja "Results"
con decenas de bloques temáticos apilados) a una tabla "tidy" (long format):

    ronda | seccion | subseccion | metrica | empresa | valor_raw | valor_numerico

Esta tabla tidy es la que después se guarda en Google Sheets y la que leen
todas las pestañas del dashboard. Mantener este formato único evita tener
que escribir un parser distinto por cada pestaña: a medida que agreguemos
pestañas nuevas, simplemente filtramos esta misma tabla por "seccion".

Lógica de detección de bloques (basada en cómo viene el Excel real):
- Una fila "título de sección" tiene texto en la primera columna y el resto
  vacío, Y la primera fila no vacía que le sigue es un encabezado de
  empresas (fila con la primera columna vacía y 2+ nombres de empresa en
  el resto). Ej: "Ratios e indicadores financieros clave".
- Una fila "título de subsección" es igual (texto + resto vacío) pero no
  está seguida de un encabezado de empresas, sino directamente de filas
  de datos. Ej: "Ratios", "Indicadores Financieros Claves, %".
- Una fila de datos tiene una etiqueta en la primera columna y un valor
  por empresa en el resto.

Nota honesta: este heurístico cubre bien bloques de dos niveles (sección >
subsección > métrica), que es el caso de "Ratios e indicadores financieros
clave" y la mayoría de los bloques del archivo. Hay un puñado de bloques
más anidados (ej. "Desglose de margen por tec") donde esta lógica simple
puede agrupar mal los niveles. Cuando lleguemos a esas pestañas, ajustamos
el parser puntualmente para ese bloque — no hace falta resolverlo ahora.
"""

import re
import pandas as pd

SHEET_NAME = "Results"


def extraer_ronda_de_nombre(filename: str) -> int | None:
    """Busca un patrón tipo 'r01', 'r2', etc. en el nombre del archivo."""
    match = re.search(r"r(\d+)", filename, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _is_title_row(row: pd.Series) -> bool:
    c0 = row.iloc[0]
    rest = row.iloc[1:]
    return isinstance(c0, str) and rest.isna().all()


def _is_company_header_row(row: pd.Series) -> bool:
    c0 = row.iloc[0]
    if not pd.isna(c0):
        return False
    rest = row.iloc[1:]
    vals = rest.dropna()
    if len(vals) < 2:
        return False
    return all(isinstance(v, str) for v in vals)


def _find_preceding_companies(df: pd.DataFrame, idx: int) -> list | None:
    """Busca hacia atrás desde `idx` el encabezado de empresas más cercano.
    Lo usamos para bloques que no repiten el encabezado justo antes."""
    for i in range(idx, -1, -1):
        if _is_company_header_row(df.iloc[i]):
            return df.iloc[i, 1:].tolist()
    return None


def _parse_inventario(df: pd.DataFrame, ronda: int) -> list[dict]:
    """
    Extrae específicamente el bloque 'Inventario, miles unidades' (dentro
    de 'Detalles de fabricación'). Este bloque tiene 3 niveles (mercado >
    tecnología) en vez de 2, así que el parser genérico de más abajo no
    puede ubicarlo sin ambigüedad (confundiría "Tec 1" de Inventario con
    "Tec 1" de Producción o de Capacidad empleada, que usan la misma
    etiqueta). Por eso lo resolvemos aparte y lo sumamos al resultado final
    con nombres de sección/subsección que no chocan con los del parser
    genérico.
    """
    records = []
    matches = df.index[df[0] == "Inventario, miles unidades"]
    if len(matches) == 0:
        return records

    start = matches[0]
    companies = _find_preceding_companies(df, start)
    if companies is None:
        return records

    current_mercado = None
    n = len(df)
    i = start + 1
    while i < n:
        row = df.iloc[i]
        c0 = row.iloc[0]

        if isinstance(c0, str) and c0.strip() == "Número de fábricas":
            break  # fin del bloque de inventario, no seguimos leyendo de más

        if isinstance(c0, str) and c0.strip() in ("EE.UU.", "Asia", "Europa"):
            current_mercado = c0.strip()
            i += 1
            continue

        if isinstance(c0, str) and c0.strip().startswith("Tec ") and current_mercado:
            tec = c0.strip()
            for empresa, valor in zip(companies, row.iloc[1:].tolist()):
                if pd.isna(valor):
                    continue
                records.append(
                    {
                        "ronda": ronda,
                        "seccion": "Detalles de fabricación",
                        "subseccion": f"Inventario, miles unidades — {current_mercado}",
                        "metrica": tec,
                        "empresa": empresa,
                        "valor_raw": valor,
                    }
                )
        i += 1

    return records


def _parse_promocion(df: pd.DataFrame, ronda: int) -> list[dict]:
    """
    Extrae específicamente la fila 'Promoción' dentro de 'Desglose de
    margen por tec, miles USD, <mercado>' (una por EE.UU./Asia/Europa).
    Es otro bloque de 3 niveles (mercado > tecnología > línea) con el
    agravante de que varias etiquetas se repiten igual dentro de cada
    tecnología ("Ingresos por ventas", "Promoción", etc.), así que el
    parser genérico las mezclaría todas. Nota: a pesar del nombre, estas
    tres secciones vienen siempre en USD (lo verificamos sumando las tres
    regiones y comparando contra 'Promoción' de Cuenta de resultados
    Global, que coincide exacto), así que no hace falta conversión de
    moneda acá como sí hace falta para el precio de venta.
    """
    records = []
    for mercado in ("EE.UU.", "Asia", "Europa"):
        titulo = f"Desglose de margen por tec, miles USD, {mercado}"
        matches = df.index[df[0] == titulo]
        if len(matches) == 0:
            continue

        start = matches[0]
        companies = _find_preceding_companies(df, start)
        if companies is None:
            continue

        current_tec = None
        n = len(df)
        i = start + 1
        while i < n:
            row = df.iloc[i]
            c0 = row.iloc[0]

            if isinstance(c0, str) and (
                c0.strip().startswith("Desglose de margen por tec") or c0.strip() == "Valuación - Global"
            ):
                break  # terminó este bloque (empieza el de la próxima región, o la sección de valuación)

            if isinstance(c0, str) and c0.strip() in ("Tec 1", "Tec 2", "Tec 3", "Tec 4") and row.iloc[1:].isna().all():
                current_tec = c0.strip()
                i += 1
                continue

            if isinstance(c0, str) and c0.strip() == "Promoción" and current_tec is not None:
                for empresa, valor in zip(companies, row.iloc[1:].tolist()):
                    if pd.isna(valor):
                        continue
                    records.append(
                        {
                            "ronda": ronda,
                            "seccion": "Desglose de margen por tec",
                            "subseccion": f"Promoción — {mercado}",
                            "metrica": current_tec,
                            "empresa": empresa,
                            "valor_raw": valor,
                        }
                    )
            i += 1

    return records


def parse_simulation_file(file, ronda: int) -> pd.DataFrame:
    """
    file: ruta o objeto file-like (ej. el que entrega st.file_uploader)
    ronda: número de ronda/semana al que corresponde este archivo

    Devuelve un DataFrame tidy. Si no se pudo extraer nada, devuelve
    un DataFrame vacío (con columnas) para que el caller pueda chequear
    `.empty` sin romper.
    """
    df = pd.read_excel(file, sheet_name=SHEET_NAME, header=None)

    records = []
    current_section = None
    current_subsection = None
    companies = None
    n = len(df)

    for i in range(n):
        row = df.iloc[i]
        c0 = row.iloc[0]

        if _is_company_header_row(row):
            companies = row.iloc[1:].tolist()
            continue

        if _is_title_row(row):
            title = c0.strip()
            # miramos hacia adelante (saltando filas vacías) para decidir
            # si este título es una SECCIÓN nueva (le sigue un header de
            # empresas) o una SUBSECCIÓN dentro de la sección actual.
            j = i + 1
            while j < n and df.iloc[j].isna().all():
                j += 1
            if j < n and _is_company_header_row(df.iloc[j]):
                current_section = title
                current_subsection = None
            else:
                current_subsection = title
            continue

        if isinstance(c0, str) and companies is not None:
            label = c0.strip()
            for empresa, valor in zip(companies, row.iloc[1:].tolist()):
                if pd.isna(valor):
                    continue
                records.append(
                    {
                        "ronda": ronda,
                        "seccion": current_section,
                        "subseccion": current_subsection,
                        "metrica": label,
                        "empresa": empresa,
                        "valor_raw": valor,
                    }
                )

    records.extend(_parse_inventario(df, ronda))
    records.extend(_parse_promocion(df, ronda))

    out = pd.DataFrame.from_records(
        records,
        columns=["ronda", "seccion", "subseccion", "metrica", "empresa", "valor_raw"],
    )
    if out.empty:
        out["valor_numerico"] = pd.Series(dtype=float)
        return out

    out["valor_numerico"] = pd.to_numeric(out["valor_raw"], errors="coerce")
    return out