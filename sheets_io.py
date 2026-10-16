"""
sheets_io.py
------------
Capa de persistencia. Usamos una Google Sheet como "base de datos" del
histórico acumulado (todas las rondas cargadas hasta ahora, en formato
tidy). Ver README.md para cómo crear el service account y compartir la
planilla.

Requiere en st.secrets:
    sheet_id = "..."                  # ID de la planilla (está en la URL)
    [gcp_service_account]
    type = "service_account"
    project_id = "..."
    private_key_id = "..."
    private_key = "..."
    client_email = "...@....iam.gserviceaccount.com"
    client_id = "..."
    token_uri = "https://oauth2.googleapis.com/token"
    (el resto de los campos del JSON que descarga Google Cloud)
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

WORKSHEET_NAME = "datos_tidy"
COLUMNS = ["ronda", "seccion", "subseccion", "metrica", "empresa", "valor_raw", "valor_numerico"]


def _get_client() -> gspread.Client:
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_worksheet():
    client = _get_client()
    sh = client.open_by_key(st.secrets["sheet_id"])
    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=WORKSHEET_NAME, rows=2000, cols=len(COLUMNS))
        ws.append_row(COLUMNS)
    return ws


@st.cache_data(ttl=300, show_spinner="Cargando histórico desde Google Sheets...")
def load_data() -> pd.DataFrame:
    """Lee todo el histórico acumulado. Cacheado 5 min para no pegarle
    a la API de Google en cada interacción del usuario."""
    ws = _get_worksheet()
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=COLUMNS)
    df = pd.DataFrame(records)
    df["ronda"] = pd.to_numeric(df["ronda"], errors="coerce").astype("Int64")
    df["valor_numerico"] = pd.to_numeric(df["valor_numerico"], errors="coerce")
    return df


def rondas_existentes() -> list[int]:
    df = load_data()
    if df.empty:
        return []
    return sorted(df["ronda"].dropna().unique().tolist())


def guardar_ronda(df_nuevo: pd.DataFrame, sobrescribir: bool = False) -> None:
    """Agrega una ronda nueva al histórico. Si sobrescribir=True, primero
    borra las filas existentes de esa ronda (evita duplicados al volver
    a subir un archivo corregido)."""
    ws = _get_worksheet()
    ronda = int(df_nuevo["ronda"].iloc[0])

    if sobrescribir:
        _borrar_ronda(ws, ronda)

    # fillna("") antes de astype(str): en pandas reciente, astype(str) deja
    # los NaN como NaN real en vez de convertirlos a "nan", y eso rompe la
    # serialización JSON que usa gspread. Rellenamos primero para evitarlo.
    filas = df_nuevo[COLUMNS].fillna("").astype(str).values.tolist()
    ws.append_rows(filas, value_input_option="USER_ENTERED")
    load_data.clear()  # invalida la cache para que el resto del dashboard vea los datos nuevos


def _borrar_ronda(ws, ronda: int) -> None:
    all_values = ws.get_all_values()
    if not all_values:
        return
    header, rows = all_values[0], all_values[1:]
    ronda_idx = header.index("ronda")
    filas_a_mantener = [header] + [r for r in rows if r[ronda_idx] != str(ronda)]
    ws.clear()
    ws.update(filas_a_mantener)