import calendar
import os
from datetime import datetime
import math

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


def obtener_slots_base(df: pd.DataFrame):
    fechas = pd.to_datetime(df["FECHA"], format="%d/%m/%Y", errors="coerce").dropna()
    if fechas.empty:
        return []

    ultimo_dia = fechas.max()
    ultimo_mes = ultimo_dia.replace(day=1)
    meses_disponibles = sorted({
        fecha.replace(day=1)
        for fecha in fechas
    })

    slots = []
    for inicio_mes in meses_disponibles:
        anio = int(inicio_mes.year)
        mes = int(inicio_mes.month)
        dias_mes = calendar.monthrange(anio, mes)[1]

        if inicio_mes < ultimo_mes:
            slots.append({
                "label": etiqueta_periodo(anio, mes),
                "kind": "month",
                "anio": anio,
                "mes": mes,
                "days": dias_mes,
            })
            continue

        cantidad_semanas = max(1, math.ceil(int(ultimo_dia.day) / 7))
        for semana_idx in range(cantidad_semanas):
            dia_inicio = semana_idx * 7 + 1
            dia_fin = min(dia_inicio + 6, dias_mes, int(ultimo_dia.day))
            if dia_inicio > dia_fin:
                continue
            slots.append({
                "label": f"S{semana_idx + 1} {MESES_ES.get(mes, str(mes))}-{anio}",
                "kind": "range",
                "start": datetime(anio, mes, dia_inicio),
                "end": datetime(anio, mes, dia_fin),
                "days": dia_fin - dia_inicio + 1,
            })

    return slots


def columnas_finales(total_slots: int):
    columnas = [
        "PERIODO_BASE",
        "CLIENTE",
        "Sucursal",
        "Producto",
    ]

    for slot in range(1, total_slots + 1):
        columnas.extend([
            f"MES_{slot}_LABEL",
            f"MES_{slot}_SEMANAS",
            f"MES_{slot}_VENTA_UND",
            f"MES_{slot}_NC_UND",
            f"MES_{slot}_NETO_UND",
            f"MES_{slot}_VENTA_MONTO",
            f"MES_{slot}_NC_MONTO",
            f"MES_{slot}_NETO_MONTO",
        ])

    columnas.extend([
        "VENTA_UND_PERIODO",
        "NC_UND_PERIODO",
        "NETO_UND_PERIODO",
        "PROMEDIO_MENSUAL_UND",
        "PROMEDIO_SEMANAL_UND",
        "VENTA_MONTO_PERIODO",
        "NC_MONTO_PERIODO",
        "NETO_MONTO_PERIODO",
        "PROMEDIO_MENSUAL_MONTO",
        "MESES_CON_DATOS",
    ])
    return columnas


def calcular_semanas_periodo(slots):
    return sum(slot["days"] for slot in slots) / 7


def asignar_slot(fecha: datetime, slots):
    for slot in slots:
        if slot["kind"] == "month":
            if fecha.year == slot["anio"] and fecha.month == slot["mes"]:
                return slot["label"]
            continue

        if slot["start"] <= fecha <= slot["end"]:
            return slot["label"]

    return None


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
        "CLIENTE_PADRE",
        "FECHA",
        "AÑO",
        "MES",
        "Sucursal_normalizada",
        "Producto_normalizado",
        "Cantidad",
        "Total",
    ]
    faltantes = [c for c in required_cols if c not in df.columns]
    if faltantes:
        raise RuntimeError(f"Faltan columnas en movimientos_final: {faltantes}")

    df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0)
    df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0)
    df["AÑO"] = pd.to_numeric(df["AÑO"], errors="coerce")
    df["MES"] = pd.to_numeric(df["MES"], errors="coerce")
    df["FECHA"] = df["FECHA"].fillna("").astype(str).str.strip()
    df["FECHA_DT"] = pd.to_datetime(df["FECHA"], format="%d/%m/%Y", errors="coerce")

    for col in ["TIPO", "CLIENTE", "CLIENTE_PADRE", "Sucursal_normalizada", "Producto_normalizado"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    df["CLIENTE_PADRE"] = df["CLIENTE_PADRE"].where(
        df["CLIENTE_PADRE"].ne(""),
        df["CLIENTE"]
    )
    df = df[df["CLIENTE_PADRE"].apply(cliente_es_supermercado)].copy()
    df["Sucursal_normalizada"] = df["Sucursal_normalizada"].replace("", "OTROS")
    df.loc[df["Sucursal_normalizada"].isna(), "Sucursal_normalizada"] = "OTROS"

    slots_base = obtener_slots_base(df)
    if not slots_base:
        debug("No hay períodos disponibles para construir reposicion_base")
        return

    df["PERIODO_LABEL"] = df["FECHA_DT"].apply(lambda fecha: asignar_slot(fecha, slots_base) if pd.notna(fecha) else None)
    df = df[df["PERIODO_LABEL"].notna()].copy()
    if df.empty:
        debug("No hay filas dentro de ENE/FEB/MAR y S1/S2 de abril")
        return

    df["VENTA_UND"] = df.apply(
        lambda row: row["Cantidad"] if row["TIPO"] == "VENTA" else 0,
        axis=1,
    )
    df["NC_UND"] = df.apply(
        lambda row: abs(row["Cantidad"]) if row["TIPO"] == "NC" else 0,
        axis=1,
    )
    df["NETO_UND"] = df["VENTA_UND"] - df["NC_UND"]
    df["VENTA_MONTO"] = df.apply(
        lambda row: row["Total"] if row["TIPO"] == "VENTA" else 0,
        axis=1,
    )
    df["NC_MONTO"] = df.apply(
        lambda row: abs(row["Total"]) if row["TIPO"] == "NC" else 0,
        axis=1,
    )
    df["NETO_MONTO"] = df["VENTA_MONTO"] - df["NC_MONTO"]

    agrupado = df.groupby(
        ["CLIENTE", "Sucursal_normalizada", "Producto_normalizado", "PERIODO_LABEL"],
        as_index=False,
    ).agg({
        "VENTA_UND": "sum",
        "NC_UND": "sum",
        "NETO_UND": "sum",
        "VENTA_MONTO": "sum",
        "NC_MONTO": "sum",
        "NETO_MONTO": "sum",
    })

    orden_periodos = [slot["label"] for slot in slots_base]
    mapa_slots = {periodo: idx + 1 for idx, periodo in enumerate(orden_periodos)}
    agrupado["SLOT"] = agrupado["PERIODO_LABEL"].map(mapa_slots)

    pivot = agrupado.pivot_table(
        index=["CLIENTE", "Sucursal_normalizada", "Producto_normalizado"],
        columns="SLOT",
        values=["VENTA_UND", "NC_UND", "NETO_UND", "VENTA_MONTO", "NC_MONTO", "NETO_MONTO"],
        aggfunc="sum",
        fill_value=0,
    )

    pivot.columns = [f"MES_{slot}_{metrica}" for metrica, slot in pivot.columns]
    pivot = pivot.reset_index()
    pivot = pivot.rename(columns={
        "Sucursal_normalizada": "Sucursal",
        "Producto_normalizado": "Producto",
    })

    total_slots = len(orden_periodos)
    for slot in range(1, total_slots + 1):
        pivot[f"MES_{slot}_LABEL"] = orden_periodos[slot - 1] if slot <= len(orden_periodos) else ""
        pivot[f"MES_{slot}_SEMANAS"] = slots_base[slot - 1]["days"] / 7 if slot <= len(slots_base) else 0
        for metrica in ["VENTA_UND", "NC_UND", "NETO_UND", "VENTA_MONTO", "NC_MONTO", "NETO_MONTO"]:
            col = f"MES_{slot}_{metrica}"
            if col not in pivot.columns:
                pivot[col] = 0.0

    venta_cols = [f"MES_{slot}_VENTA_UND" for slot in range(1, total_slots + 1)]
    nc_cols = [f"MES_{slot}_NC_UND" for slot in range(1, total_slots + 1)]
    neto_cols = [f"MES_{slot}_NETO_UND" for slot in range(1, total_slots + 1)]
    venta_monto_cols = [f"MES_{slot}_VENTA_MONTO" for slot in range(1, total_slots + 1)]
    nc_monto_cols = [f"MES_{slot}_NC_MONTO" for slot in range(1, total_slots + 1)]
    neto_monto_cols = [f"MES_{slot}_NETO_MONTO" for slot in range(1, total_slots + 1)]
    cantidad_periodos = len(orden_periodos)
    semanas_periodo = calcular_semanas_periodo(slots_base)

    pivot["PERIODO_BASE"] = " / ".join(orden_periodos)
    pivot["VENTA_UND_PERIODO"] = pivot[venta_cols].sum(axis=1)
    pivot["NC_UND_PERIODO"] = pivot[nc_cols].sum(axis=1)
    pivot["NETO_UND_PERIODO"] = pivot[neto_cols].sum(axis=1)
    pivot["PROMEDIO_MENSUAL_UND"] = (pivot["NETO_UND_PERIODO"] / cantidad_periodos).round(0).astype(int)
    pivot["PROMEDIO_SEMANAL_UND"] = (pivot["NETO_UND_PERIODO"] / semanas_periodo).round(0).astype(int)
    pivot["VENTA_MONTO_PERIODO"] = pivot[venta_monto_cols].sum(axis=1)
    pivot["NC_MONTO_PERIODO"] = pivot[nc_monto_cols].sum(axis=1)
    pivot["NETO_MONTO_PERIODO"] = pivot[neto_monto_cols].sum(axis=1)
    pivot["PROMEDIO_MENSUAL_MONTO"] = (pivot["NETO_MONTO_PERIODO"] / cantidad_periodos).round(0).astype(int)
    pivot["MESES_CON_DATOS"] = (pivot[neto_cols] != 0).sum(axis=1)

    base_final = pivot[columnas_finales(total_slots)].copy()
    base_final = base_final.sort_values(
        ["CLIENTE", "Sucursal", "PROMEDIO_MENSUAL_MONTO"],
        ascending=[True, True, False],
    )

    columnas_texto = {"PERIODO_BASE", "CLIENTE", "Sucursal", "Producto"} | {
        f"MES_{slot}_LABEL" for slot in range(1, total_slots + 1)
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
        "VENTA_MONTO_PERIODO",
        "NC_MONTO_PERIODO",
        "NETO_MONTO_PERIODO",
        "PROMEDIO_MENSUAL_MONTO",
        "MESES_CON_DATOS",
    ]
    for slot in range(1, total_slots + 1):
        columnas_enteras.extend([
            f"MES_{slot}_VENTA_UND",
            f"MES_{slot}_NC_UND",
            f"MES_{slot}_NETO_UND",
            f"MES_{slot}_VENTA_MONTO",
            f"MES_{slot}_NC_MONTO",
            f"MES_{slot}_NETO_MONTO",
        ])

    for col in columnas_enteras:
        if col in base_final.columns:
            base_final[col] = base_final[col].round(0).astype(int)

    for slot in range(1, total_slots + 1):
        col = f"MES_{slot}_SEMANAS"
        if col in base_final.columns:
            base_final[col] = pd.to_numeric(base_final[col], errors="coerce").fillna(0).round(4)

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
