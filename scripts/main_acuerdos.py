import os
import re
from urllib.parse import urljoin

import pdfplumber
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# =========================
# CONFIG ERP
# =========================
ERP_URL = os.getenv("ERP_URL", "https://erpsol.valurq.com.py/#")
USUARIO = os.getenv("ERP_USER", "")
CLAVE = os.getenv("ERP_PASSWORD", "")

PDF_PATH = "data/acuerdos_enero_marzo.pdf"

FECHA_DESDE = "2026-01-01"
FECHA_HASTA = "2026-03-31"


# =========================
# CONFIG GOOGLE SHEETS
# =========================
JSON_PATH = "automatizacion-sol-huevos-2-f02d718cb7d4.json"
SHEET_ID = "1B21HlZ5MBVj6Orc1rkLM1_mZycXLDEJDIT9OF9Gw9Kw"
WORKSHEET_NAME = "acuerdos_raw"


# =========================
# UTILS
# =========================
def debug(msg: str):
    print(msg, flush=True)


def validar_credenciales_erp():
    if not USUARIO or not CLAVE:
        raise RuntimeError(
            "Faltan credenciales del ERP. Definí ERP_USER y ERP_PASSWORD en variables de entorno."
        )


def limpiar_texto(texto: str) -> str:
    if texto is None:
        return ""
    return " ".join(str(texto).split()).strip()


def monto_a_int(texto: str) -> int:
    texto = limpiar_texto(texto)
    if not texto:
        return 0
    texto = texto.replace(".", "").replace(",", "")
    try:
        return int(texto)
    except Exception:
        return 0


def fecha_iso_a_ui(fecha_iso: str) -> str:
    yyyy, mm, dd = fecha_iso.split("-")
    return f"{dd}/{mm}/{yyyy}"


# =========================
# PLAYWRIGHT HELPERS
# =========================
def click_text_safe(page, texto: str, exact=True, timeout=10000):
    try:
        page.get_by_text(texto, exact=exact).click(timeout=timeout)
        return True
    except Exception:
        try:
            page.locator(f"text={texto}").first.click(timeout=timeout)
            return True
        except Exception:
            return False


def fill_input_robusto(locator, valor: str):
    locator.click(timeout=3000)

    try:
        locator.fill("")
    except Exception:
        pass

    try:
        locator.fill(valor, timeout=3000)
        return True
    except Exception:
        pass

    try:
        locator.click(timeout=3000)
        locator.press("Meta+A", timeout=2000)
        locator.type(valor, delay=50, timeout=5000)
        return True
    except Exception:
        pass

    try:
        locator.click(timeout=3000)
        locator.press("Control+A", timeout=2000)
        locator.type(valor, delay=50, timeout=5000)
        return True
    except Exception:
        pass

    try:
        locator.click(timeout=3000)
        locator.type(valor, delay=50, timeout=5000)
        return True
    except Exception:
        pass

    return False


def click_boton_consulta(page) -> bool:
    debug("Intentando click en REALIZAR CONSULTA...")

    try:
        page.get_by_role("button", name="REALIZAR CONSULTA").click(timeout=5000)
        return True
    except Exception:
        pass

    try:
        page.get_by_text("REALIZAR CONSULTA", exact=False).click(timeout=5000)
        return True
    except Exception:
        pass

    try:
        page.locator("text=REALIZAR CONSULTA").first.click(timeout=5000)
        return True
    except Exception:
        pass

    try:
        botones = page.locator("button")
        total = botones.count()
        for i in range(total):
            btn = botones.nth(i)
            try:
                texto = limpiar_texto(btn.inner_text()).upper()
                if "REALIZAR CONSULTA" in texto:
                    btn.click(timeout=5000)
                    return True
            except Exception:
                continue
    except Exception:
        pass

    try:
        candidatos = page.locator('input[type="button"], input[type="submit"], .btn')
        total = candidatos.count()
        for i in range(total):
            c = candidatos.nth(i)
            try:
                texto = (
                    limpiar_texto(c.inner_text())
                    or limpiar_texto(c.get_attribute("value"))
                    or limpiar_texto(c.get_attribute("title"))
                ).upper()

                if "REALIZAR CONSULTA" in texto or "CONSULTA" in texto:
                    c.click(timeout=5000)
                    return True
            except Exception:
                continue
    except Exception:
        pass

    return False


# =========================
# LOGIN
# =========================
def login(page) -> bool:
    debug("Intentando login...")
    page.goto(ERP_URL)
    page.wait_for_timeout(3000)

    page.locator('input[name="usuario"]').fill(USUARIO)
    page.locator('input[name="clave"]').fill(CLAVE)

    for intento in range(12):
        try:
            debug(f"Intento login #{intento + 1}")
            page.get_by_role("button", name="INGRESAR").click(timeout=2000)
        except Exception:
            pass

        page.wait_for_timeout(2500)

        if page.locator("text=Diego").count() > 0:
            return True

        if page.locator('input[name="usuario"]').count() == 0:
            return True

    return False


# =========================
# NAVEGACIÓN ERP
# =========================
def abrir_gerencial_consolidado(page) -> bool:
    debug("Abriendo REPORTE DE VENTAS...")
    if not click_text_safe(page, "REPORTE DE VENTAS", exact=True, timeout=15000):
        return False

    page.wait_for_timeout(1500)

    debug("Abriendo GERENCIAL CONSOLIDADO...")
    if not click_text_safe(page, "GERENCIAL CONSOLIDADO", exact=True, timeout=15000):
        return False

    page.wait_for_timeout(4000)

    if page.locator("text=INFORME DE GERENCIAL DE VENTAS CONSOLIDADO").count() > 0:
        return True

    if page.locator("text=GERENCIAL CONSOLIDADO").count() > 0:
        return True

    if page.locator("text=REALIZAR CONSULTA").count() > 0:
        return True

    if page.locator("input").count() >= 2:
        return True

    return False


def obtener_campos_fecha(page):
    try:
        desde = page.locator('input[name="fecha_desde"]').first
        hasta = page.locator('input[name="fecha_hasta"]').first
        if desde.count() > 0 and hasta.count() > 0:
            return desde, hasta
    except Exception:
        pass

    try:
        candidatos = page.locator("input")
        visibles = []

        total = candidatos.count()
        for i in range(total):
            inp = candidatos.nth(i)
            try:
                if inp.is_visible():
                    tipo = (inp.get_attribute("type") or "").lower()
                    placeholder = (inp.get_attribute("placeholder") or "").lower()
                    name = (inp.get_attribute("name") or "").lower()

                    if tipo in ["text", "date", "search", ""] or "dd/mm" in placeholder or "fecha" in name:
                        visibles.append(inp)
            except Exception:
                continue

        if len(visibles) >= 2:
            return visibles[0], visibles[1]
    except Exception:
        pass

    try:
        inputs = page.locator("input")
        visibles = []
        total = inputs.count()

        for i in range(total):
            inp = inputs.nth(i)
            try:
                if inp.is_visible():
                    visibles.append(inp)
            except Exception:
                continue

        if len(visibles) >= 2:
            return visibles[0], visibles[1]
    except Exception:
        pass

    raise RuntimeError("No encontré los campos de fecha")


def generar_reporte(page) -> bool:
    debug(f"Fecha desde: {FECHA_DESDE}")
    debug(f"Fecha hasta: {FECHA_HASTA}")

    fecha_desde_ui = fecha_iso_a_ui(FECHA_DESDE)
    fecha_hasta_ui = fecha_iso_a_ui(FECHA_HASTA)

    try:
        campo_desde, campo_hasta = obtener_campos_fecha(page)
        debug("Campos de fecha detectados")

        ok1 = fill_input_robusto(campo_desde, fecha_desde_ui)
        page.wait_for_timeout(300)
        ok2 = fill_input_robusto(campo_hasta, fecha_hasta_ui)

        if not ok1 or not ok2:
            raise RuntimeError("No se pudo completar uno de los campos de fecha")

        debug("Fechas OK")
    except Exception as e:
        debug(f"Error fechas: {e}")
        return False

    page.wait_for_timeout(1000)

    if not click_boton_consulta(page):
        debug("Error: no pude clickear REALIZAR CONSULTA")
        return False

    debug("Consulta lanzada")
    page.wait_for_timeout(6000)
    return True


# =========================
# PDF
# =========================
def obtener_url_pdf(context, page) -> str:
    debug("Esperando que aparezca el enlace del PDF...")

    for _ in range(30):
        try:
            if page.get_by_text("enlace", exact=False).count() > 0:
                debug("Texto de enlace detectado")
                break
        except Exception:
            pass

        try:
            if page.locator('a[href*=".pdf"]').count() > 0:
                debug("Anchor PDF detectado")
                break
        except Exception:
            pass

        page.wait_for_timeout(1000)

    selectores_directos = [
        'a[href*=".pdf"]',
        'a[href*="gerencia"]',
        'a[href*="consolidado"]',
        'a[href*="/reportes_fuente/"]',
        'a[href*="salidas"]',
    ]

    for selector in selectores_directos:
        try:
            anchors = page.locator(selector)
            total = anchors.count()
            for i in range(total):
                href = anchors.nth(i).get_attribute("href")
                if href and (
                    ".pdf" in href.lower()
                    or "consolidado" in href.lower()
                    or "gerencia" in href.lower()
                    or "/reportes_fuente/" in href.lower()
                    or "salidas" in href.lower()
                ):
                    url_pdf = urljoin(ERP_URL, href)
                    debug(f"URL PDF encontrada por href directo: {url_pdf}")
                    return url_pdf
        except Exception:
            pass

    textos_link = [
        "en este enlace",
        "este enlace",
        "Presione en este enlace",
        "enlace",
    ]

    for texto in textos_link:
        try:
            locator = page.get_by_text(texto, exact=False).first
            if locator.count() > 0:
                debug(f"Intentando click sobre texto del enlace: {texto}")

                with context.expect_page(timeout=15000) as new_page_info:
                    locator.click(timeout=5000)

                nueva_pagina = new_page_info.value
                nueva_pagina.wait_for_load_state("domcontentloaded", timeout=15000)
                url_popup = nueva_pagina.url

                if (
                    ".pdf" in url_popup.lower()
                    or "consolidado" in url_popup.lower()
                    or "gerencia" in url_popup.lower()
                    or "/reportes_fuente/" in url_popup.lower()
                ):
                    debug(f"URL PDF encontrada por nueva pestaña: {url_popup}")
                    return url_popup
        except Exception:
            pass

    try:
        anchors = page.locator("a")
        total = anchors.count()
        for i in range(total):
            try:
                texto = (anchors.nth(i).inner_text() or "").strip()
                href = anchors.nth(i).get_attribute("href")
                if href and (
                    ".pdf" in href.lower()
                    or "consolidado" in href.lower()
                    or "gerencia" in href.lower()
                    or "/reportes_fuente/" in href.lower()
                    or "enlace" in texto.lower()
                ):
                    url_pdf = urljoin(ERP_URL, href)
                    debug(f"URL PDF encontrada por revisión general de anchors: {url_pdf}")
                    return url_pdf
            except Exception:
                continue
    except Exception:
        pass

    try:
        for p in context.pages:
            try:
                url_actual = p.url
                if (
                    ".pdf" in url_actual.lower()
                    or "consolidado" in url_actual.lower()
                    or "gerencia" in url_actual.lower()
                    or "/reportes_fuente/" in url_actual.lower()
                ):
                    debug(f"URL PDF encontrada en páginas abiertas: {url_actual}")
                    return url_actual
            except Exception:
                continue
    except Exception:
        pass

    raise RuntimeError("No se encontró la URL del PDF")


def descargar_pdf(context, url_pdf: str, pdf_path: str):
    debug("Descargando PDF...")

    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    response = context.request.get(url_pdf)
    if not response.ok:
        raise RuntimeError(f"No se pudo descargar PDF. HTTP {response.status}")

    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    with open(pdf_path, "wb") as f:
        f.write(response.body())

    debug(f"PDF guardado en: {pdf_path}")


# =========================
# PARSER GERENCIAL CONSOLIDADO
# =========================
PATRON_DESDE = re.compile(r"Desde\s*:\s*(\d{2}/\d{2}/\d{4})")
PATRON_HASTA = re.compile(r"Hasta\s*:\s*(\d{2}/\d{2}/\d{4})")
PATRON_FILA_CLIENTE = re.compile(
    r"^(?P<cliente>.+?)\s+"
    r"(?P<venta>\d[\d\.]*)\s+"
    r"(?P<nc>\d[\d\.]*)\s+"
    r"(?P<acuerdos>\d[\d\.]*)\s+"
    r"(?P<neto>\d[\d\.]*)$"
)


def es_basura_consolidado(linea: str) -> bool:
    linea = limpiar_texto(linea)

    if not linea:
        return True

    basuras = {
        "SOL HUEVOS",
        "INFORME GERENCIAL DE VENTAS CONSOLIDADO.",
        "Solo se considera cliente con rubro = supermercados",
        "Criterios",
        "CLIENTE VENTA NC ACUERDOS NETO",
        "CLIENTE",
        "VENTA",
        "NC",
        "ACUERDOS",
        "NETO",
    }

    if linea in basuras:
        return True

    if linea.startswith("Desde :"):
        return True
    if linea.startswith("Hasta :"):
        return True
    if linea.startswith("TOTAL GENERAL"):
        return True

    return False


def extraer_datos_pdf(pdf_path):
    filas = []

    if not os.path.exists(pdf_path):
        raise RuntimeError(f"No existe el PDF: {pdf_path}")

    fecha_desde_pdf = ""
    fecha_hasta_pdf = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            texto = page.extract_text()
            if not texto:
                continue

            lineas = [limpiar_texto(x) for x in texto.split("\n")]

            for linea in lineas:
                if not linea:
                    continue

                m_desde = PATRON_DESDE.search(linea)
                if m_desde:
                    fecha_desde_pdf = m_desde.group(1)

                m_hasta = PATRON_HASTA.search(linea)
                if m_hasta:
                    fecha_hasta_pdf = m_hasta.group(1)

                if es_basura_consolidado(linea):
                    continue

                m_fila = PATRON_FILA_CLIENTE.match(linea)
                if m_fila:
                    cliente = limpiar_texto(m_fila.group("cliente"))
                    venta = monto_a_int(m_fila.group("venta"))
                    nc = monto_a_int(m_fila.group("nc"))
                    acuerdos = monto_a_int(m_fila.group("acuerdos"))
                    neto = monto_a_int(m_fila.group("neto"))

                    filas.append([
                        cliente,
                        fecha_desde_pdf,
                        fecha_hasta_pdf,
                        venta,
                        nc,
                        acuerdos,
                        neto,
                    ])

    return filas


# =========================
# GOOGLE SHEETS
# =========================
def conectar_google_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_file(JSON_PATH, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_ID)
    worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
    return worksheet


def subir_datos(worksheet, filas):
    debug("Limpiando hoja...")
    worksheet.clear()

    encabezados = [[
        "CLIENTE",
        "FECHA_DESDE",
        "FECHA_HASTA",
        "VENTA",
        "NC",
        "ACUERDOS",
        "NETO",
    ]]
    worksheet.update(values=encabezados, range_name="A1")

    if filas:
        debug(f"Subiendo {len(filas)} filas...")
        worksheet.update(values=filas, range_name=f"A2:G{len(filas)+1}")
    else:
        debug("No hubo filas para subir")


# =========================
# MAIN
# =========================
def main():
    validar_credenciales_erp()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=600)
        context = browser.new_context()
        page = context.new_page()

        try:
            if not login(page):
                debug("LOGIN FAIL")
                return

            debug("Login OK")

            if not abrir_gerencial_consolidado(page):
                debug("NAV FAIL")
                return

            debug("GERENCIAL CONSOLIDADO OK")

            if not generar_reporte(page):
                debug("ERROR EN GENERACIÓN")
                return

            debug("REPORTE GENERADO OK")

            url_pdf = obtener_url_pdf(context, page)
            descargar_pdf(context, url_pdf, PDF_PATH)

            debug("Procesando PDF...")
            filas = extraer_datos_pdf(PDF_PATH)
            debug(f"Filas extraídas: {len(filas)}")

            worksheet = conectar_google_sheet()
            debug("Conexión Google Sheets OK")

            subir_datos(worksheet, filas)
            debug("CARGA COMPLETADA OK")

        except PlaywrightTimeoutError as e:
            debug(f"Timeout Playwright: {e}")
        except Exception as e:
            debug(f"ERROR GENERAL: {e}")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
