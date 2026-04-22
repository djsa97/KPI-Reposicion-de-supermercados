import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials
import os
import unicodedata


SPREADSHEET_ID = "1B21HlZ5MBVj6Orc1rkLM1_mZycXLDEJDIT9OF9Gw9Kw"
STOCK_SPREADSHEET_ID = "1wHioBhy8usSOY-M5OTW_bfIQrFTP5BO4r4LM0SCswYo"
STOCK_WORKSHEET_GID = 897103869
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_FILE = os.getenv(
    "GOOGLE_CREDS_FILE",
    os.path.join(BASE_DIR, "automatizacion-sol-huevos-2-f02d718cb7d4.json"),
)
WORKSHEET_NAME = "reposicion_base"
MESES_BASE = 5
CLIENTES_EXCLUIDOS = set()
COL_PROM_UND = "Prom. períodos"
COL_PROM_MONTO = "Prom. períodos monto"
COL_DEPOSITO = "Depósito actual"

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


@st.cache_resource
def get_client():
    service_account_info = None
    try:
        secrets_dict = st.secrets.to_dict()
        service_account_info = secrets_dict.get("gcp_service_account")
    except Exception:
        service_account_info = None

    if service_account_info:
        creds = Credentials.from_service_account_info(
            dict(service_account_info),
            scopes=SCOPES,
        )
    else:
        creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_data(ttl=120)
def load_data():
    client = get_client()
    sheet = client.open_by_key(SPREADSHEET_ID)
    data = sheet.worksheet(WORKSHEET_NAME).get_all_records()
    df = pd.DataFrame(data)

    if df.empty:
        return df

    numeric_cols = [
        "PROMEDIO_MENSUAL_UND",
        "PROMEDIO_SEMANAL_UND",
        "VENTA_UND_PERIODO",
        "NC_UND_PERIODO",
        "NETO_UND_PERIODO",
        "MESES_CON_DATOS",
    ]
    for slot in range(1, MESES_BASE + 1):
        numeric_cols.extend([
            f"MES_{slot}_VENTA_UND",
            f"MES_{slot}_NC_UND",
            f"MES_{slot}_NETO_UND",
            f"MES_{slot}_VENTA_MONTO",
            f"MES_{slot}_NC_MONTO",
            f"MES_{slot}_NETO_MONTO",
        ])
    numeric_cols.extend([
        "VENTA_MONTO_PERIODO",
        "NC_MONTO_PERIODO",
        "NETO_MONTO_PERIODO",
        "PROMEDIO_MENSUAL_MONTO",
    ])

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    for col in ["PERIODO_BASE", "CLIENTE", "Sucursal", "Producto"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    for slot in range(1, MESES_BASE + 1):
        label_col = f"MES_{slot}_LABEL"
        if label_col in df.columns:
            df[label_col] = df[label_col].fillna("").astype(str).str.strip()

    return df


def mapear_producto_a_columna_stock(producto: str) -> str | None:
    texto = str(producto or "").upper().strip()
    if "30 TIPO B" in texto:
        return "TIPO_B"
    if "30 TIPO A" in texto:
        return "PAQ_30"
    if "12 TIPO A" in texto:
        return "PAQ_12"
    if "20 TIPO A" in texto:
        return "PAQ_20"
    if "6 TIPO A" in texto:
        return "PAQ_6"
    return None


def normalizar_supermercado_stock(texto: str) -> tuple[str, str]:
    raw = str(texto or "").strip()
    base = normalizar_texto_base(raw)

    if not base:
        return "OTROS", "OTROS"

    def has(*tokens):
        return all(token in base for token in tokens)

    if base.startswith("arete") or "arete " in base:
        if "sausalito" in base:
            return "CAFSA S.A.", "SAUSALITO"
        if "pinedo" in base:
            return "CAFSA S.A.", "PINEDO"
        if "lambare" in base:
            return "CAFSA S.A.", "LAMBARE"
        if has("primer", "presidente"):
            return "CAFSA S.A.", "PRIMER PRESIDENTE"
        return "CAFSA S.A.", "OTROS"

    if has("casa", "rica"):
        if "laureles" in base:
            return "ALIMENTOS ESPECIALES S.A.", "LAURELES"
        if "molas" in base:
            return "ALIMENTOS ESPECIALES S.A.", "MOLAS"
        if "espana" in base:
            return "ALIMENTOS ESPECIALES S.A.", "ESPANA"
        if "perseverancia" in base or "perserverancia" in base:
            return "ALIMENTOS ESPECIALES S.A.", "PERSERVERANCIA"
        return "ALIMENTOS ESPECIALES S.A.", "OTROS"

    if base.startswith("lt ") or base.startswith("lt"):
        if has("villa", "hayes"):
            return "LT Sociedad Anonima", "VILLA HAYES"
        if "costa" in base:
            return "LT Sociedad Anonima", "COSTA V.H."
        if "emboscada" in base:
            return "LT Sociedad Anonima", "EMBOSCADA"
        if "limpio" in base:
            return "LT Sociedad Anonima", "LIMPIO"
        if "central" in base:
            return "LT Sociedad Anonima", "CENTRAL"
        return "LT Sociedad Anonima", "OTROS"

    if "super box" in base:
        return "SUPER BOX S. A.", "LUQUE"

    if has("villa", "sofia"):
        if "luque" in base:
            return "SUPERMERCADO VILLA SOFIA S.A.", "LUQUE"
        if "central" in base:
            return "SUPERMERCADO VILLA SOFIA S.A.", "CENTRAL"
        if "sajonia" in base:
            return "SUPERMERCADO VILLA SOFIA S.A.", "OTROS"
        return "SUPERMERCADO VILLA SOFIA S.A.", "OTROS"

    if "biggie" in base:
        if has("denis", "roa"):
            return "Biggie S.A.", "DENIS ROA"
        if has("genaro", "romero"):
            return "Biggie S.A.", "GENARO ROMERO"
        if "palmeras" in base:
            return "Biggie S.A.", "LAS PALMERAS"
        if "morra" in base:
            return "Biggie S.A.", "VILLA MORRA"
        if "herrera" in base:
            return "Biggie S.A.", "HERRERA"
        if "molas" in base:
            return "Biggie S.A.", "MOLAS Y TEBICUARY"
        if "santa teresa" in base or "sta teresa" in base:
            return "Biggie S.A.", "SANTA TERESA"
        if "pacheco" in base or "pachexo" in base:
            return "Biggie S.A.", "PACHECO"
        if has("primer", "presidente"):
            return "Biggie S.A.", "PRIMER PRESIDENTE"
        return "Biggie S.A.", "OTROS"

    if "dmart" in base or "delivery hero" in base:
        if has("jose", "asuncion", "flores"):
            return "DELIVERY HERO DMART PARAGUAY S.A", "JOSE ASUNCION FLORES"
        if "lambare" in base:
            return "DELIVERY HERO DMART PARAGUAY S.A", "LAMBARE"
        if "luque" in base:
            return "DELIVERY HERO DMART PARAGUAY S.A", "LUQUE"
        if has("san", "lorenzo"):
            return "DELIVERY HERO DMART PARAGUAY S.A", "SAN LORENZO"
        return "DELIVERY HERO DMART PARAGUAY S.A", "OTROS"

    if "salemma" in base:
        if "carmelitas" in base:
            return "SALEMMA RETAIL SA", "CARMELITAS"
        return "SALEMMA RETAIL SA", "OTROS"

    if "pacifico" in base or "cebre" in base:
        return "CEBRE S.A.", "SUPERMERCADO PACIFICO CEBRE S.A."

    if "delimarket" in base:
        return "RETAIL S.A.", "DELIMARKET"
    if has("denis", "roa"):
        return "RETAIL S.A.", "DENIS ROA"
    if "hiperseis" in base or "hiperseis" in base:
        return "RETAIL S.A.", "HIPERSEIS"
    if "japon" in base:
        return "RETAIL S.A.", "JAPON"
    if "laureles" in base:
        return "RETAIL S.A.", "LOS LAURELES"
    if "mburukuya" in base or "mburucuya" in base:
        return "RETAIL S.A.", "MBURUKUYA"
    if "mundimark" in base:
        return "RETAIL S.A.", "MUNDIMARK"
    if "negrita" in base:
        return "RETAIL S.A.", "NEGRITA"
    if "portal" in base:
        return "RETAIL S.A.", "PORTAL"
    if has("san", "bernardino"):
        return "RETAIL S.A.", "SAN BERNARDINO"
    if has("capiata", "ruta", "2"):
        return "RETAIL S.A.", "STOCK CAPIATA RUTA 2"
    if "villeta" in base:
        return "RETAIL S.A.", "VILLETA"
    if has("stock", "mariano"):
        return "RETAIL S.A.", "STOCK MARIANO ROQUE ALONSO 2"
    if has("martin", "ledesma"):
        return "RETAIL S.A.", "STOCK MARTIN LEDESMA"

    if has("acceso", "sur") or base == "acceso":
        return "CADENA REAL S.A.", "ACCESO SUR"
    if "baja ave" in base:
        return "CADENA REAL S.A.", "BAJA AVE"
    if "fernando" in base or has("fdo", "mora"):
        return "CADENA REAL S.A.", "FDO DE LA MORA"
    if has("felix", "bogado"):
        return "CADENA REAL S.A.", "FELIX BOGADO"
    if "nemby2" in base or "nemby 2" in base:
        return "CADENA REAL S.A.", "NEMBY 2"
    if "nemby1" in base or "ñemby1" in base:
        return "CADENA REAL S.A.", "ÑEMBY1"
    if "ruta1" in base or "ruta 1" in base:
        return "CADENA REAL S.A.", "RUTA1"
    if "ruta2" in base or "ruta 2" in base:
        return "CADENA REAL S.A.", "RUTA2"
    if has("san", "vicente"):
        return "CADENA REAL S.A.", "SAN VICENTE"
    if has("villa", "morra"):
        return "CADENA REAL S.A.", "VILLA MORRA"

    return "OTROS", "OTROS"


@st.cache_data(ttl=120)
def load_stock_actual():
    client = get_client()
    try:
        sheet = client.open_by_key(STOCK_SPREADSHEET_ID)
        ws = sheet.get_worksheet_by_id(STOCK_WORKSHEET_GID)
        rows = ws.get_all_values()
    except Exception:
        return {}

    if len(rows) <= 1:
        return {}

    data = []
    for row in rows[1:]:
        padded = row + [""] * max(0, 17 - len(row))
        data.append({
            "timestamp": padded[0].strip(),
            "supermercado": padded[2].strip(),
            "PAQ_30": padded[12].strip() if len(padded) > 12 else "",
            "PAQ_12": padded[13].strip() if len(padded) > 13 else "",
            "PAQ_20": padded[14].strip() if len(padded) > 14 else "",
            "PAQ_6": padded[15].strip() if len(padded) > 15 else "",
            "TIPO_B": padded[16].strip() if len(padded) > 16 else "",
        })

    stock = pd.DataFrame(data)
    if stock.empty:
        return {}

    stock["timestamp_dt"] = pd.to_datetime(stock["timestamp"], dayfirst=True, errors="coerce")
    stock = stock.sort_values("timestamp_dt")
    stock = stock.dropna(subset=["supermercado"])
    stock = stock[stock["supermercado"].astype(str).str.strip() != ""].copy()
    stock = stock.drop_duplicates(subset=["supermercado"], keep="last")

    for col in ["PAQ_30", "PAQ_12", "PAQ_20", "PAQ_6", "TIPO_B"]:
        stock[col] = pd.to_numeric(stock[col], errors="coerce").fillna(0)

    stock_map = {}
    for _, row in stock.iterrows():
        cliente, sucursal = normalizar_supermercado_stock(row["supermercado"])
        for col in ["PAQ_30", "PAQ_12", "PAQ_20", "PAQ_6", "TIPO_B"]:
            stock_map[(cliente, sucursal, col)] = int(round(float(row[col])))

    return stock_map


def deposito_actual_row(cliente: str, sucursal: str, producto: str, stock_map: dict):
    col_stock = mapear_producto_a_columna_stock(producto)
    if not col_stock:
        return None

    key = (str(cliente).strip(), str(sucursal).strip(), col_stock)
    if key not in stock_map:
        return None

    return int(stock_map[key])


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


def fmt_num(x):
    try:
        return f"{int(round(float(x))):,}".replace(",", ".")
    except Exception:
        return "0"


def fmt_money(x):
    return fmt_num(x)


def fmt_deposito(x):
    if x is None or pd.isna(x):
        return "n/a"
    return fmt_num(x)


def label_mes(df: pd.DataFrame, slot: int) -> str:
    col = f"MES_{slot}_LABEL"
    if col in df.columns and not df.empty:
        valor = df[col].iloc[0]
        if valor:
            return valor
    return ""


def semanas_del_mes(label: str) -> float:
    if label.startswith(("S1 ", "S2 ", "S3 ", "S4 ")):
        return 1.0
    if label.startswith(("ENE", "MAR", "MAY", "JUL", "AGO", "OCT", "DIC")):
        return 31 / 7
    if label.startswith(("ABR", "JUN", "SEP", "NOV")):
        return 30 / 7
    if label.startswith("FEB"):
        return 28 / 7
    return 4.33


def mapa_periodos(df: pd.DataFrame):
    mapa = {}
    for slot in range(1, MESES_BASE + 1):
        label = label_mes(df, slot)
        if label:
            mapa[label] = slot
    return mapa


def meses_objetivo(df: pd.DataFrame):
    meses = []
    for slot in range(1, MESES_BASE + 1):
        label = label_mes(df, slot)
        if label:
            meses.append(label)
    return meses


def valor_promedio_semanal(df: pd.DataFrame, label_objetivo: str) -> pd.Series:
    mapa = mapa_periodos(df)
    if label_objetivo not in mapa:
        return pd.Series([0] * len(df), index=df.index)

    slot = mapa[label_objetivo]
    semanas = semanas_del_mes(label_objetivo)
    return (df[f"MES_{slot}_NETO_UND"] / semanas).round(0).astype(int)


def build_producto_resumen(df: pd.DataFrame) -> pd.DataFrame:
    base = df.groupby("Producto", as_index=False).sum(numeric_only=True)
    vista = base[["Producto"]].copy()
    labels = meses_objetivo(df)
    mapa = mapa_periodos(df)

    columnas_prom = []
    for label in labels:
        slot = mapa.get(label)
        if not slot:
            continue
        serie = (base[f"MES_{slot}_NETO_UND"] / semanas_del_mes(label)).round(0).astype(int)
        col = f"Prom. semanal neto {label}"
        vista[col] = serie
        columnas_prom.append(col)

    vista[COL_PROM_UND] = vista[columnas_prom].mean(axis=1).round(0).astype(int) if columnas_prom else 0
    return vista.sort_values([COL_PROM_UND, "Producto"], ascending=[False, True])


def build_tabla_principal(df: pd.DataFrame) -> pd.DataFrame:
    # For the first detail table, show the homologated branch/sucursal as the
    # leading label and hide the old separate "Sucursal" column entirely.
    vista = pd.DataFrame({
        "CLIENTE": df["Sucursal"].fillna("").astype(str),
        "Producto": df["Producto"].fillna("").astype(str),
    })
    labels = meses_objetivo(df)

    columnas_prom = []
    for label in labels:
        col = f"Prom. semanal neto {label}"
        vista[col] = valor_promedio_semanal(df, label)
        columnas_prom.append(col)

    vista[COL_PROM_UND] = vista[columnas_prom].mean(axis=1).round(0).astype(int) if columnas_prom else 0
    return vista


def build_tabla_principal_montos(df: pd.DataFrame) -> pd.DataFrame:
    vista = df[["CLIENTE", "Sucursal", "Producto"]].copy()
    labels = meses_objetivo(df)
    mapa = mapa_periodos(df)

    columnas_monto = []
    for label in labels:
        slot = mapa.get(label)
        if not slot:
            continue
        col_destino = f"Monto neto {label}"
        vista[col_destino] = df[f"MES_{slot}_NETO_MONTO"].round(0).astype(int)
        columnas_monto.append(col_destino)

    vista[COL_PROM_MONTO] = vista[columnas_monto].mean(axis=1).round(0).astype(int) if columnas_monto else 0
    vista["Total meses actuales monto"] = vista[columnas_monto].sum(axis=1).round(0).astype(int) if columnas_monto else 0
    return vista


def build_tabla_supermercado_montos(df: pd.DataFrame) -> pd.DataFrame:
    tabla = build_tabla_principal_montos(df)
    if tabla.empty:
        return pd.DataFrame(columns=["CLIENTE"])

    columnas_monto = [c for c in tabla.columns if c.startswith("Monto neto ")]
    columnas_sumar = columnas_monto + [COL_PROM_MONTO, "Total meses actuales monto"]

    return (
        tabla.groupby("CLIENTE", as_index=False)[columnas_sumar]
        .sum()
        .sort_values("Total meses actuales monto", ascending=False)
    )


def style_detalle(df: pd.DataFrame, referencia_producto_detalle: dict[str, float]):
    cols_meses = [c for c in df.columns if c.startswith("Prom. semanal neto ")]
    cols_objetivo = cols_meses + [COL_PROM_UND]

    def style_row(row):
        producto = str(row.get("Producto", "")).strip()
        umbral = float(referencia_producto_detalle.get(producto, 0))
        styles = [""] * len(row)

        for idx, col in enumerate(df.columns):
            if col not in cols_objetivo:
                continue

            try:
                valor = float(row[col])
            except Exception:
                valor = 0.0

            color = "#e8f5e9" if valor >= umbral else "#fdecea"
            styles[idx] = f"background-color: {color};"

        return styles

    formatters = {}
    for col in df.columns:
        if col in {"CLIENTE", "Producto"}:
            continue
        formatters[col] = fmt_num

    return df.style.apply(style_row, axis=1).format(formatters)


def style_montos_supermercado(df: pd.DataFrame):
    columnas_monto = [c for c in df.columns if c != "CLIENTE"]
    return df.style.format({col: fmt_money for col in columnas_monto})


def construir_tendencia_productos(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label in meses_objetivo(df):
        serie = valor_promedio_semanal(df, label)
        tmp = pd.DataFrame({
            "Producto": df["Producto"].values,
            "Promedio": serie.values,
        })
        tmp = tmp.groupby("Producto", as_index=False)["Promedio"].sum()
        tmp["Mes"] = label
        rows.append(tmp)

    if not rows:
        return pd.DataFrame(columns=["Producto", "Promedio", "Mes"])

    tendencia = pd.concat(rows, ignore_index=True)
    ranking = (
        tendencia.groupby("Producto", as_index=False)["Promedio"]
        .mean()
        .sort_values("Promedio", ascending=False)
    )
    top_productos = ranking.head(7)["Producto"].tolist()
    return tendencia[tendencia["Producto"].isin(top_productos)].copy()


def construir_tendencia_productos_monto(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    mapa = mapa_periodos(df)

    for label in meses_objetivo(df):
        slot = mapa.get(label)
        if not slot:
            continue
        tmp = pd.DataFrame({
            "Producto": df["Producto"].values,
            "Monto": df[f"MES_{slot}_NETO_MONTO"].values,
        })
        tmp = tmp.groupby("Producto", as_index=False)["Monto"].sum()
        tmp["Mes"] = label
        rows.append(tmp)

    if not rows:
        return pd.DataFrame(columns=["Producto", "Monto", "Mes"])

    tendencia = pd.concat(rows, ignore_index=True)
    ranking = (
        tendencia.groupby("Producto", as_index=False)["Monto"]
        .mean()
        .sort_values("Monto", ascending=False)
    )
    top_productos = ranking.head(7)["Producto"].tolist()
    return tendencia[tendencia["Producto"].isin(top_productos)].copy()


def construir_ranking_sucursales(df: pd.DataFrame) -> pd.DataFrame:
    tabla = build_tabla_principal(df)
    if tabla.empty:
        return pd.DataFrame(columns=["Etiqueta", COL_PROM_UND])

    ranking = (
        tabla.groupby(["CLIENTE", "Sucursal"], as_index=False)[COL_PROM_UND]
        .sum()
        .sort_values(COL_PROM_UND, ascending=False)
        .head(15)
    )
    ranking["Etiqueta"] = ranking["CLIENTE"] + " | " + ranking["Sucursal"]
    return ranking


def construir_supermercados_producto(df: pd.DataFrame, producto: str, metrica: str) -> pd.DataFrame:
    tabla = build_tabla_principal(df)
    if tabla.empty:
        return pd.DataFrame(columns=["CLIENTE", metrica])

    base = tabla[tabla["Producto"] == producto].copy()
    if base.empty:
        return pd.DataFrame(columns=["CLIENTE", metrica])

    return (
        base.groupby("CLIENTE", as_index=False)[metrica]
        .sum()
        .sort_values(metrica, ascending=False)
        .head(12)
    )


def construir_supermercados_producto_monto(df: pd.DataFrame, producto: str, metrica: str) -> pd.DataFrame:
    tabla = build_tabla_principal_montos(df)
    if tabla.empty:
        return pd.DataFrame(columns=["CLIENTE", metrica])

    base = tabla[tabla["Producto"] == producto].copy()
    if base.empty:
        return pd.DataFrame(columns=["CLIENTE", metrica])

    return (
        base.groupby("CLIENTE", as_index=False)[metrica]
        .sum()
        .sort_values(metrica, ascending=False)
        .head(12)
    )


def construir_evolucion_supermercados_producto(df: pd.DataFrame, producto: str) -> pd.DataFrame:
    tabla = build_tabla_principal(df)
    if tabla.empty:
        return pd.DataFrame(columns=["CLIENTE", "Mes", "Promedio"])

    base = tabla[tabla["Producto"] == producto].copy()
    if base.empty:
        return pd.DataFrame(columns=["CLIENTE", "Mes", "Promedio"])

    top_clientes = (
        base.groupby("CLIENTE", as_index=False)[COL_PROM_UND]
        .sum()
        .sort_values(COL_PROM_UND, ascending=False)
        .head(8)["CLIENTE"]
        .tolist()
    )

    rows = []
    for label in meses_objetivo(df):
        col = f"Prom. semanal neto {label}"
        tmp = (
            base[base["CLIENTE"].isin(top_clientes)]
            .groupby("CLIENTE", as_index=False)[col]
            .sum()
            .rename(columns={col: "Promedio"})
        )
        tmp["Mes"] = label
        rows.append(tmp)

    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["CLIENTE", "Mes", "Promedio"])


def construir_evolucion_supermercados_producto_monto(df: pd.DataFrame, producto: str) -> pd.DataFrame:
    tabla = build_tabla_principal_montos(df)
    if tabla.empty:
        return pd.DataFrame(columns=["CLIENTE", "Mes", "Monto"])

    base = tabla[tabla["Producto"] == producto].copy()
    if base.empty:
        return pd.DataFrame(columns=["CLIENTE", "Mes", "Monto"])

    top_clientes = (
        base.groupby("CLIENTE", as_index=False)[COL_PROM_MONTO]
        .sum()
        .sort_values(COL_PROM_MONTO, ascending=False)
        .head(8)["CLIENTE"]
        .tolist()
    )

    rows = []
    for label in meses_objetivo(df):
        col = f"Monto neto {label}"
        tmp = (
            base[base["CLIENTE"].isin(top_clientes)]
            .groupby("CLIENTE", as_index=False)[col]
            .sum()
            .rename(columns={col: "Monto"})
        )
        tmp["Mes"] = label
        rows.append(tmp)

    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["CLIENTE", "Mes", "Monto"])


def construir_mix_productos_supermercado(df: pd.DataFrame) -> pd.DataFrame:
    tabla = build_tabla_principal(df)
    if tabla.empty:
        return pd.DataFrame(columns=["CLIENTE", "Producto", COL_PROM_UND])

    top_clientes = (
        tabla.groupby("CLIENTE", as_index=False)[COL_PROM_UND]
        .sum()
        .sort_values(COL_PROM_UND, ascending=False)
        .head(8)["CLIENTE"]
        .tolist()
    )

    top_productos = (
        tabla.groupby("Producto", as_index=False)[COL_PROM_UND]
        .sum()
        .sort_values(COL_PROM_UND, ascending=False)
        .head(6)["Producto"]
        .tolist()
    )

    base = tabla[
        tabla["CLIENTE"].isin(top_clientes) &
        tabla["Producto"].isin(top_productos)
    ].copy()

    return (
        base.groupby(["CLIENTE", "Producto"], as_index=False)[COL_PROM_UND]
        .sum()
        .sort_values(["CLIENTE", COL_PROM_UND], ascending=[True, False])
    )


def construir_mix_productos_supermercado_monto(df: pd.DataFrame) -> pd.DataFrame:
    tabla = build_tabla_principal_montos(df)
    if tabla.empty:
        return pd.DataFrame(columns=["CLIENTE", "Producto", COL_PROM_MONTO])

    top_clientes = (
        tabla.groupby("CLIENTE", as_index=False)[COL_PROM_MONTO]
        .sum()
        .sort_values(COL_PROM_MONTO, ascending=False)
        .head(8)["CLIENTE"]
        .tolist()
    )

    top_productos = (
        tabla.groupby("Producto", as_index=False)[COL_PROM_MONTO]
        .sum()
        .sort_values(COL_PROM_MONTO, ascending=False)
        .head(6)["Producto"]
        .tolist()
    )

    base = tabla[
        tabla["CLIENTE"].isin(top_clientes) &
        tabla["Producto"].isin(top_productos)
    ].copy()

    return (
        base.groupby(["CLIENTE", "Producto"], as_index=False)[COL_PROM_MONTO]
        .sum()
        .sort_values(["CLIENTE", COL_PROM_MONTO], ascending=[True, False])
    )


def construir_sucursales_producto(df: pd.DataFrame, producto: str, metrica: str) -> pd.DataFrame:
    tabla = build_tabla_principal(df)
    if tabla.empty:
        return pd.DataFrame(columns=["Etiqueta", metrica])

    base = tabla[tabla["Producto"] == producto].copy()
    if base.empty:
        return pd.DataFrame(columns=["Etiqueta", metrica])

    ranking = (
        base.groupby(["CLIENTE", "Sucursal"], as_index=False)[metrica]
        .sum()
        .sort_values(metrica, ascending=False)
        .head(15)
    )
    ranking["Etiqueta"] = ranking["CLIENTE"] + " | " + ranking["Sucursal"]
    return ranking


def construir_sucursales_producto_monto(df: pd.DataFrame, producto: str, metrica: str) -> pd.DataFrame:
    tabla = build_tabla_principal_montos(df)
    if tabla.empty:
        return pd.DataFrame(columns=["Etiqueta", metrica])

    base = tabla[tabla["Producto"] == producto].copy()
    if base.empty:
        return pd.DataFrame(columns=["Etiqueta", metrica])

    ranking = (
        base.groupby(["CLIENTE", "Sucursal"], as_index=False)[metrica]
        .sum()
        .sort_values(metrica, ascending=False)
        .head(15)
    )
    ranking["Etiqueta"] = ranking["CLIENTE"] + " | " + ranking["Sucursal"]
    return ranking


def construir_tendencia_supermercados_monto(df: pd.DataFrame) -> pd.DataFrame:
    tabla = build_tabla_principal_montos(df)
    if tabla.empty:
        return pd.DataFrame(columns=["CLIENTE", "Mes", "Monto"])

    top_clientes = (
        tabla.groupby("CLIENTE", as_index=False)["Total meses actuales monto"]
        .sum()
        .sort_values("Total meses actuales monto", ascending=False)
        .head(8)["CLIENTE"]
        .tolist()
    )

    rows = []
    for label in meses_objetivo(df):
        col = f"Monto neto {label}"
        tmp = (
            tabla[tabla["CLIENTE"].isin(top_clientes)]
            .groupby("CLIENTE", as_index=False)[col]
            .sum()
            .rename(columns={col: "Monto"})
        )
        tmp["Mes"] = label
        rows.append(tmp)

    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["CLIENTE", "Mes", "Monto"])


st.set_page_config(
    page_title="Dashboard Reposición",
    page_icon="📦",
    layout="wide",
)

st.title("Dashboard de Reposición")

df = load_data()

if df.empty:
    st.warning("La hoja reposicion_base está vacía.")
    st.stop()

df = df[~df["CLIENTE"].isin(CLIENTES_EXCLUIDOS)].copy()
df = df[~df["Producto"].str.contains("CARBON", case=False, na=False)].copy()
df = df[df["Producto"].apply(producto_relevante)].copy()
df["Sucursal"] = df.apply(lambda row: normalizar_sucursal_dashboard(row["CLIENTE"], row["Sucursal"]), axis=1)

if df.empty:
    st.warning("No hay datos luego de aplicar exclusiones base.")
    st.stop()

st.caption("Todos los valores mostrados son netos: venta menos nota de crédito.")
st.caption("La tabla principal sigue en unidades. Desde Visualizaciones de seguimiento todo pasa a monto neto.")
st.caption(f"Período disponible hoy en la base: {df['PERIODO_BASE'].iloc[0]}")

labels_activos = meses_objetivo(df)
if len(labels_activos) < 3:
    st.warning("Hoy la base no tiene completos enero, febrero y marzo. Las columnas faltantes se muestran en 0 hasta que esos meses existan en el sheet.")

f1, f2, f3, f4, f5 = st.columns([2, 2, 1, 2, 2])

with f1:
    clientes = sorted(df["CLIENTE"].dropna().unique().tolist())
    cliente_sel = st.selectbox("Supermercado", ["Todos"] + clientes)

with f2:
    sucursales = sorted(df["Sucursal"].dropna().unique().tolist())
    sucursal_sel = st.selectbox("Sucursal", ["Todas"] + sucursales)

with f3:
    incluir_otros = st.checkbox("OTROS", value=True)

with f4:
    buscar_cliente = st.text_input("Buscar cliente")

with f5:
    buscar_producto = st.text_input("Buscar producto")

df_filtrado = df.copy()

if cliente_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["CLIENTE"] == cliente_sel].copy()

if sucursal_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Sucursal"] == sucursal_sel].copy()

if not incluir_otros:
    df_filtrado = df_filtrado[df_filtrado["Sucursal"].str.upper() != "OTROS"].copy()

if buscar_cliente.strip():
    patron_cliente = buscar_cliente.strip()
    df_filtrado = df_filtrado[df_filtrado["CLIENTE"].str.contains(patron_cliente, case=False, na=False)].copy()

if buscar_producto.strip():
    patron = buscar_producto.strip()
    df_filtrado = df_filtrado[df_filtrado["Producto"].str.contains(patron, case=False, na=False)].copy()

if df_filtrado.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

tabla_productos = build_producto_resumen(df_filtrado)
promedio_general = float(tabla_productos[COL_PROM_UND].mean()) if not tabla_productos.empty else 0
referencia_producto = (
    tabla_productos.set_index("Producto")[COL_PROM_UND].to_dict()
    if not tabla_productos.empty else {}
)

st.subheader("Detalle por supermercado y producto")

o1, o2 = st.columns([2, 2])

with o1:
    opciones_orden = {
        "Cliente": "CLIENTE",
        "Producto": "Producto",
        "Prom. períodos": COL_PROM_UND,
    }
    for label in labels_activos:
        opciones_orden[f"Prom. semanal neto {label}"] = f"Prom. semanal neto {label}"

    ordenar_por = st.selectbox(
        "Ordenar por",
        list(opciones_orden.keys()),
        index=3,
    )

with o2:
    ver_filas = st.selectbox("Filas visibles", [50, 100, 200, 500], index=1)

tabla_principal = build_tabla_principal(df_filtrado)
referencia_producto_detalle = (
    tabla_principal.groupby("Producto")[COL_PROM_UND].mean().to_dict()
    if not tabla_principal.empty else {}
)
col_orden = opciones_orden[ordenar_por]
ascending = col_orden in {"CLIENTE", "Producto"}
tabla_principal = tabla_principal.sort_values(col_orden, ascending=ascending)

tabla_principal = tabla_principal.head(ver_filas)
st.dataframe(
    style_detalle(tabla_principal, referencia_producto_detalle),
    width="stretch",
    hide_index=True,
)

st.subheader("Promedio semanal neto por producto")
st.dataframe(
    tabla_productos.style.format({
        col: fmt_num for col in tabla_productos.columns if col != "Producto"
    }),
    width="stretch",
    hide_index=True,
)

st.caption(f"Promedio general de la tabla superior: {fmt_num(promedio_general)}")

st.subheader("Visualizaciones de seguimiento")
st.caption("Desde esta sección todo está en monto neto. Las dos tablas de arriba quedan en unidades como referencia operativa.")

tabla_supermercado_montos = build_tabla_supermercado_montos(df_filtrado)
st.markdown("**Monto neto total por supermercado**")
if tabla_supermercado_montos.empty:
    st.info("No hay datos suficientes para construir la tabla de monto neto por supermercado.")
else:
    st.dataframe(
        style_montos_supermercado(tabla_supermercado_montos),
        width="stretch",
        hide_index=True,
    )

tendencia_productos = construir_tendencia_productos_monto(df_filtrado)
tendencia_supermercados = construir_tendencia_supermercados_monto(df_filtrado)
mix_productos_supermercado = construir_mix_productos_supermercado_monto(df_filtrado)

st.markdown("**Tendencia mensual por supermercado**")
if tendencia_supermercados.empty:
    st.info("No hay datos suficientes para la tendencia mensual por supermercado.")
else:
    fig_tendencia_super = px.line(
        tendencia_supermercados,
        x="Mes",
        y="Monto",
        color="CLIENTE",
        markers=True,
        line_shape="linear",
    )
    fig_tendencia_super.update_layout(
        height=460,
        margin=dict(l=20, r=20, t=20, b=20),
        yaxis_title="Monto neto",
        xaxis_title="Mes",
        legend_title="Supermercado",
    )
    fig_tendencia_super.update_yaxes(tickformat=",.0f")
    st.plotly_chart(fig_tendencia_super, use_container_width=True)

v1, v2 = st.columns([2, 2])
with v1:
    productos_vis = tabla_productos["Producto"].tolist()
    producto_vis_sel = st.selectbox(
        "Producto para análisis visual",
        productos_vis,
        index=0 if productos_vis else None,
    )
with v2:
    metrica_vis_labels = {"Prom. períodos (monto)": COL_PROM_MONTO}
    for label in labels_activos:
        metrica_vis_labels[f"Monto neto {label}"] = f"Monto neto {label}"

    metrica_vis_sel_label = st.selectbox(
        "Métrica del análisis",
        list(metrica_vis_labels.keys()),
        index=0,
    )
    metrica_vis_sel = metrica_vis_labels[metrica_vis_sel_label]

ranking_clientes_producto = construir_supermercados_producto_monto(df_filtrado, producto_vis_sel, metrica_vis_sel)
evolucion_supermercados_producto = construir_evolucion_supermercados_producto_monto(df_filtrado, producto_vis_sel)
ranking_sucursales_producto = construir_sucursales_producto_monto(df_filtrado, producto_vis_sel, metrica_vis_sel)

g1, g2 = st.columns(2)

with g1:
    st.markdown("**Tendencia mensual por producto**")
    if tendencia_productos.empty:
        st.info("No hay datos suficientes para graficar la tendencia por producto.")
    else:
        fig_tendencia = px.line(
            tendencia_productos,
            x="Mes",
            y="Monto",
            color="Producto",
            markers=True,
            line_shape="linear",
        )
        fig_tendencia.update_layout(
            height=420,
            margin=dict(l=20, r=20, t=20, b=20),
            yaxis_title="Monto neto",
            xaxis_title="Mes",
            legend_title="Producto",
        )
        fig_tendencia.update_yaxes(tickformat=",.0f")
        st.plotly_chart(fig_tendencia, use_container_width=True)

with g2:
    st.markdown(f"**Supermercados para {producto_vis_sel}**")
    if ranking_clientes_producto.empty:
        st.info("No hay datos suficientes para graficar supermercados.")
    else:
        fig_clientes = px.bar(
            ranking_clientes_producto.sort_values(metrica_vis_sel, ascending=True),
            x=metrica_vis_sel,
            y="CLIENTE",
            orientation="h",
            text=metrica_vis_sel,
        )
        fig_clientes.update_traces(texttemplate="%{text:.0f}", textposition="outside")
        fig_clientes.update_layout(
            height=420,
            margin=dict(l=20, r=20, t=20, b=20),
            yaxis_title="Supermercado",
            xaxis_title="Monto neto",
            showlegend=False,
        )
        fig_clientes.update_xaxes(tickformat=",.0f")
        st.plotly_chart(fig_clientes, use_container_width=True)

g3 = st.columns(1)[0]
g4 = st.columns(1)[0]

with g3:
    st.markdown(f"**Evolución por supermercado de {producto_vis_sel}**")
    if evolucion_supermercados_producto.empty:
        st.info("No hay datos suficientes para la evolución por supermercado.")
    else:
        fig_evolucion = px.line(
            evolucion_supermercados_producto,
            x="Mes",
            y="Monto",
            color="CLIENTE",
            markers=True,
        )
        fig_evolucion.update_layout(
            height=460,
            margin=dict(l=20, r=20, t=20, b=20),
            yaxis_title="Monto neto",
            xaxis_title="Mes",
            legend_title="Supermercado",
        )
        fig_evolucion.update_yaxes(tickformat=",.0f")
        st.plotly_chart(fig_evolucion, use_container_width=True)

g5, g6 = st.columns(2)

with g5:
    st.markdown(f"**Sucursales líderes de {producto_vis_sel}**")
    if ranking_sucursales_producto.empty:
        st.info("No hay datos suficientes para graficar sucursales.")
    else:
        fig_sucursales = px.bar(
            ranking_sucursales_producto.sort_values(metrica_vis_sel, ascending=True),
            x=metrica_vis_sel,
            y="Etiqueta",
            orientation="h",
            text=metrica_vis_sel,
        )
        fig_sucursales.update_traces(texttemplate="%{text:.0f}", textposition="outside")
        fig_sucursales.update_layout(
            height=460,
            margin=dict(l=20, r=20, t=20, b=20),
            yaxis_title="Sucursal",
            xaxis_title="Monto neto",
            showlegend=False,
        )
        fig_sucursales.update_xaxes(tickformat=",.0f")
        st.plotly_chart(fig_sucursales, use_container_width=True)

with g6:
    st.markdown("**Mix de productos por supermercado**")
    if mix_productos_supermercado.empty:
        st.info("No hay datos suficientes para el mix de productos.")
    else:
        fig_mix = px.bar(
            mix_productos_supermercado,
            x="CLIENTE",
            y=COL_PROM_MONTO,
            color="Producto",
            barmode="stack",
        )
        fig_mix.update_layout(
            height=440,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="Supermercado",
            yaxis_title="Monto neto promedio de períodos",
            legend_title="Producto",
        )
        fig_mix.update_yaxes(tickformat=",.0f")
        st.plotly_chart(fig_mix, use_container_width=True)
