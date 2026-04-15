import os
import re
import json
import subprocess
from urllib.parse import urljoin

import pdfplumber
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# =========================
# CONFIG ERP
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
OCR_SWIFT_HELPER = os.path.join(BASE_DIR, "ocr_pdf_obs.swift")
OCR_BINARY_PATH = "/tmp/ocr_pdf_obs"

ERP_URL = os.getenv("ERP_URL", "https://erpsol.valurq.com.py/#")
USUARIO = os.getenv("ERP_USER", "")
CLAVE = os.getenv("ERP_PASSWORD", "")

PDF_PATH = os.path.join(PROJECT_DIR, "data", "ventas_enero_marzo.pdf")

FECHA_DESDE = "2026-01-01"
FECHA_HASTA = "2026-03-31"

CLIENTES_SUPER_OCR = {
    "SALEMMA RETAIL SA",
    "SUPER BOX S. A.",
    "EMPRENDIMIENTOS JC S.A.",
    "SUPERMERCADO VILLA SOFIA S.A.",
    "CADENA REAL S.A.",
    "LT SOCIEDAD ANONIMA",
    "CEBRE S.A.",
    "CAFSA S.A.",
    "ALIMENTOS ESPECIALES S.A.",
    "TODO CARNE S.A.",
    "MGI MISION S.A.",
    "DELIVERY HERO DMART PARAGUAY S.A",
    "DELIVERY HERO DMART PARAGUAY S.A -",
    "RETAIL S.A.",
    "BIGGIE S.A.",
}


# =========================
# CONFIG GOOGLE SHEETS
# =========================
JSON_PATH = os.path.join(PROJECT_DIR, "automatizacion-sol-huevos-2-f02d718cb7d4.json")
SHEET_ID = "1B21HlZ5MBVj6Orc1rkLM1_mZycXLDEJDIT9OF9Gw9Kw"
WORKSHEET_NAME = "movimientos_raw"


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


def cantidad_a_numero(texto: str):
    texto = limpiar_texto(texto)
    if not texto:
        return 0

    texto2 = texto.replace(",", ".")
    try:
        valor = float(texto2)
        if valor.is_integer():
            return int(valor)
        return valor
    except Exception:
        texto3 = texto.replace(".", "").replace(",", ".")
        try:
            valor = float(texto3)
            if valor.is_integer():
                return int(valor)
            return valor
        except Exception:
            return 0


def fecha_iso_a_ui(fecha_iso: str) -> str:
    yyyy, mm, dd = fecha_iso.split("-")
    return f"{dd}/{mm}/{yyyy}"


def ensure_ocr_binary():
    helper_exists = os.path.exists(OCR_SWIFT_HELPER)
    if not helper_exists:
        return False

    needs_build = not os.path.exists(OCR_BINARY_PATH)
    if not needs_build:
        try:
            needs_build = os.path.getmtime(OCR_BINARY_PATH) < os.path.getmtime(OCR_SWIFT_HELPER)
        except Exception:
            needs_build = True

    if not needs_build:
        return True

    try:
        subprocess.run(
            ["swiftc", OCR_SWIFT_HELPER, "-o", OCR_BINARY_PATH],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def extraer_sucursales_ocr(pdf_path: str, page_index: int):
    if not ensure_ocr_binary():
        return []

    try:
        out = subprocess.check_output(
            [OCR_BINARY_PATH, pdf_path, str(page_index)],
            text=True,
        )
        data = json.loads(out)
    except Exception:
        return []

    lineas = []
    for item in data:
        texto = limpiar_texto(item.get("text", ""))
        texto_up = texto.upper()
        if not texto:
            continue
        if texto_up.startswith("SUCURSAL"):
            texto = re.sub(r"^SUCURSAL\s*", "", texto, flags=re.IGNORECASE).strip()
            lineas.append((float(item.get("minY", 0)), limpiar_obs_sucursal(texto)))

    lineas.sort(key=lambda x: -x[0])
    return [texto for _, texto in lineas if texto]


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


def fill_input_robusto(locator, valor: str, valor_iso: str | None = None):
    tipo = ""
    try:
        tipo = (locator.get_attribute("type") or "").lower()
    except Exception:
        tipo = ""

    if tipo == "date" and valor_iso:
        try:
            locator.click(timeout=3000)
        except Exception:
            pass

        try:
            locator.fill(valor_iso, timeout=3000)
            return True
        except Exception:
            pass

        try:
            locator.evaluate(
                """(el, v) => {
                    el.value = v;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('blur', { bubbles: true }));
                }""",
                valor_iso,
            )
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
        locator.fill(valor, timeout=3000)
        return True
    except Exception:
        pass

    try:
        locator.evaluate(
            """(el, v) => {
                el.value = v;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            valor,
        )
        return True
    except Exception:
        pass

    try:
        locator.click(timeout=3000)
    except Exception:
        pass

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
    """
    Intenta varias formas de clickear el botón de generación/consulta
    """
    debug("Intentando click en botón de generación...")
    textos_objetivo = ["REALIZAR CONSULTA", "GENERAR REPORTE", "CONSULTA", "GENERAR"]

    for texto in textos_objetivo:
        try:
            page.get_by_role("button", name=texto).click(timeout=5000)
            return True
        except Exception:
            pass

    for texto in textos_objetivo:
        try:
            page.get_by_text(texto, exact=False).first.click(timeout=5000)
            return True
        except Exception:
            pass

    for texto in textos_objetivo:
        try:
            page.locator(f"text={texto}").first.click(timeout=5000)
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
                if any(obj in texto for obj in textos_objetivo):
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

                if any(obj in texto for obj in textos_objetivo):
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
    page.goto(ERP_URL, wait_until="domcontentloaded", timeout=60000)
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
def abrir_reporte_ventas(page) -> bool:
    debug("Abriendo REPORTE DE VENTAS...")
    if not click_text_safe(page, "REPORTE DE VENTAS", exact=True, timeout=15000):
        return False

    page.wait_for_timeout(1500)

    debug("Abriendo VENTAS DETALLADO...")
    if not click_text_safe(page, "VENTAS DETALLADO", exact=True, timeout=15000):
        return False

    page.wait_for_timeout(4000)

    if page.locator("input").count() >= 2 and page.locator("text=FECHA DESDE").count() > 0:
        return True

    if page.locator("text=VENTAS DETALLADO").count() > 0:
        return True

    if page.locator("text=VENTAS POR CLIENTE").count() > 0:
        return True

    if page.locator("text=REALIZAR CONSULTA").count() > 0:
        return True

    return False


def obtener_campos_fecha(page):
    # Intento 1: por name
    try:
        desde = page.locator('input[name="fecha_desde"]').first
        hasta = page.locator('input[name="fecha_hasta"]').first
        if desde.count() > 0 and hasta.count() > 0:
            return desde, hasta
    except Exception:
        pass

    # Intento 2: inputs visibles tipo fecha/text
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

    # Intento 3: primeros 2 inputs visibles
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

    try:
        campo_desde, campo_hasta = obtener_campos_fecha(page)
        debug("Campos de fecha detectados")

        ok1 = fill_input_robusto(campo_desde, fecha_iso_a_ui(FECHA_DESDE), FECHA_DESDE)
        page.wait_for_timeout(300)
        ok2 = fill_input_robusto(campo_hasta, fecha_iso_a_ui(FECHA_HASTA), FECHA_HASTA)

        if not ok1 or not ok2:
            raise RuntimeError("No se pudo completar uno de los campos de fecha")

        debug("Fechas OK")
    except Exception as e:
        debug(f"Error fechas: {e}")
        return False

    try:
        checkbox = None

        try:
            checkbox = page.get_by_label("CONSIDERAR TODOS LOS CLIENTES", exact=False)
            if checkbox.count() == 0:
                checkbox = None
        except Exception:
            checkbox = None

        if checkbox is None:
            try:
                label = page.get_by_text("CONSIDERAR TODOS LOS CLIENTES", exact=False).first
                contenedor = label.locator("xpath=ancestor::*[self::label or self::div][1]")
                candidato = contenedor.locator('input[type="checkbox"]').first
                if candidato.count() > 0:
                    checkbox = candidato
            except Exception:
                checkbox = None

        if checkbox is None:
            try:
                checkbox = page.locator('input[type="checkbox"]').first
            except Exception:
                checkbox = None

        if checkbox and checkbox.count() > 0:
            try:
                checkbox.scroll_into_view_if_needed(timeout=3000)
            except Exception:
                pass

            try:
                if not checkbox.is_checked():
                    checkbox.click(force=True, timeout=3000)
                    page.wait_for_timeout(500)
            except Exception:
                try:
                    checkbox.check(force=True, timeout=3000)
                    page.wait_for_timeout(500)
                except Exception:
                    try:
                        checkbox.evaluate(
                            """(el) => {
                                el.checked = true;
                                el.dispatchEvent(new Event('input', { bubbles: true }));
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                                el.dispatchEvent(new Event('click', { bubbles: true }));
                            }"""
                        )
                        page.wait_for_timeout(500)
                    except Exception:
                        pass

            try:
                marcado = checkbox.is_checked()
            except Exception:
                marcado = False

            if marcado:
                debug("Checkbox 'considerar todos los clientes' marcado")
            else:
                debug("No se pudo confirmar la casilla de todos los clientes")
        else:
            debug("No encontré la casilla de todos los clientes")
    except Exception:
        debug("No se pudo marcar la casilla de todos los clientes")

    page.wait_for_timeout(1000)

    if not click_boton_consulta(page):
        debug("No pude clickear REALIZAR CONSULTA, probando fallback por Enter...")
        try:
            campo_hasta.press("Enter", timeout=3000)
            page.wait_for_timeout(6000)
            debug("Consulta lanzada por Enter en fecha hasta")
            return True
        except Exception:
            pass

        try:
            page.keyboard.press("Enter")
            page.wait_for_timeout(6000)
            debug("Consulta lanzada por Enter general")
            return True
        except Exception:
            pass

        try:
            page.evaluate(
                """() => {
                    const form = document.querySelector('form');
                    if (form) form.submit();
                }"""
            )
            page.wait_for_timeout(6000)
            debug("Consulta lanzada por submit de formulario")
            return True
        except Exception:
            pass

        debug("Error al consultar: no pude lanzar la consulta")
        return False

    debug("Consulta lanzada")
    page.wait_for_timeout(6000)
    return True


# =========================
# PDF
# =========================
def obtener_url_pdf(context, page) -> str:
    debug("Esperando que aparezca el enlace del PDF...")
    patrones_pdf = [
        ".pdf",
        "ventas_detallado",
        "rep_ventas",
        "/reportes_fuente/",
        "salidas",
        "jasper",
    ]

    def es_url_pdf(url: str) -> bool:
        url_l = (url or "").lower()
        return any(p in url_l for p in patrones_pdf)

    def buscar_en_pagina(pag) -> str | None:
        try:
            for selector in [
                'a[href*=".pdf"]',
                'a[href*="ventas_detallado"]',
                'a[href*="rep_ventas"]',
                'a[href*="/reportes_fuente/"]',
                'a[href*="salidas"]',
                'iframe[src*=".pdf"]',
                'iframe[src*="reportes_fuente"]',
                'iframe[src*="jasper"]',
                'embed[src*=".pdf"]',
                'object[data*=".pdf"]',
            ]:
                elementos = pag.locator(selector)
                total = elementos.count()
                for i in range(total):
                    el = elementos.nth(i)
                    href = (
                        el.get_attribute("href")
                        or el.get_attribute("src")
                        or el.get_attribute("data")
                        or ""
                    )
                    if href and es_url_pdf(href):
                        return urljoin(ERP_URL, href)
        except Exception:
            pass

        try:
            anchors = pag.locator("a")
            total = anchors.count()
            for i in range(total):
                anchor = anchors.nth(i)
                texto = limpiar_texto(anchor.inner_text()).lower()
                href = anchor.get_attribute("href") or ""
                if href and (es_url_pdf(href) or "enlace" in texto):
                    return urljoin(ERP_URL, href)
        except Exception:
            pass

        try:
            if es_url_pdf(pag.url):
                return pag.url
        except Exception:
            pass

        return None

    for _ in range(90):
        try:
            if page.get_by_text("enlace", exact=False).count() > 0:
                debug("Texto de enlace detectado")
                break
        except Exception:
            pass

        try:
            if buscar_en_pagina(page):
                debug("Elemento de reporte detectado")
                break
        except Exception:
            pass

        try:
            body = limpiar_texto(page.locator("body").inner_text()).lower()
            if "presione en este enlace" in body or "este enlace" in body:
                debug("Mensaje de enlace detectado en pantalla")
                break
        except Exception:
            pass

        page.wait_for_timeout(1000)

    for _ in range(20):
        try:
            url_directa = buscar_en_pagina(page)
            if url_directa:
                debug(f"URL PDF encontrada en página actual: {url_directa}")
                return url_directa
        except Exception:
            pass
        page.wait_for_timeout(1000)

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

                if es_url_pdf(url_popup):
                    debug(f"URL PDF encontrada por nueva pestaña: {url_popup}")
                    return url_popup

                url_popup_scan = buscar_en_pagina(nueva_pagina)
                if url_popup_scan:
                    debug(f"URL PDF encontrada dentro de la nueva pestaña: {url_popup_scan}")
                    return url_popup_scan
        except Exception:
            pass

    try:
        anchors = page.locator("a")
        total = anchors.count()
        for i in range(total):
            try:
                texto = (anchors.nth(i).inner_text() or "").strip()
                href = anchors.nth(i).get_attribute("href")
                if href and (es_url_pdf(href) or "enlace" in texto.lower()):
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
                if es_url_pdf(url_actual):
                    debug(f"URL PDF encontrada en páginas abiertas: {url_actual}")
                    return url_actual
                url_scan = buscar_en_pagina(p)
                if url_scan:
                    debug(f"URL PDF encontrada inspeccionando páginas abiertas: {url_scan}")
                    return url_scan
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
# PARSER VENTAS
# =========================
PATRON_CLIENTE = re.compile(r"^CLIENTE\s*:\s*(.+)$", re.IGNORECASE)
PATRON_FECHA = re.compile(r"(\d{2}/\d{2}/\d{4})")
PATRON_OBS = re.compile(r"^OBS\s*[:\.]\s*(.*)$", re.IGNORECASE)
PATRON_PRODUCTO = re.compile(
    r"^(?P<producto>.+?)\s+(?P<cantidad>\d[\d\.,]*)\s+(?P<precio>\d[\d\.,]*)\s+"
    r"(?P<exentas>\d[\d\.,]*)\s+(?P<grav5>\d[\d\.,]*)\s+(?P<grav10>\d[\d\.,]*)\s+(?P<total>\d[\d\.,]*)$"
)


def es_basura_venta(linea: str) -> bool:
    linea = limpiar_texto(linea)

    if not linea:
        return True

    exactas = {
        "SOL HUEVOS",
        "VENTAS POR CLIENTE REMOTE -",
        "Criterios",
        "Producto Cantidad Precio Exentas Gravadas 5% Gravadas 10% Total",
        "Producto",
        "Cantidad",
        "Precio",
        "Total",
        "ventas_detallado.jrxml",
    }

    if linea in exactas:
        return True

    if linea.startswith("Desde :"):
        return True
    if linea.startswith("Hasta :"):
        return True
    if linea.startswith("Total :"):
        return True
    if linea.startswith("Total Factura :"):
        return True
    if linea.startswith("TOTAL DEL CLIENTE"):
        return True
    if linea.startswith("TOTAL GENERAL"):
        return True
    if linea.startswith("Numero:"):
        return True

    return False


def limpiar_cliente(cliente_crudo: str) -> str:
    cliente_crudo = limpiar_texto(cliente_crudo)
    cliente_crudo = re.sub(r"^\d[\d\.\-]*\s+", "", cliente_crudo).strip()
    cliente_crudo = re.sub(r"\s*-\s*\d[\d\-\.]*$", "", cliente_crudo).strip()
    return cliente_crudo


def limpiar_obs_sucursal(obs: str) -> str:
    return limpiar_texto(obs)


def cliente_requiere_ocr(cliente: str) -> bool:
    return limpiar_texto(cliente).upper() in CLIENTES_SUPER_OCR


def extraer_datos_pdf(pdf_path):
    filas = []

    if not os.path.exists(pdf_path):
        raise RuntimeError(f"No existe el PDF: {pdf_path}")

    cliente_actual = ""
    fecha_actual = ""
    sucursal_actual = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages):
            texto = page.extract_text()
            if not texto:
                continue

            lineas = [limpiar_texto(x) for x in texto.split("\n")]
            sucursales_ocr_pagina = None
            obs_idx = -1

            for linea in lineas:
                if not linea:
                    continue

                m_cliente = PATRON_CLIENTE.match(linea)
                if m_cliente:
                    cliente_actual = limpiar_cliente(m_cliente.group(1))
                    fecha_actual = ""
                    sucursal_actual = ""
                    continue

                m_fecha = PATRON_FECHA.search(linea)
                if m_fecha:
                    fecha_actual = m_fecha.group(1)
                    continue

                m_obs = PATRON_OBS.match(linea)
                if m_obs:
                    obs_idx += 1
                    obs = limpiar_texto(m_obs.group(1))
                    if obs:
                        sucursal_actual = limpiar_obs_sucursal(obs)
                    else:
                        if sucursales_ocr_pagina is None and cliente_requiere_ocr(cliente_actual):
                            sucursales_ocr_pagina = extraer_sucursales_ocr(pdf_path, page_index)
                        if sucursales_ocr_pagina is None:
                            sucursales_ocr_pagina = []
                        if obs_idx < len(sucursales_ocr_pagina):
                            sucursal_actual = sucursales_ocr_pagina[obs_idx]
                        else:
                            sucursal_actual = ""
                    continue

                if es_basura_venta(linea):
                    continue

                m_prod = PATRON_PRODUCTO.match(linea)
                if m_prod and cliente_actual and fecha_actual:
                    producto = limpiar_texto(m_prod.group("producto"))
                    cantidad = cantidad_a_numero(m_prod.group("cantidad"))
                    precio = monto_a_int(m_prod.group("precio"))
                    total = monto_a_int(m_prod.group("total"))

                    filas.append([
                        cliente_actual,
                        fecha_actual,
                        sucursal_actual,
                        producto,
                        cantidad,
                        precio,
                        total,
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
        "FECHA",
        "Sucursal",
        "Producto",
        "Cantidad",
        "Precio",
        "Total",
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

            if not abrir_reporte_ventas(page):
                debug("NAV FAIL")
                return

            debug("REP. VENTAS OK")

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
