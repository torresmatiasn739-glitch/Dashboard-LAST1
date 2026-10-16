import streamlit as st

from parser import parse_simulation_file, extraer_ronda_de_nombre
import sheets_io
import style

st.set_page_config(page_title="Cargar datos", layout="wide")
style.mostrar_logo()
st.title("📤 Cargar resultados de una nueva ronda")

archivo = st.file_uploader("Subí el archivo .xls exportado del simulador", type=["xls", "xlsx"])

if archivo is not None:
    ronda_detectada = extraer_ronda_de_nombre(archivo.name)
    ronda_sugerida = ronda_detectada if ronda_detectada is not None else 1
    ronda = st.number_input(
        "Número de ronda (usá 0 para la situación inicial)",
        min_value=0,
        max_value=50,
        value=ronda_sugerida,
        step=1,
    )

    rondas_cargadas = sheets_io.rondas_existentes()
    ya_existe = ronda in rondas_cargadas

    if ya_existe:
        st.warning(f"La ronda {ronda} ya está cargada. Si continuás, se reemplaza por estos datos nuevos.")

    if st.button("Procesar y guardar", type="primary"):
        with st.spinner("Procesando archivo..."):
            df_tidy = parse_simulation_file(archivo, ronda=int(ronda))

        if df_tidy.empty:
            st.error(
                "No se pudo extraer información del archivo. Revisá que sea el mismo "
                "formato que vienen exportando del simulador (hoja 'Results')."
            )
        else:
            st.success(f"Se extrajeron {len(df_tidy)} valores de la ronda {ronda}.")
            st.dataframe(df_tidy.head(30), use_container_width=True)

            with st.spinner("Guardando en Google Sheets..."):
                sheets_io.guardar_ronda(df_tidy, sobrescribir=ya_existe)
            st.success("¡Listo! Los datos ya están disponibles en el resto del dashboard.")
            st.balloons()

st.divider()
rondas = sheets_io.rondas_existentes()
st.caption("Rondas actualmente cargadas: " + (", ".join(str(r) for r in rondas) if rondas else "ninguna todavía"))