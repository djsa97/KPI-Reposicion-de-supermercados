import re
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials


# =========================
# CONFIG GOOGLE SHEETS
# =========================
JSON_PATH = "automatizacion-sol-huevos-2-f02d718cb7d4.json"
SHEET_ID = "1B21HlZ5MBVj6Orc1rkLM1_mZycXLDEJDIT9OF9Gw9Kw"

SHEET_VENTAS = "movimientos_raw"
SHEET_NC = "notas_credito_raw"
SHEET_FINAL = "movimientos_final"
SHEET_SUCURSALES = "catalogo_sucursales"


SUCURSALES_ALIAS = {
    "BIGGIE S.A.": {
        "PACHEXO": "PACHECO",
        "BIGGIE PACHECO": "PACHECO",
        "BIGGIE LILLO HERRERA": "LILIO HERRERA",
        "LIILLO HERRERA": "LILIO HERRERA",
        "LILLO HERRERA": "LILIO HERRERA",
        "BIGGIE LILIO HERRERA": "LILIO HERRERA",
        "BIGGIE LIILLO HERRERA": "LILIO HERRERA",
        "SUCURSA SANTA TERESA": "SANTA TERESA Y MIRANDA",
    },
}

SUCURSALES_VALIDAS = {
    "ALIMENTOS ESPECIALES S.A.": {"ESPANA", "LAURELES", "MOLAS", "OTROS", "PERSERVERANCIA"},
    "BIGGIE S.A.": {"DENIS ROA", "GENARO ROMERO", "LAS PALMERAS", "VILLA MORRA", "HERRERA", "MOLAS Y TEBICUARY", "OTROS", "SANTA TERESA"},
    "CADENA REAL S.A.": {"ACCESO SUR", "BAJA AVE", "FDO DE LA MORA", "FELIX BOGADO", "NEMBY 2", "ÑEMBY1", "OTROS", "RUTA1", "RUTA2", "SAN VICENTE", "VILLA MORRA"},
    "CAFSA S.A.": {"LAMBARE", "OTROS", "PINEDO", "PRIMER PRESIDENTE", "SAUSALITO"},
    "CEBRE S.A.": {"SUPERMERCADO PACIFICO CEBRE S.A."},
    "DELIVERY HERO DMART PARAGUAY S.A": {"JOSE ASUNCION FLORES", "LAMBARE", "LUQUE", "OTROS", "SAN LORENZO"},
    "DELIVERY HERO DMART PARAGUAY S.A -": {"JOSE ASUNCION FLORES", "LAMBARE", "LUQUE", "OTROS", "SAN LORENZO"},
    "LT SOCIEDAD ANONIMA": {"CENTRAL", "COSTA V.H.", "EMBOSCADA", "LIMPIO", "OTROS", "VILLA HAYES"},
    "RETAIL S.A.": {"DELIMARKET", "DENIS ROA", "ESPANA", "HIPERSEIS", "JAPON", "LOS LAURELES", "MBURUKUYA", "MUNDIMARK", "NEGRITA", "OTROS", "PORTAL", "SAN BERNARDINO", "STOCK CAPIATA RUTA 2", "VILLETA", "STOCK MARIANO ROQUE ALONSO 2", "STOCK MARTIN LEDESMA", "TOTAL"},
    "SALEMMA RETAIL SA": {"CARMELITAS", "OTROS"},
    "SUPER BOX S. A.": {"LUQUE"},
    "SUPERMERCADO VILLA SOFIA S.A.": {"LUQUE", "CENTRAL", "OTROS"},
}

ALIASES_VALIDOS = {
    "ALIMENTOS ESPECIALES S.A.": {
        "ESPAÑA": "ESPANA",
        "ESPANA": "ESPANA",
        "CASA RICA ESPANA": "ESPANA",
        "MOLAS": "MOLAS",
        "MOLAS LOPEZ": "MOLAS",
        "CASA RICA MOLAS LOPEZ": "MOLAS",
        "LAURELES": "LAURELES",
        "PERSERVERANCIA": "PERSERVERANCIA",
        "PERSEVERANCIA": "PERSERVERANCIA",
        "CASA RICA PERSEVERANCIA": "PERSERVERANCIA",
        "ALIMENTOS ESPECIALES": "OTROS",
        "AVERIADOS": "OTROS",
        "AVERIADO": "OTROS",
        "EN MAL ESTADO": "OTROS",
        "PS AVERIADOS": "OTROS",
        "VENCIDOS AVERIADOS": "OTROS",
    },
    "BIGGIE S.A.": {
        "DENIS ROA": "DENIS ROA",
        "GENARO ROMERO": "GENARO ROMERO",
        "LAS PALMERAS": "LAS PALMERAS",
        "PALMERAS": "LAS PALMERAS",
        "VILLA MORRA": "VILLA MORRA",
        "LILIO HERRERA": "HERRERA",
        "LILLO HERRERA": "HERRERA",
        "LIILLO HERRERA": "HERRERA",
        "HERRERA": "HERRERA",
        "MOLAS": "MOLAS Y TEBICUARY",
        "MOLAS Y TEBICUARY": "MOLAS Y TEBICUARY",
        "STA TERESA": "SANTA TERESA",
        "SANTA TERESA": "SANTA TERESA",
        "PACHECO": "OTROS",
        "PACHEXO": "OTROS",
        "FALTANTE": "OTROS",
    },
    "CADENA REAL S.A.": {
        "ACCESO SUR": "ACCESO SUR",
        "ACCESO": "ACCESO SUR",
        "BAJA AVE": "BAJA AVE",
        "FDO DE LA MORA": "FDO DE LA MORA",
        "FERNANDO": "FDO DE LA MORA",
        "FELIX BOGADO": "FELIX BOGADO",
        "NEMBY 1": "ÑEMBY1",
        "NEMBY1": "ÑEMBY1",
        "ÑEMBY1": "ÑEMBY1",
        "NEMBY 2": "NEMBY 2",
        "NEMBY2": "NEMBY 2",
        "RUTA1": "RUTA1",
        "RUTA 1": "RUTA1",
        "RUTA2": "RUTA2",
        "RUTA 2": "RUTA2",
        "SAN VICENTE": "SAN VICENTE",
        "VILLA MORRA": "VILLA MORRA",
        "BAJA POR AVERIADO": "OTROS",
        "DIFERENCIA CANTIDAD": "OTROS",
    },
    "CAFSA S.A.": {
        "LAMBARE": "LAMBARE",
        "LAMBARÉ": "LAMBARE",
        "PINEDO": "PINEDO",
        "PN": "PINEDO",
        "PRIMER PRESIDENTE": "PRIMER PRESIDENTE",
        "PP": "PRIMER PRESIDENTE",
        "SAUSALITO": "SAUSALITO",
        "CAFSA": "OTROS",
        "AVERIADO": "OTROS",
        "AVERIADOS Y VENCIDOS": "OTROS",
        "VENCIDOS": "OTROS",
    },
    "CEBRE S.A.": {
        "PACIFICO": "SUPERMERCADO PACIFICO CEBRE S.A.",
        "SUPERMERCADO PACIFICO CEBRE S.A.": "SUPERMERCADO PACIFICO CEBRE S.A.",
    },
    "DELIVERY HERO DMART PARAGUAY S.A": {
        "JOSE ASUNCION FLORES": "JOSE ASUNCION FLORES",
        "LAMBARE": "LAMBARE",
        "LUQUE": "LUQUE",
        "SAN LORENZO": "SAN LORENZO",
    },
    "DELIVERY HERO DMART PARAGUAY S.A -": {
        "JOSE ASUNCION FLORES": "JOSE ASUNCION FLORES",
        "LAMBARE": "LAMBARE",
        "LUQUE": "LUQUE",
        "SAN LORENZO": "SAN LORENZO",
    },
    "LT SOCIEDAD ANONIMA": {
        "CENTRAL": "CENTRAL",
        "LT CENTRAL": "CENTRAL",
        "COSTA V H": "COSTA V.H.",
        "COSTA V.H.": "COSTA V.H.",
        "LT EXPRESS COSTA": "COSTA V.H.",
        "EMBOSCADA": "EMBOSCADA",
        "LIMPIO": "LIMPIO",
        "LT LIMPIO": "LIMPIO",
        "VILLA HAYES": "VILLA HAYES",
        "LT VILLA HAYES": "VILLA HAYES",
    },
    "RETAIL S.A.": {
        "DELIMARKET": "DELIMARKET",
        "DENIS ROA": "DENIS ROA",
        "SUPERSEIS DENIS ROA": "DENIS ROA",
        "SUPSERSEIS DENIS ROA": "DENIS ROA",
        "ESPANA": "ESPANA",
        "ESPAÑA": "ESPANA",
        "HIPERSEIS": "HIPERSEIS",
        "JAPON": "JAPON",
        "LOS LAURELES": "LOS LAURELES",
        "LAURELES": "LOS LAURELES",
        "MBURUKUYA": "MBURUKUYA",
        "MBURUCUYA": "MBURUKUYA",
        "MUNDIMARK": "MUNDIMARK",
        "NEGRITA": "NEGRITA",
        "PORTAL": "PORTAL",
        "EL PORTAL": "PORTAL",
        "SAN BERNARDINO": "SAN BERNARDINO",
        "STOCK CAPIATA RUTA 2": "STOCK CAPIATA RUTA 2",
        "RETAIL STOCK CAPIATA": "STOCK CAPIATA RUTA 2",
        "VILLETA": "VILLETA",
        "STOCK MARIANO ROQUE ALONSO 2": "STOCK MARIANO ROQUE ALONSO 2",
        "STOCK MARIANO ROQUE": "STOCK MARIANO ROQUE ALONSO 2",
        "STOCK MARTIN LEDESMA": "STOCK MARTIN LEDESMA",
        "TOTAL": "TOTAL",
    },
    "SALEMMA RETAIL SA": {
        "CARMELITAS": "CARMELITAS",
    },
    "SUPER BOX S. A.": {
        "LUQUE": "LUQUE",
    },
    "SUPERMERCADO VILLA SOFIA S.A.": {
        "LUQUE": "LUQUE",
        "CENTRAL": "CENTRAL",
        "SAJONIA": "OTROS",
    },
}


# =========================
# UTILS
# =========================
def debug(msg: str):
    print(msg, flush=True)


def limpiar_texto(texto):
    if texto is None:
        return ""
    return " ".join(str(texto).split()).strip()


def a_float(valor):
    if valor is None or valor == "":
        return 0.0
    texto = str(valor).strip().replace(",", ".")
    try:
        return float(texto)
    except Exception:
        return 0.0


def a_int(valor):
    if valor is None or valor == "":
        return 0
    texto = str(valor).strip().replace(".", "").replace(",", "")
    try:
        return int(float(texto))
    except Exception:
        return 0


def parsear_fecha(fecha_str: str):
    fecha_str = limpiar_texto(fecha_str)
    return datetime.strptime(fecha_str, "%d/%m/%Y")


def normalizar_texto_catalogo(texto: str) -> str:
    t = limpiar_texto(texto).upper()
    t = t.replace(".", " ")
    t = t.replace(",", " ")
    t = t.replace("-", " ")
    t = t.replace("SUCURSAL", " ")
    t = t.replace("SUC.", " ")
    t = t.replace("DEPOSITO", " ")
    return limpiar_texto(t)


def normalizar_cliente_key(cliente: str) -> str:
    return limpiar_texto(cliente).upper()


# =========================
# NORMALIZACIÓN PRODUCTOS
# =========================
def normalizar_producto(producto: str) -> str:
    p = limpiar_texto(producto).upper()

    # limpiar códigos
    p = re.sub(r"COD\.?\s*\d+", "", p).strip()
    p = re.sub(r"COD\d+", "", p).strip()

    if "HUEVOS POR UNIDAD" in p:
        return "HUEVOS POR UNIDAD"

    if "PLANCHA 6" in p or "PLANCHA 6 HUEVOS" in p:
        return "PLANCHA 6 TIPO A"

    if "PLANCHA 12" in p or "PLANCHA 12 HUEVOS" in p:
        return "PLANCHA 12 TIPO A"

    if "PLANCHA 20" in p or "PLANCHAS 20 HUEVOS" in p:
        return "PLANCHA 20 TIPO A"

    if "TIPO B" in p:
        return "PLANCHA 30 TIPO B"

    if "EMPAQUETADO" in p or "SUPER EMPAQUETADO" in p:
        return "PLANCHA 30 TIPO A EMPAQUETADO"

    if "GRANEL" in p:
        return "PLANCHA 30 TIPO A GRANEL"

    if "PLANCHA 30" in p or "PLANCHAS 30" in p:
        return "PLANCHA 30 TIPO A"

    return p


# =========================
# NORMALIZACIÓN SUCURSALES
# =========================
def cargar_catalogo_sucursales(spreadsheet):
    try:
        ws = spreadsheet.worksheet(SHEET_SUCURSALES)
    except gspread.exceptions.WorksheetNotFound:
        return {}

    rows = ws.get_all_records()
    catalogo = {}

    for row in rows:
        cliente = normalizar_texto_catalogo(row.get("CLIENTE", ""))
        alias = normalizar_texto_catalogo(row.get("ALIAS", ""))
        canonica = limpiar_texto(row.get("SUCURSAL_CANONICA", ""))

        if not cliente or not alias or not canonica:
            continue

        catalogo[(cliente, alias)] = canonica

    return catalogo


def normalizar_sucursal(cliente: str, sucursal: str, catalogo_sucursales=None) -> str:
    s = limpiar_texto(sucursal)
    if not s:
        return "OTROS"

    cliente_key = normalizar_cliente_key(cliente)
    sucursal_key = normalizar_texto_catalogo(sucursal)

    if catalogo_sucursales:
        canonica = catalogo_sucursales.get((normalizar_texto_catalogo(cliente), sucursal_key))
        if canonica:
            return canonica

    validas = SUCURSALES_VALIDAS.get(cliente_key, {"OTROS"})
    aliases = ALIASES_VALIDOS.get(cliente_key, {})
    alias_genericos = SUCURSALES_ALIAS.get(cliente_key, {})

    if sucursal_key in validas:
        return sucursal_key

    if sucursal_key in aliases:
        canonica = aliases[sucursal_key]
        return canonica if canonica in validas else "OTROS"

    if sucursal_key in alias_genericos:
        canonica = alias_genericos[sucursal_key]
        canonica = aliases.get(canonica, canonica)
        return canonica if canonica in validas else "OTROS"

    for alias, canonica in aliases.items():
        if alias and alias in sucursal_key:
            return canonica if canonica in validas else "OTROS"

    return "OTROS"


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
    return spreadsheet


def leer_hoja(spreadsheet, nombre_hoja):
    ws = spreadsheet.worksheet(nombre_hoja)
    data = ws.get_all_records()
    return data


def escribir_hoja(spreadsheet, nombre_hoja, filas):
    ws = spreadsheet.worksheet(nombre_hoja)
    ws.clear()

    encabezados = [[
        "TIPO",
        "CLIENTE",
        "FECHA",
        "AÑO",
        "MES",
        "SEMANA",
        "Sucursal_original",
        "Sucursal_normalizada",
        "Producto_original",
        "Producto_normalizado",
        "Cantidad",
        "Precio",
        "Total",
    ]]
    ws.update("A1", encabezados)

    if filas:
        ws.update(f"A2:M{len(filas)+1}", filas)


# =========================
# CONSOLIDACIÓN
# =========================
def consolidar_ventas(data_ventas, catalogo_sucursales=None):
    filas = []

    for row in data_ventas:
        tipo = "VENTA"
        cliente = limpiar_texto(row.get("CLIENTE", ""))
        fecha = limpiar_texto(row.get("FECHA", ""))
        sucursal_original = limpiar_texto(
            row.get("Sucursal_homologada", "") or row.get("Sucursal", "")
        )
        producto_original = limpiar_texto(row.get("Producto", ""))

        cantidad = a_float(row.get("Cantidad", 0))
        precio = a_int(row.get("Precio", 0))
        total = a_int(row.get("Total", 0))

        if not cliente or not fecha or not producto_original:
            continue

        dt = parsear_fecha(fecha)
        anio = dt.year
        mes = dt.month
        semana = dt.isocalendar().week

        sucursal_normalizada = normalizar_sucursal(cliente, sucursal_original, catalogo_sucursales)
        producto_normalizado = normalizar_producto(producto_original)

        filas.append([
            tipo,
            cliente,
            fecha,
            anio,
            mes,
            semana,
            sucursal_original,
            sucursal_normalizada,
            producto_original,
            producto_normalizado,
            cantidad,
            precio,
            total,
        ])

    return filas


def consolidar_nc(data_nc, catalogo_sucursales=None):
    filas = []

    for row in data_nc:
        tipo = "NC"
        cliente = limpiar_texto(row.get("CLIENTE", ""))
        fecha = limpiar_texto(row.get("FECHA", ""))
        sucursal_original = limpiar_texto(
            row.get("Sucursal_homologada", "") or row.get("Sucursal", "")
        )
        producto_original = limpiar_texto(row.get("Producto", ""))

        cantidad = a_float(row.get("Cantidad", 0))
        total = a_int(row.get("Total", 0))

        # NC: negativos
        cantidad = -abs(cantidad)
        total = -abs(total)

        # en NCR no tenés precio separado confiable
        precio = 0

        if not cliente or not fecha or not producto_original:
            continue

        dt = parsear_fecha(fecha)
        anio = dt.year
        mes = dt.month
        semana = dt.isocalendar().week

        sucursal_normalizada = normalizar_sucursal(cliente, sucursal_original, catalogo_sucursales)
        producto_normalizado = normalizar_producto(producto_original)

        filas.append([
            tipo,
            cliente,
            fecha,
            anio,
            mes,
            semana,
            sucursal_original,
            sucursal_normalizada,
            producto_original,
            producto_normalizado,
            cantidad,
            precio,
            total,
        ])

    return filas


# =========================
# MAIN
# =========================
def main():
    debug("Conectando a Google Sheets...")
    spreadsheet = conectar_google_sheet()
    catalogo_sucursales = cargar_catalogo_sucursales(spreadsheet)

    debug("Leyendo ventas...")
    data_ventas = leer_hoja(spreadsheet, SHEET_VENTAS)
    debug(f"Ventas leídas: {len(data_ventas)}")

    debug("Leyendo notas de crédito...")
    data_nc = leer_hoja(spreadsheet, SHEET_NC)
    debug(f"NC leídas: {len(data_nc)}")

    debug("Consolidando ventas...")
    filas_ventas = consolidar_ventas(data_ventas, catalogo_sucursales)
    debug(f"Ventas consolidadas: {len(filas_ventas)}")

    debug("Consolidando NC...")
    filas_nc = consolidar_nc(data_nc, catalogo_sucursales)
    debug(f"NC consolidadas: {len(filas_nc)}")

    filas_finales = filas_ventas + filas_nc

    filas_finales.sort(key=lambda x: (
        x[1],  # cliente
        datetime.strptime(x[2], "%d/%m/%Y"),  # fecha
        x[9],  # producto normalizado
    ))

    debug(f"Escribiendo movimientos_final: {len(filas_finales)} filas...")
    escribir_hoja(spreadsheet, SHEET_FINAL, filas_finales)

    debug("OK consolidado terminado")


if __name__ == "__main__":
    main()
