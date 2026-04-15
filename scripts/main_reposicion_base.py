import calendar
import os

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials


# =========================
# CONFIG GOOGLE SHEETS
# =========================
SPREADSHEET_ID = "1B21HlZ5MBVj6Orc1rkLM1_mZycXLDEJDIT9OF9Gw9Kw"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CREDS_FILE = os.getenv(
    "GOOGLE_CREDS_FILE",
    "automatizacion-sol-huevos-2-f02d718cb7d4.json",
)

SHEET_SOURCE = "movimientos_final"
SHEET_DEST = "reposicion_base"
MESES_BASE = 3


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


MESES_ES = {
    1: "ENE",
    2: "FEB",
    3: "MAR",
    4: "ABR",
    5: "MAY",
    6: "JUN",
    7: "JUL",
    8: "AGO",
    9: "SEP",
    10: "OCT",
    11: "NOV",
    12: "DIC",
}


# =========================
# HELPERS
# =========================
def debug(msg: str):
    print(msg, flush=True)


def limpiar_texto(texto):
    if texto is None:
        return ""
    return " ".join(str(texto).split()).strip()


def cliente_es_supermercado(cliente: str) -> bool:
    return limpiar_texto(cliente) in CLIENTES_SUPER


def get_client():
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def etiqueta_periodo(anio: int, mes: int) -> str:
    return f"{MESES_ES.get(mes, str(mes))}-{anio}"


def obtener_periodos_base(df: pd.DataFrame):
    periodos = (
        df[["AÑO", "MES"]]
        .dropna()
        .drop_duplicates()
        .sort_values(["AÑO", "MES"])
    )

    if periodos.empty:
        return []

    ultimos = periodos.tail(MESES_BASE).values.tolist()
    return [(int(anio), int(mes)) for anio, mes in ultimos]


def columnas_finales():
    columnas = [
        "PERIODO_BASE",
        "CLIENTE",
        "Sucursal",
        "Producto",
    ]

    for slot in range(1, MESES_BASE + 1):
        columnas.extend([
            f"MES_{slot}_LABEL",
            f"MES_{slot}_VENTA_UND",
            f"MES_{slot}_NC_UND",
            f"MES_{slot}_NETO_UND",
        ])

    columnas.extend([
        "VENTA_UND_PERIODO",
        "NC_UND_PERIODO",
        "NETO_UND_PERIODO",
        "PROMEDIO_MENSUAL_UND",
        "PROMEDIO_SEMANAL_UND",
        "MESES_CON_DATOS",
    ])
    return columnas


def calcular_semanas_periodo(periodos):
    dias = 0
    for anio, mes in periodos:
        dias += calendar.monthrange(anio, mes)[1]
    return dias / 7


def main():
    client = get_client()
    sheet = client.open_by_key(SPREADSHEET_ID)

    debug("Leyendo movimientos_final...")
    data = sheet.worksheet(SHEET_SOURCE).get_all_records()
    df = pd.DataFrame(data)

    if df.empty:
        debug("movimientos_final está vacío")
        return

    required_cols = [
        "TIPO",
        "CLIENTE",
        "AÑO",
        "MES",
        "Sucursal_normalizada",
        "Producto_normalizado",
        "Cantidad",
    ]
    faltantes = [c for c in required_cols if c not in df.columns]
    if faltantes:
        raise RuntimeError(f"Faltan columnas en movimientos_final: {faltantes}")

    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)
    df["AÑO"] = pd.to_numeric(df["AÑO"], errors="coerce")
    df["MES"] = pd.to_numeric(df["MES"], errors="coerce")

    for col in ["TIPO", "CLIENTE", "Sucursal_normalizada", "Producto_normalizado"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    df = df[df["CLIENTE"].apply(cliente_es_supermercado)].copy()
    df["Sucursal_normalizada"] = df["Sucursal_normalizada"].replace("", "OTROS")
    df.loc[df["Sucursal_normalizada"].isna(), "Sucursal_normalizada"] = "OTROS"

    periodos_base = obtener_periodos_base(df)
    if not periodos_base:
        debug("No hay períodos disponibles para construir reposicion_base")
        return

    periodos_validos = set(periodos_base)
    df = df[df.apply(lambda row: (int(row["AÑO"]), int(row["MES"])) in periodos_validos, axis=1)].copy()

    df["PERIODO_LABEL"] = df.apply(
        lambda row: etiqueta_periodo(int(row["AÑO"]), int(row["MES"])),
        axis=1,
    )

    df["VENTA_UND"] = df.apply(
        lambda row: row["Cantidad"] if row["TIPO"] == "VENTA" else 0,
        axis=1,
    )
    df["NC_UND"] = df.apply(
        lambda row: abs(row["Cantidad"]) if row["TIPO"] == "NC" else 0,
        axis=1,
    )
    df["NETO_UND"] = df["VENTA_UND"] - df["NC_UND"]

    agrupado = df.groupby(
        ["CLIENTE", "Sucursal_normalizada", "Producto_normalizado", "PERIODO_LABEL"],
        as_index=False,
    ).agg({
        "VENTA_UND": "sum",
        "NC_UND": "sum",
        "NETO_UND": "sum",
    })

    orden_periodos = [etiqueta_periodo(anio, mes) for anio, mes in periodos_base]
    mapa_slots = {periodo: idx + 1 for idx, periodo in enumerate(orden_periodos)}
    agrupado["SLOT"] = agrupado["PERIODO_LABEL"].map(mapa_slots)

    pivot = agrupado.pivot_table(
        index=["CLIENTE", "Sucursal_normalizada", "Producto_normalizado"],
        columns="SLOT",
        values=["VENTA_UND", "NC_UND", "NETO_UND"],
        aggfunc="sum",
        fill_value=0,
    )

    pivot.columns = [f"MES_{slot}_{metrica}" for metrica, slot in pivot.columns]
    pivot = pivot.reset_index()
    pivot = pivot.rename(columns={
        "Sucursal_normalizada": "Sucursal",
        "Producto_normalizado": "Producto",
    })

    for slot in range(1, MESES_BASE + 1):
        pivot[f"MES_{slot}_LABEL"] = orden_periodos[slot - 1] if slot <= len(orden_periodos) else ""
        for metrica in ["VENTA_UND", "NC_UND", "NETO_UND"]:
            col = f"MES_{slot}_{metrica}"
            if col not in pivot.columns:
                pivot[col] = 0.0

    venta_cols = [f"MES_{slot}_VENTA_UND" for slot in range(1, MESES_BASE + 1)]
    nc_cols = [f"MES_{slot}_NC_UND" for slot in range(1, MESES_BASE + 1)]
    neto_cols = [f"MES_{slot}_NETO_UND" for slot in range(1, MESES_BASE + 1)]
    cantidad_periodos = len(orden_periodos)
    semanas_periodo = calcular_semanas_periodo(periodos_base)

    pivot["PERIODO_BASE"] = " / ".join(orden_periodos)
    pivot["VENTA_UND_PERIODO"] = pivot[venta_cols].sum(axis=1)
    pivot["NC_UND_PERIODO"] = pivot[nc_cols].sum(axis=1)
    pivot["NETO_UND_PERIODO"] = pivot[neto_cols].sum(axis=1)
    pivot["PROMEDIO_MENSUAL_UND"] = (pivot["NETO_UND_PERIODO"] / cantidad_periodos).round(0).astype(int)
    pivot["PROMEDIO_SEMANAL_UND"] = (pivot["NETO_UND_PERIODO"] / semanas_periodo).round(0).astype(int)
    pivot["MESES_CON_DATOS"] = (pivot[neto_cols] != 0).sum(axis=1)

    base_final = pivot[columnas_finales()].copy()
    base_final = base_final.sort_values(
        ["CLIENTE", "Sucursal", "PROMEDIO_MENSUAL_UND"],
        ascending=[True, True, False],
    )

    columnas_texto = {"PERIODO_BASE", "CLIENTE", "Sucursal", "Producto"} | {
        f"MES_{slot}_LABEL" for slot in range(1, MESES_BASE + 1)
    }
    for col in base_final.columns:
        if col not in columnas_texto:
            base_final[col] = pd.to_numeric(base_final[col], errors="coerce").fillna(0)

    columnas_enteras = [
        "VENTA_UND_PERIODO",
        "NC_UND_PERIODO",
        "NETO_UND_PERIODO",
        "PROMEDIO_MENSUAL_UND",
        "PROMEDIO_SEMANAL_UND",
        "MESES_CON_DATOS",
    ]
    for slot in range(1, MESES_BASE + 1):
        columnas_enteras.extend([
            f"MES_{slot}_VENTA_UND",
            f"MES_{slot}_NC_UND",
            f"MES_{slot}_NETO_UND",
        ])

    for col in columnas_enteras:
        if col in base_final.columns:
            base_final[col] = base_final[col].round(0).astype(int)

    debug(f"Período base: {' / '.join(orden_periodos)}")
    debug(f"Filas agrupadas: {len(base_final)}")

    try:
        ws = sheet.worksheet(SHEET_DEST)
        ws.clear()
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=SHEET_DEST, rows="3000", cols="40")

    ws.update([base_final.columns.values.tolist()] + base_final.values.tolist())
    debug("Datos subidos a reposicion_base")


if __name__ == "__main__":
    main()
