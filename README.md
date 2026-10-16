# Dashboard de Control de Gestión — Simulador de Negocios

Estado actual: pestaña **"Cargar datos"** + pestaña **"Ratios e indicadores
financieros clave"**. El resto de las pestañas se van a ir agregando como
archivos nuevos dentro de `pages/`.

## Cómo funciona el flujo de datos (resumen)

1. Cada semana, alguien del equipo entra al dashboard, va a **Cargar datos**
   y sube el `.xls` que exporta el simulador (ej. `results-r02.xls`).
2. `parser.py` lee ese Excel y lo convierte a una tabla "tidy" (una fila por
   cada combinación ronda/sección/métrica/empresa/valor).
3. Esa tabla se **agrega** (append) a una Google Sheet que funciona como
   base de datos acumulada de todas las rondas jugadas hasta el momento.
4. Cada pestaña del dashboard (como "Ratios e indicadores") lee esa misma
   Google Sheet, filtra la sección que le interesa, y arma sus gráficos.

Por qué Google Sheets y no guardar un archivo en el servidor: cuando el
dashboard está desplegado (Streamlit Community Cloud u otro hosting), el
disco del servidor es efímero — se borra en cada redeploy o reinicio. Si
guardáramos el histórico en un CSV local, lo perderías tarde o temprano.
Google Sheets persiste siempre, es gratis, y de paso cualquiera del equipo
puede abrir la planilla y revisar o corregir un valor a mano si hace falta.

## 1. Instalación local

```bash
python -m venv .venv
source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Crear el service account de Google (una sola vez)

1. Entrá a [console.cloud.google.com](https://console.cloud.google.com/) y
   creá un proyecto nuevo (o usá uno existente).
2. En **APIs y servicios → Biblioteca**, activá:
   - Google Sheets API
   - Google Drive API
3. En **APIs y servicios → Credenciales → Crear credenciales → Cuenta de
   servicio**. Le ponés un nombre (ej. `dashboard-simulador`) y la creás.
4. Entrá a esa cuenta de servicio → pestaña **Claves → Agregar clave →
   Crear clave nueva → JSON**. Se descarga un archivo `.json`: ahí están
   todos los campos que necesitás (`private_key`, `client_email`, etc.).

## 3. Crear y compartir la Google Sheet

1. Creá una Google Sheet nueva (puede estar vacía, el código crea la hoja
   `datos_tidy` sola la primera vez que se usa).
2. Copiá el **ID de la planilla**: es la parte de la URL entre `/d/` y
   `/edit`.
   `https://docs.google.com/spreadsheets/d/ESTE_ES_EL_ID/edit`
3. Compartí la planilla (botón "Compartir") con el `client_email` que
   figura en el JSON del service account, dándole permiso de **Editor**.
   Sin este paso el dashboard no va a poder escribir en la planilla.

## 4. Configurar los secrets

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Editá `.streamlit/secrets.toml` y completá:
- `sheet_id` con el ID del paso anterior.
- Todos los campos de `[gcp_service_account]` copiándolos del `.json`
  descargado (el campo `private_key` incluye saltos de línea `\n`; dejalo
  tal cual, entre comillas, como viene en el JSON).

## 5. Correrlo en local

```bash
streamlit run app.py
```

Se abre en el navegador. Probá subir `results-r01.xls` en "Cargar datos"
y después mirá la pestaña "Ratios e indicadores financieros clave".

## 6. Compartirlo (desplegar online)

Como pediste, esto no puede quedar solo en localhost. La opción más simple
y gratuita:

1. Subí esta carpeta a un repositorio de GitHub (sin el `secrets.toml`
   real — ya está en `.gitignore`).
2. Entrá a [share.streamlit.io](https://share.streamlit.io), conectá tu
   cuenta de GitHub y elegí el repo + `app.py` como archivo principal.
3. En **Advanced settings → Secrets**, pegá el contenido completo de tu
   `secrets.toml` real (sheet_id + bloque `[gcp_service_account]`).
4. Deploy. Te da una URL pública (`https://tu-app.streamlit.app`) que
   podés compartir con todo el equipo. Cualquiera que entre puede cargar
   la ronda nueva o solo mirar los gráficos.

## Siguientes pasos

Mandame el mockup de la próxima pestaña (igual que hiciste con "Ratios e
indicadores") y la agrego como un nuevo archivo en `pages/`, reutilizando
el mismo `parser.py` y la misma Google Sheet — no hay que volver a cargar
los Excel ya subidos.
