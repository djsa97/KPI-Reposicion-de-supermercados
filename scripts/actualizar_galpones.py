import argparse
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data" / "galpones"
ERP_OUTPUT = DATA_DIR / "informe_galpones.xlsx"
CLASSIFICATION_OUTPUT = DATA_DIR / "produccion_respuestas.xlsx"
DEFAULT_LAUNCHER_ENV = Path.home() / "Documents" / "ERP Launcher" / "launcher.env"

ERP_URL = os.getenv("ERP_URL", "https://erpsol.valurq.com.py/#")
ERP_USER = os.getenv("ERP_USER", "")
ERP_PASSWORD = os.getenv("ERP_PASSWORD", "")
FECHA_DESDE = os.getenv("ERP_FECHA_DESDE", "2026-01-01")
FECHA_HASTA = os.getenv("ERP_FECHA_HASTA", date.today().isoformat())

GOOGLE_CREDS_FILE = Path(
    os.getenv(
        "GOOGLE_CREDS_FILE",
        ROOT_DIR / "automatizacion-sol-huevos-2-f02d718cb7d4.json",
    )
)
CLASSIFICATION_SHEET_ID = "1YLyafk2PfuVbH-lzueansm1czO7iViYmNSPf0VIoUJY"
CLASSIFICATION_GIDS = [1888865188, 171831057]
CLASSIFICATION_WORKSHEET_HINTS = [
    "Respuestas de formulario 1",
    "Producción  (respuestas)",
    "Produccion  (respuestas)",
]
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def debug(message: str) -> None:
    print(message, flush=True)


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value:
            values[key] = value
    return values


def load_launcher_env() -> None:
    launcher_home = os.getenv("ERP_LAUNCHER_HOME")
    env_path = Path(launcher_home) / "launcher.env" if launcher_home else DEFAULT_LAUNCHER_ENV
    for key, value in load_env_file(env_path).items():
        os.environ.setdefault(key, value)


def refresh_runtime_env() -> None:
    global ERP_URL, ERP_USER, ERP_PASSWORD, FECHA_DESDE, FECHA_HASTA
    ERP_URL = os.getenv("ERP_URL", ERP_URL)
    ERP_USER = os.getenv("ERP_USER", ERP_USER)
    ERP_PASSWORD = os.getenv("ERP_PASSWORD", ERP_PASSWORD)
    FECHA_DESDE = os.getenv("ERP_FECHA_DESDE", FECHA_DESDE)
    FECHA_HASTA = os.getenv("ERP_FECHA_HASTA", FECHA_HASTA)


def fecha_iso_a_ui(fecha_iso: str) -> str:
    yyyy, mm, dd = fecha_iso.split("-")
    return f"{dd}/{mm}/{yyyy}"


def click_text_safe(page, text: str, exact: bool = True, timeout: int = 10_000) -> bool:
    try:
        page.get_by_text(text, exact=exact).click(timeout=timeout)
        return True
    except Exception:
        try:
            page.locator(f"text={text}").first.click(timeout=timeout)
            return True
        except Exception:
            return False


def fill_input_robusto(locator, valor: str, valor_iso: str | None = None) -> bool:
    input_type = ""
    try:
        input_type = (locator.get_attribute("type") or "").lower()
    except Exception:
        pass

    if input_type == "date" and valor_iso:
        try:
            locator.fill(valor_iso, timeout=3000)
            return True
        except Exception:
            try:
                locator.evaluate(
                    """(el, v) => {
                        el.value = v;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    valor_iso,
                )
                return True
            except Exception:
                pass

    for key in ("Meta+A", "Control+A"):
        try:
            locator.click(timeout=3000)
            locator.press(key, timeout=1000)
            locator.type(valor, delay=30, timeout=5000)
            return True
        except Exception:
            pass

    try:
        locator.fill(valor, timeout=3000)
        return True
    except Exception:
        return False


def login(page) -> bool:
    debug("Intentando login ERP...")
    page.goto(ERP_URL, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(3000)
    page.locator('input[name="usuario"]').fill(ERP_USER)
    page.locator('input[name="clave"]').fill(ERP_PASSWORD)

    for attempt in range(12):
        try:
            debug(f"Intento login #{attempt + 1}")
            page.get_by_role("button", name="INGRESAR").click(timeout=2000)
        except Exception:
            pass
        page.wait_for_timeout(2500)
        if page.locator('input[name="usuario"]').count() == 0:
            return True
    return False


def abrir_reporte_galpones(page) -> bool:
    debug("Abriendo INFORMES VARIOS > INFORME GALPONES...")
    if not click_text_safe(page, "INFORMES VARIOS", exact=False, timeout=15_000):
        debug("No pude abrir INFORMES VARIOS.")
        return False

    page.wait_for_timeout(1200)

    if not click_text_safe(page, "INFORME GALPONES", exact=False, timeout=15_000):
        debug("No pude abrir INFORME GALPONES.")
        return False

    page.wait_for_timeout(2500)

    try:
        body = page.locator("body").inner_text(timeout=5000).upper()
    except Exception:
        body = ""

    if "DESDE FECHA" in body and "HASTA FECHA" in body:
        debug("Pantalla de parámetros del informe detectada.")
        return True

    if "A PLANILLA" in body or "PLANILLA" in body:
        debug("Pantalla de informe detectada.")
        return True

    debug("No pude confirmar la pantalla de parámetros de INFORME GALPONES.")
    return False


def obtener_campos_fecha(page):
    for names in [
        ("fecha_desde", "fecha_hasta"),
        ("desde", "hasta"),
        ("fec_desde", "fec_hasta"),
    ]:
        try:
            desde = page.locator(f'input[name="{names[0]}"]').first
            hasta = page.locator(f'input[name="{names[1]}"]').first
            if desde.count() > 0 and hasta.count() > 0:
                return desde, hasta
        except Exception:
            pass

    visibles = []
    inputs = page.locator("input")
    for i in range(inputs.count()):
        item = inputs.nth(i)
        try:
            if item.is_visible():
                input_type = (item.get_attribute("type") or "").lower()
                name = (item.get_attribute("name") or "").lower()
                placeholder = (item.get_attribute("placeholder") or "").lower()
                if input_type in {"date", "text", ""} or "fecha" in name or "dd/mm" in placeholder:
                    visibles.append(item)
        except Exception:
            continue
    if len(visibles) >= 2:
        return visibles[0], visibles[1]
    raise RuntimeError("No encontre los campos de fecha del reporte.")


def lanzar_consulta(page) -> None:
    labels = [
        "A PLANILLA",
        "REALIZAR CONSULTA",
        "CONSULTAR",
        "GENERAR",
        "GENERAR REPORTE",
        "BUSCAR",
    ]
    for label in labels:
        if click_text_safe(page, label, exact=False, timeout=5000):
            page.wait_for_timeout(6000)
            return
    page.keyboard.press("Enter")
    page.wait_for_timeout(6000)


def buscar_descarga_excel(context, page, output_path: Path) -> bool:
    debug("Buscando botón o enlace de Excel...")
    selectors = [
        'a[href*=".xlsx"]',
        'a[href*=".xls"]',
        'a[href*="excel"]',
        'button:has-text("Excel")',
        'button:has-text("XLS")',
        'button:has-text("Descargar")',
        'a:has-text("Excel")',
        'a:has-text("XLS")',
        'a:has-text("Descargar")',
    ]

    for selector in selectors:
        locator = page.locator(selector)
        try:
            total = locator.count()
        except Exception:
            total = 0
        for i in range(total):
            item = locator.nth(i)
            try:
                if not item.is_visible():
                    continue
            except Exception:
                pass
            try:
                with page.expect_download(timeout=20_000) as download_info:
                    item.click(timeout=5000)
                download = download_info.value
                output_path.parent.mkdir(parents=True, exist_ok=True)
                download.save_as(str(output_path))
                debug(f"Excel ERP guardado: {output_path}")
                return True
            except Exception:
                try:
                    href = item.get_attribute("href") or ""
                    if href:
                        response = context.request.get(urljoin(ERP_URL, href), timeout=30_000)
                        if response.ok:
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            output_path.write_bytes(response.body())
                            debug(f"Excel ERP guardado desde enlace: {output_path}")
                            return True
                except Exception:
                    pass
    return False


def descargar_erp_galpones(output_path: Path) -> None:
    if not ERP_USER or not ERP_PASSWORD:
        raise RuntimeError("Faltan ERP_USER y ERP_PASSWORD en launcher.env.")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        try:
            if not login(page):
                raise RuntimeError("No se pudo iniciar sesion en ERP.")
            if not abrir_reporte_galpones(page):
                raise RuntimeError(
                    "No encontre el reporte de galpones. Si el menu tiene otro nombre, "
                    "pasame una captura del menu del ERP y lo ajusto."
                )

            desde, hasta = obtener_campos_fecha(page)
            fill_input_robusto(desde, fecha_iso_a_ui(FECHA_DESDE), FECHA_DESDE)
            fill_input_robusto(hasta, fecha_iso_a_ui(FECHA_HASTA), FECHA_HASTA)
            debug(f"Fechas ERP: {FECHA_DESDE} a {FECHA_HASTA}")
            lanzar_consulta(page)

            if not buscar_descarga_excel(context, page, output_path):
                raise RuntimeError("No encontre descarga Excel despues de generar el reporte.")
        finally:
            browser.close()


def copy_erp_excel(source: Path, output_path: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"No existe el Excel ERP indicado: {source}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output_path)
    debug(f"Excel ERP copiado: {source} -> {output_path}")


def connect_sheet():
    if not GOOGLE_CREDS_FILE.exists():
        raise FileNotFoundError(f"No existe GOOGLE_CREDS_FILE: {GOOGLE_CREDS_FILE}")
    creds = Credentials.from_service_account_file(GOOGLE_CREDS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def resolve_classification_worksheet(spreadsheet):
    worksheets = spreadsheet.worksheets()
    for gid in CLASSIFICATION_GIDS:
        for ws in worksheets:
            if ws.id == gid:
                return ws
    title_map = {ws.title.strip().lower(): ws for ws in worksheets}
    for hint in CLASSIFICATION_WORKSHEET_HINTS:
        ws = title_map.get(hint.strip().lower())
        if ws:
            return ws
    return worksheets[0]


def descargar_clasificacion_sheet(output_path: Path) -> None:
    debug("Descargando clasificación desde Google Sheet...")
    client = connect_sheet()
    spreadsheet = client.open_by_key(CLASSIFICATION_SHEET_ID)
    worksheet = resolve_classification_worksheet(spreadsheet)
    rows = worksheet.get_all_values()
    if not rows:
        raise RuntimeError(f"La hoja {worksheet.title} no tiene datos.")

    header = rows[0]
    data = rows[1:]
    df = pd.DataFrame(data, columns=header)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Respuestas de formulario 1", index=False)
    debug(f"Clasificación guardada desde hoja '{worksheet.title}': {output_path}")


def git_changed() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", "data/galpones"],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        check=True,
    )
    return bool(result.stdout.strip())


def publicar_si_cambio() -> None:
    if not git_changed():
        debug("No hay cambios de datos para publicar.")
        return

    subprocess.run(
        ["git", "add", "data/galpones/informe_galpones.xlsx", "data/galpones/produccion_respuestas.xlsx"],
        cwd=ROOT_DIR,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Update galpones dashboard data"],
        cwd=ROOT_DIR,
        check=True,
    )
    subprocess.run(["git", "push", "origin", "main"], cwd=ROOT_DIR, check=True)
    debug("Datos publicados en GitHub. Streamlit Cloud va a redeployar solo.")


def parse_args():
    parser = argparse.ArgumentParser(description="Actualiza datos del dashboard productivo de galpones.")
    parser.add_argument("--erp-excel", help="Usa un Excel ERP ya descargado en vez de automatizar el ERP.")
    parser.add_argument("--solo-sheet", action="store_true", help="Actualiza solo la clasificación de Google Sheet.")
    parser.add_argument("--solo-erp", action="store_true", help="Actualiza solo el Excel del ERP.")
    parser.add_argument("--no-push", action="store_true", help="No hace commit/push a GitHub.")
    parser.add_argument("--fecha-desde", default=FECHA_DESDE)
    parser.add_argument("--fecha-hasta", default=FECHA_HASTA)
    return parser.parse_args()


def main() -> None:
    load_launcher_env()
    args = parse_args()
    os.environ["ERP_FECHA_DESDE"] = args.fecha_desde
    os.environ["ERP_FECHA_HASTA"] = args.fecha_hasta
    refresh_runtime_env()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not args.solo_sheet:
        if args.erp_excel:
            copy_erp_excel(Path(args.erp_excel).expanduser(), ERP_OUTPUT)
        else:
            try:
                descargar_erp_galpones(ERP_OUTPUT)
            except PlaywrightTimeoutError as exc:
                raise RuntimeError(f"Timeout descargando Excel ERP: {exc}") from exc

    if not args.solo_erp:
        try:
            descargar_clasificacion_sheet(CLASSIFICATION_OUTPUT)
        except gspread.exceptions.APIError as exc:
            raise RuntimeError(
                "No pude leer el Google Sheet de clasificación. Compartilo con "
                "bot-erp@automatizacion-sol-huevos-2.iam.gserviceaccount.com "
                "con permiso de lector/editor y volvé a ejecutar."
            ) from exc

    if not args.no_push:
        publicar_si_cambio()

    debug("Actualización de galpones completada.")


if __name__ == "__main__":
    main()
