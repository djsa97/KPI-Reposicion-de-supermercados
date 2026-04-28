import calendar
import os
import re
import unicodedata

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials


SPREADSHEET_ID = "1B21HlZ5MBVj6Orc1rkLM1_mZycXLDEJDIT9OF9Gw9Kw"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDS_FILE = os.getenv(
    "GOOGLE_CREDS_FILE",
    os.path.join(BASE_DIR, "automatizacion-sol-huevos-2-f02d718cb7d4.json"),
)
SHEET_SOURCE = "reposicion_base"
SHEET_DEST = "control_dashboard"
CLIENTES_EXCLUIDOS = set()

SUCURSALES_VALIDAS = {
    "ALIMENTOS ESPECIALES S.A.": ["ESPANA", "LAURELES", "MOLAS", "OTROS", "PERSERVERANCIA"],
    "Biggie S.A.": ["DENIS ROA", "GENARO ROMERO", "LAS PALMERAS", "VILLA MORRA", "HERRERA", "MOLAS Y TEBICUARY", "OTROS", "SANTA TERESA", "PACHECO", "PRIMER PRESIDENTE"],
    "CADENA REAL S.A.": ["ACCESO SUR", "BAJA AVE", "FDO DE LA MORA", "FELIX BOGADO", "NEMBY 2", "ÑEMBY1", "OTROS", "RUTA1", "RUTA2", "SAN VICENTE", "VILLA MORRA"],
    "CAFSA S.A.": ["LAMBARE", "OTROS", "PINEDO", "PRIMER PRESIDENTE", "SAUSALITO"],
    "CEBRE S.A.": ["SUPERMERCADO PACIFICO CEBRE S.A."],
    "DELIVERY HERO DMART PARAGUAY S.A -": ["JOSE ASUNCION FLORES", "LAMBARE", "LUQUE", "OTROS", "SAN LORENZO"],
    "DELIVERY HERO DMART PARAGUAY S.A": ["JOSE ASUNCION FLORES", "LAMBARE", "LUQUE", "OTROS", "SAN LORENZO"],
    "LT Sociedad Anonima": ["CENTRAL", "COSTA V.H.", "EMBOSCADA", "LIMPIO", "OTROS", "VILLA HAYES"],
    "RETAIL S.A.": ["DELIMARKET", "DENIS ROA", "ESPANA", "HIPERSEIS", "JAPON", "LOS LAURELES", "MBURUKUYA", "MUNDIMARK", "NEGRITA", "OTROS", "PORTAL", "SAN BERNARDINO", "STOCK CAPIATA RUTA 2", "VILLETA", "STOCK MARIANO ROQUE ALONSO 2", "STOCK MARTIN LEDESMA", "TOTAL"],
    "SALEMMA RETAIL SA": ["CARMELITAS", "OTROS"],
    "SUPER BOX S. A.": ["LUQUE"],
    "SUPERMERCADO VILLA SOFIA S.A.": ["LUQUE", "CENTRAL", "OTROS"],
}

ALIASES_SUCURSALES = {
    "ALIMENTOS ESPECIALES S.A.": {
        "MOLAS LOPEZ": "MOLAS",
        "CASA RICA MOLAS LOPEZ": "MOLAS",
        "CASA RICA - MOLAS LOPEZ": "MOLAS",
        "ESPANA": "ESPANA",
        "CASA RICA ESPANA": "ESPANA",
        "CASA RICA - ESPANA": "ESPANA",
        "LAURELES": "LAURELES",
        "PERSERVERANCIA": "PERSERVERANCIA",
        "PERSEVERANCIA": "PERSERVERANCIA",
        "CASA RICA PERSEVERANCIA": "PERSERVERANCIA",
        "CASA RICA - PERSEVERANCIA": "PERSERVERANCIA",
    },
    "Biggie S.A.": {
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
        "SANTA TERESA": "SANTA TERESA",
        "STA TERESA": "SANTA TERESA",
        "PACHECO": "PACHECO",
        "PACHEXO": "PACHECO",
        "PRIMER PRESIDENTE": "PRIMER PRESIDENTE",
        "FALTANTE": "OTROS",
    },
    "CADENA REAL S.A.": {
        "ACCESO": "ACCESO SUR",
        "ACCESO SUR": "ACCESO SUR",
        "BAJA AVE": "BAJA AVE",
        "FDO DE LA MORA": "FDO DE LA MORA",
        "FERNANDO": "FDO DE LA MORA",
        "FELIX BOGADO": "FELIX BOGADO",
        "NEMBY2": "NEMBY 2",
        "NEMBY 2": "NEMBY 2",
        "NEMBY1": "ÑEMBY1",
        "ÑEMBY1": "ÑEMBY1",
        "RUTA1": "RUTA1",
        "RUTA 1": "RUTA1",
        "RUTA2": "RUTA2",
        "RUTA 2": "RUTA2",
        "SAN VICENTE": "SAN VICENTE",
        "VILLA MORRA": "VILLA MORRA",
    },
    "CAFSA S.A.": {
        "LAMBARE": "LAMBARE",
        "PINEDO": "PINEDO",
        "PRIMER PRESIDENTE": "PRIMER PRESIDENTE",
        "SAUSALITO": "SAUSALITO",
        "ARETE PRIMER PRESIDENTE": "PRIMER PRESIDENTE",
        "ARETE SAUSALITO": "SAUSALITO",
        "ARETE LAMBARE": "LAMBARE",
        "ARETE PINEDO": "PINEDO",
    },
    "CEBRE S.A.": {
        "PACIFICO": "SUPERMERCADO PACIFICO CEBRE S.A.",
        "SUPERMERCADO PACIFICO CEBRE S.A.": "SUPERMERCADO PACIFICO CEBRE S.A.",
    },
    "DELIVERY HERO DMART PARAGUAY S.A -": {
        "JOSE ASUNCION FLORES": "JOSE ASUNCION FLORES",
        "LAMBARE": "LAMBARE",
        "LUQUE": "LUQUE",
        "SAN LORENZO": "SAN LORENZO",
    },
    "DELIVERY HERO DMART PARAGUAY S.A": {
        "JOSE ASUNCION FLORES": "JOSE ASUNCION FLORES",
        "LAMBARE": "LAMBARE",
        "LUQUE": "LUQUE",
        "SAN LORENZO": "SAN LORENZO",
    },
    "LT Sociedad Anonima": {
        "CENTRAL": "CENTRAL",
        "LT CENTRAL": "CENTRAL",
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
        "SUPSERSEIS DENIS ROA": "DENIS ROA",
        "SUPERSEIS DENIS ROA": "DENIS ROA",
        "ESPANA": "ESPANA",
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


def debug(msg: str):
    print(msg, flush=True)


def get_client():
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def producto_relevante(producto: str) -> bool:
    texto = str(producto).upper()
    return ("HUEVO" in texto) or ("PLANCHA" in texto)


def normalizar_texto_base(texto: str) -> str:
    texto = str(texto or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = " ".join(texto.replace("_", " ").split())
    return texto


def normalizar_sucursal_dashboard(cliente: str, sucursal: str) -> str:
    cliente = str(cliente or "").strip()
    texto = str(sucursal or "").strip()
    texto_up = texto.upper()
    texto_base = normalizar_texto_base(texto)

    if not texto:
        return "OTROS"

    patrones_invalidos = [
        "HUEVO VENCIDO",
        "HUEVO",
        "VENCIDO",
        "POR CANTIDAD",
        "SOLIC",
        "NRO ",
        "NRO.",
        "NRO",
        "CANTIDAD",
        "AVERIADO",
        "AVERIADOS",
        "STOCK",
    ]
    if any(pat in texto_up for pat in patrones_invalidos):
        return "OTROS"
    if texto_up.isdigit():
        return "OTROS"

    sucursales_validas = set(SUCURSALES_VALIDAS.get(cliente, []))
    aliases_cliente = ALIASES_SUCURSALES.get(cliente, {})

    if texto_up in sucursales_validas:
        return texto_up

    if texto_up in aliases_cliente:
        canonica = aliases_cliente[texto_up]
        return canonica if canonica in sucursales_validas else "OTROS"

    for alias, canonica in aliases_cliente.items():
        alias_base = normalizar_texto_base(alias)
        if alias_base and alias_base in texto_base:
            return canonica

    return texto_up if texto_up else "OTROS"


def semanas_del_mes(label: str) -> float:
    label = str(label or "").upper()
    if label.startswith("S"):
        return 1.0
    if label.startswith(("ENE", "MAR", "MAY", "JUL", "AGO", "OCT", "DIC")):
        return 31 / 7
    if label.startswith(("ABR", "JUN", "SEP", "NOV")):
        return 30 / 7
    if label.startswith("FEB"):
        return 28 / 7
    return 30 / 7


def semanas_slot(df: pd.DataFrame, slot: int, label: str) -> float:
    col = f"MES_{slot}_SEMANAS"
    if col in df.columns and not df.empty:
        semanas = pd.to_numeric(df[col], errors="coerce").fillna(0)
        valor = float(semanas.iloc[0]) if not semanas.empty else 0
        if valor > 0:
            return valor
    return semanas_del_mes(label)


def cargar_reposicion_base(sheet) -> pd.DataFrame:
    data = sheet.worksheet(SHEET_SOURCE).get_all_records()
    df = pd.DataFrame(data)
    if df.empty:
        return df

    numeric_cols = [
        "VENTA_UND_PERIODO",
        "NC_UND_PERIODO",
        "NETO_UND_PERIODO",
        "PROMEDIO_MENSUAL_UND",
        "PROMEDIO_SEMANAL_UND",
        "MESES_CON_DATOS",
    ]
    for col in df.columns:
        if re.fullmatch(r"MES_\d+_(VENTA|NC|NETO)_UND", col):
            numeric_cols.append(col)
        if re.fullmatch(r"MES_\d+_SEMANAS", col):
            numeric_cols.append(col)

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    for col in ["PERIODO_BASE", "CLIENTE", "Sucursal", "Producto"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    for col in df.columns:
        if re.fullmatch(r"MES_\d+_LABEL", col):
            df[col] = df[col].fillna("").astype(str).str.strip()

    return df


def slots_disponibles(df: pd.DataFrame) -> list[int]:
    slots = []
    for col in df.columns:
        match = re.fullmatch(r"MES_(\d+)_LABEL", col)
        if not match:
            continue
        slot = int(match.group(1))
        if not df.empty and str(df[col].iloc[0]).strip():
            slots.append(slot)
    return sorted(slots)


def build_control_dashboard(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    df = df[~df["CLIENTE"].isin(CLIENTES_EXCLUIDOS)].copy()
    df = df[~df["Producto"].str.contains("CARBON", case=False, na=False)].copy()
    df = df[df["Producto"].apply(producto_relevante)].copy()
    df["Sucursal_dashboard"] = df.apply(
        lambda row: normalizar_sucursal_dashboard(row["CLIENTE"], row["Sucursal"]),
        axis=1,
    )

    labels = []
    for slot in slots_disponibles(df):
        label = df[f"MES_{slot}_LABEL"].iloc[0] if f"MES_{slot}_LABEL" in df.columns and not df.empty else ""
        if label:
            labels.append((slot, label))

    rows = []
    for producto in sorted(df["Producto"].dropna().unique().tolist()):
        subset = df[df["Producto"] == producto].copy()
        subset_dash = subset.copy()

        row = {
            "PRODUCTO": producto,
            "PERIODO_BASE": subset["PERIODO_BASE"].iloc[0] if not subset.empty else "",
            "FILAS_BASE": len(subset),
            "FILAS_DASH": len(subset_dash),
        }

        prom_cols = []
        for slot, label in labels:
            semanas = semanas_slot(df, slot, label)
            neto_base = int(round(subset[f"MES_{slot}_NETO_UND"].sum()))
            neto_dash = int(round(subset_dash[f"MES_{slot}_NETO_UND"].sum()))
            excluido = neto_base - neto_dash
            prom_base = int(round(neto_base / semanas))
            prom_dash = int(round(neto_dash / semanas))

            row[f"{label} NETO_BASE"] = neto_base
            row[f"{label} NETO_DASH"] = neto_dash
            row[f"{label} EXCLUIDO_OTROS"] = excluido
            row[f"{label} PROM_SEMANAL_BASE"] = prom_base
            row[f"{label} PROM_SEMANAL_DASH"] = prom_dash
            prom_cols.append(f"{label} PROM_SEMANAL_DASH")

        row["PROM_PERIODOS_DASH"] = (
            int(round(pd.Series([row[col] for col in prom_cols]).mean()))
            if prom_cols else 0
        )
        row["CONTROL"] = "OK" if all(row[f"{label} EXCLUIDO_OTROS"] == 0 for _, label in labels) else "REVISAR"
        rows.append(row)

    control = pd.DataFrame(rows)
    if control.empty:
        return control

    columnas = ["PRODUCTO", "PERIODO_BASE", "FILAS_BASE", "FILAS_DASH"]
    for _, label in labels:
        columnas.extend([
            f"{label} NETO_BASE",
            f"{label} NETO_DASH",
            f"{label} EXCLUIDO_OTROS",
            f"{label} PROM_SEMANAL_BASE",
            f"{label} PROM_SEMANAL_DASH",
        ])
    columnas.extend(["PROM_PERIODOS_DASH", "CONTROL"])
    control = control[columnas].sort_values(["PROM_PERIODOS_DASH", "PRODUCTO"], ascending=[False, True])
    return control


def subir_control(sheet, control_df: pd.DataFrame):
    try:
        ws = sheet.worksheet(SHEET_DEST)
        ws.clear()
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=SHEET_DEST, rows="200", cols="60")

    if control_df.empty:
        ws.update([["SIN_DATOS"]])
        return

    ws.update([control_df.columns.tolist()] + control_df.astype(object).fillna("").values.tolist())


def main():
    client = get_client()
    sheet = client.open_by_key(SPREADSHEET_ID)
    debug("Leyendo reposicion_base...")
    df = cargar_reposicion_base(sheet)
    if df.empty:
        debug("reposicion_base está vacía")
        return

    control = build_control_dashboard(df)
    subir_control(sheet, control)
    debug(f"Control generado: {len(control)} filas")
    debug(f"Datos subidos a {SHEET_DEST}")


if __name__ == "__main__":
    main()
