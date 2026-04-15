from collections import defaultdict

import gspread
from google.oauth2.service_account import Credentials


# =========================
# CONFIG GOOGLE SHEETS
# =========================
JSON_PATH = "automatizacion-sol-huevos-2-f02d718cb7d4.json"
SHEET_ID = "1B21HlZ5MBVj6Orc1rkLM1_mZycXLDEJDIT9OF9Gw9Kw"

SHEET_MOV_FINAL = "movimientos_final"
SHEET_ACUERDOS = "acuerdos_raw"
SHEET_DASHBOARD_BASE = "dashboard_base"


# =========================
# CLIENTES SUPERMERCADOS
# =========================
CLIENTES_SUPER = {
    "SALEMMA RETAIL SA",
    "SUPER BOX S. A.",
    "EMPRENDIMIENTOS JC S.A.",
    "SUPERMERCADO VILLA SOFIA S.A.",
    "CADENA REAL S.A.",
    "LT Sociedad Anonima",
    "CEBRE S.A.",
    "D.A. S.R.L.",
    "CAFSA S.A.",
    "ALIMENTOS ESPECIALES S.A.",
    "TODO CARNE S.A.",
    "MGI MISION S.A.",
    "DELIVERY HERO DMART PARAGUAY S.A",
    "RETAIL S.A.",
    "Biggie  S.A.",
    "Biggie S.A.",
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


def cliente_es_supermercado(cliente: str) -> bool:
    cliente = limpiar_texto(cliente)
    return cliente in CLIENTES_SUPER


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
    return ws.get_all_records()


def escribir_hoja(spreadsheet, nombre_hoja, filas):
    ws = spreadsheet.worksheet(nombre_hoja)
    ws.clear()

    headers = [[
        "ORDEN_CLIENTE",
        "NIVEL",
        "CLIENTE",
        "Sucursal",
        "Producto",
        "VENTA",
        "NC",
        "ACUERDOS",
        "NETO",
    ]]
    ws.update("A1", headers)

    if filas:
        ws.update(f"A2:I{len(filas)+1}", filas)


# =========================
# ACUERDOS
# =========================
def cargar_acuerdos_por_cliente(data_acuerdos):
    acuerdos = {}

    for row in data_acuerdos:
        cliente = limpiar_texto(row.get("CLIENTE", ""))
        monto = a_int(row.get("ACUERDOS", 0))

        if not cliente:
            continue

        acuerdos[cliente] = monto

    return acuerdos


# =========================
# DASHBOARD BASE
# =========================
def construir_dashboard_base(data_mov, acuerdos_por_cliente):
    # acumuladores
    total_cliente = defaultdict(lambda: {"venta": 0, "nc": 0})
    total_sucursal = defaultdict(lambda: {"venta": 0, "nc": 0})
    total_producto = defaultdict(lambda: {"venta": 0, "nc": 0})

    # recorrer movimientos_final
    for row in data_mov:
        cliente = limpiar_texto(row.get("CLIENTE", ""))
        sucursal = limpiar_texto(row.get("Sucursal_normalizada", ""))
        producto = limpiar_texto(row.get("Producto_normalizado", ""))
        tipo = limpiar_texto(row.get("TIPO", ""))

        total = a_int(row.get("Total", 0))

        if not cliente_es_supermercado(cliente):
            continue

        if not sucursal:
            sucursal = "OTROS"

        if tipo == "VENTA":
            total_cliente[cliente]["venta"] += total
            total_sucursal[(cliente, sucursal)]["venta"] += total
            total_producto[(cliente, sucursal, producto)]["venta"] += total

        elif tipo == "NC":
            # en movimientos_final ya debería venir negativo
            total_cliente[cliente]["nc"] += total
            total_sucursal[(cliente, sucursal)]["nc"] += total
            total_producto[(cliente, sucursal, producto)]["nc"] += total

    # construir filas ordenadas
    filas = []
    clientes_ordenados = sorted(total_cliente.keys())

    orden_cliente = 1

    for cliente in clientes_ordenados:
        venta_cliente = total_cliente[cliente]["venta"]
        nc_cliente = total_cliente[cliente]["nc"]
        acuerdos_cliente = acuerdos_por_cliente.get(cliente, 0)
        neto_cliente = venta_cliente + nc_cliente - acuerdos_cliente

        # fila cliente
        filas.append([
            orden_cliente,
            "CLIENTE",
            cliente,
            "",
            "",
            venta_cliente,
            nc_cliente,
            acuerdos_cliente,
            neto_cliente,
        ])

        # sucursales del cliente
        sucursales_cliente = sorted([
            suc for (cli, suc) in total_sucursal.keys()
            if cli == cliente
        ])

        for sucursal in sucursales_cliente:
            venta_suc = total_sucursal[(cliente, sucursal)]["venta"]
            nc_suc = total_sucursal[(cliente, sucursal)]["nc"]
            neto_suc = venta_suc + nc_suc

            filas.append([
                orden_cliente,
                "SUCURSAL",
                cliente,
                sucursal,
                "",
                venta_suc,
                nc_suc,
                0,
                neto_suc,
            ])

            # productos de esa sucursal
            productos_suc = sorted([
                prod for (cli, suc, prod) in total_producto.keys()
                if cli == cliente and suc == sucursal
            ])

            for producto in productos_suc:
                venta_prod = total_producto[(cliente, sucursal, producto)]["venta"]
                nc_prod = total_producto[(cliente, sucursal, producto)]["nc"]
                neto_prod = venta_prod + nc_prod

                filas.append([
                    orden_cliente,
                    "PRODUCTO",
                    cliente,
                    sucursal,
                    producto,
                    venta_prod,
                    nc_prod,
                    0,
                    neto_prod,
                ])

        orden_cliente += 1

    return filas


# =========================
# MAIN
# =========================
def main():
    debug("Conectando a Google Sheets...")
    spreadsheet = conectar_google_sheet()

    debug("Leyendo movimientos_final...")
    data_mov = leer_hoja(spreadsheet, SHEET_MOV_FINAL)
    debug(f"movimientos_final leídos: {len(data_mov)}")

    debug("Leyendo acuerdos_raw...")
    data_acuerdos = leer_hoja(spreadsheet, SHEET_ACUERDOS)
    debug(f"acuerdos_raw leídos: {len(data_acuerdos)}")

    debug("Cargando acuerdos por cliente...")
    acuerdos_por_cliente = cargar_acuerdos_por_cliente(data_acuerdos)
    debug(f"Clientes con acuerdos: {len(acuerdos_por_cliente)}")

    debug("Construyendo dashboard_base...")
    filas = construir_dashboard_base(data_mov, acuerdos_por_cliente)
    debug(f"Filas dashboard_base: {len(filas)}")

    debug("Escribiendo dashboard_base...")
    escribir_hoja(spreadsheet, SHEET_DASHBOARD_BASE, filas)

    debug("OK dashboard_base terminado")


if __name__ == "__main__":
    main()