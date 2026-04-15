# Dashboard de Reposición SOL HUEVOS

Dashboard de reposición en Streamlit conectado a Google Sheets, con foco en promedio semanal neto por producto, supermercado y sucursal.

## Qué incluye

- Dashboard principal de reposición: `dashboard_reposicion.py`
- Scripts de extracción desde ERP:
  - `scripts/main_ventas.py`
  - `scripts/main_notas_credito.py`
  - `scripts/main_acuerdos.py`
- Consolidación y base del dashboard:
  - `scripts/main_consolidado.py`
  - `scripts/main_reposicion_base.py`
  - `scripts/main_control_dashboard.py`

## Requisitos

- Python 3.11+
- Google Sheet con estas hojas:
  - `movimientos_raw`
  - `notas_credito_raw`
  - `acuerdos_raw`
  - `movimientos_final`
  - `reposicion_base`
  - `control_dashboard`
- Archivo local de credenciales de Google Service Account
- Credenciales del ERP configuradas por variables de entorno

## Variables de entorno

Para ejecutar los scripts del ERP, configurá:

```bash
export ERP_URL="https://erpsol.valurq.com.py/#"
export ERP_USER="tu_usuario"
export ERP_PASSWORD="tu_password"
```

Opcionalmente podés indicar otra ruta para las credenciales de Google:

```bash
export GOOGLE_CREDS_FILE="/ruta/a/service-account.json"
```

Si no se define `GOOGLE_CREDS_FILE`, el proyecto busca localmente:

```text
automatizacion-sol-huevos-2-f02d718cb7d4.json
```

Ese archivo está ignorado por git y no debe subirse al repositorio.

## Ejecutar el dashboard

```bash
cd /ruta/al/proyecto
python3 -m streamlit run dashboard_reposicion.py
```

## Flujo de actualización

```bash
python3 scripts/main_ventas.py
python3 scripts/main_notas_credito.py
python3 scripts/main_acuerdos.py
python3 scripts/main_consolidado.py
python3 scripts/main_reposicion_base.py
python3 scripts/main_control_dashboard.py
python3 -m streamlit run dashboard_reposicion.py
```

## Publicación

Antes de publicar:

- no subir credenciales JSON
- no subir PDFs descargados del ERP
- no subir usuario/clave del ERP al código

Este repo ya está preparado para eso con `.gitignore` y variables de entorno.
