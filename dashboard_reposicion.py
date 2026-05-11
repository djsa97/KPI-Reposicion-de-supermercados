import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import calendar
from google.oauth2.service_account import Credentials
from gspread.utils import ValueRenderOption
import os
import re
import unicodedata


SPREADSHEET_ID = "1B21HlZ5MBVj6Orc1rkLM1_mZycXLDEJDIT9OF9Gw9Kw"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_FILE = os.getenv(
    "GOOGLE_CREDS_FILE",
    os.path.join(BASE_DIR, "automatizacion-sol-huevos-2-f02d718cb7d4.json"),
)
WORKSHEET_NAME = "reposicion_base"
CLIENTES_EXCLUIDOS = set()
COL_PROM_UND = "Prom. períodos"
COL_PROM_MONTO = "Prom. períodos monto"
MESES_ES_REV = {
    "ENE": 1,
    "FEB": 2,
    "MAR": 3,
    "ABR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AGO": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DIC": 12,
}

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
    ws = sheet.worksheet(WORKSHEET_NAME)
    values = ws.get(
        value_render_option=ValueRenderOption.unformatted,
    )
    if not values:
        return pd.DataFrame()

    header = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=header)

    if df.empty:
        return df

    numeric_cols = [
        "PROMEDIO_MENSUAL_UND",
        "PROMEDIO_SEMANAL_UND",
        "VENTA_UND_PERIODO",
        "NC_UND_PERIODO",
        "NETO_UND_PERIODO",
        "MESES_CON_DATOS",
        "VENTA_MONTO_PERIODO",
        "NC_MONTO_PERIODO",
        "NETO_MONTO_PERIODO",
        "PROMEDIO_MENSUAL_MONTO",
    ]
    for col in df.columns:
        if re.fullmatch(r"MES_\d+_(VENTA|NC|NETO)_(UND|MONTO)", col):
            numeric_cols.append(col)
        if re.fullmatch(r"MES_\d+_SEMANAS", col):
            numeric_cols.append(col)

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    for col in ["PERIODO_BASE", "CLIENTE", "Sucursal", "Producto"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    if "CLIENTE" in df.columns:
        df["CLIENTE"] = df["CLIENTE"].map(normalizar_cliente_dashboard)

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


def producto_relevante(producto: str) -> bool:
    texto = str(producto).upper()
    return ("HUEVO" in texto) or ("PLANCHA" in texto)


def normalizar_texto_base(texto: str) -> str:
    texto = str(texto or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = " ".join(texto.replace("_", " ").split())
    return texto


def normalizar_cliente_dashboard(cliente: str) -> str:
    cliente_limpio = str(cliente or "").strip()
    texto_base = normalizar_texto_base(cliente_limpio)

    if not texto_base:
        return ""

    if texto_base == "super seis":
        return "Super Seis"

    if texto_base.startswith("s6 "):
        return "Super Seis"

    return cliente_limpio


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
    if label.startswith("S"):
        return 1.0
    if label.startswith(("ENE", "MAR", "MAY", "JUL", "AGO", "OCT", "DIC")):
        return 31 / 7
    if label.startswith(("ABR", "JUN", "SEP", "NOV")):
        return 30 / 7
    if label.startswith("FEB"):
        return 28 / 7
    return 4.33


def semanas_slot(df: pd.DataFrame, slot: int, label: str) -> float:
    col = f"MES_{slot}_SEMANAS"
    if col in df.columns and not df.empty:
        semanas = pd.to_numeric(df[col], errors="coerce").fillna(0)
        valor = float(semanas.iloc[0]) if not semanas.empty else 0
        if valor > 0:
            return valor
    return semanas_del_mes(label)


def mapa_periodos(df: pd.DataFrame):
    mapa = {}
    for slot in slots_disponibles(df):
        label = label_mes(df, slot)
        if label:
            mapa[label] = slot
    return mapa


def meses_objetivo(df: pd.DataFrame):
    meses = []
    for slot in slots_disponibles(df):
        label = label_mes(df, slot)
        if label:
            meses.append(label)
    return meses


def valor_promedio_semanal(df: pd.DataFrame, label_objetivo: str) -> pd.Series:
    mapa = mapa_periodos(df)
    if label_objetivo not in mapa:
        return pd.Series([0] * len(df), index=df.index)

    slot = mapa[label_objetivo]
    semanas = semanas_slot(df, slot, label_objetivo)
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
        serie = (base[f"MES_{slot}_NETO_UND"] / semanas_slot(df, slot, label)).round(0).astype(int)
        col = f"Prom. semanal neto {label}"
        vista[col] = serie
        columnas_prom.append(col)

    vista[COL_PROM_UND] = vista[columnas_prom].mean(axis=1).round(0).astype(int) if columnas_prom else 0
    return vista.sort_values([COL_PROM_UND, "Producto"], ascending=[False, True])


def build_tabla_principal(df: pd.DataFrame) -> pd.DataFrame:
    base = df.groupby(["CLIENTE", "Producto"], as_index=False).sum(numeric_only=True)
    vista = pd.DataFrame({
        "Cliente": base["CLIENTE"].fillna("").astype(str),
        "Producto": base["Producto"].fillna("").astype(str),
    })
    labels = meses_objetivo(df)

    columnas_prom = []
    for label in labels:
        col = f"Prom. semanal neto {label}"
        slot = mapa_periodos(df).get(label)
        if not slot:
            continue
        serie = (base[f"MES_{slot}_NETO_UND"] / semanas_slot(df, slot, label)).round(0).astype(int)
        vista[col] = serie
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


def build_tabla_venta_periodos_monto(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Producto"])

    base = df.groupby("Producto", as_index=False).sum(numeric_only=True)
    vista = base[["Producto"]].copy()
    labels = meses_objetivo(df)
    mapa = mapa_periodos(df)

    columnas_meses_cerrados = []
    columnas_semanas_actuales = []

    for label in labels:
        slot = mapa.get(label)
        if not slot:
            continue

        if label.startswith("S"):
            col = f"Venta semanal {label}"
            columnas_semanas_actuales.append(col)
        else:
            col = f"Venta total {label}"
            columnas_meses_cerrados.append(col)

        vista[col] = base[f"MES_{slot}_VENTA_MONTO"].round(0).astype(int)

    if columnas_meses_cerrados:
        vista["Prom. meses cerrados"] = (
            vista[columnas_meses_cerrados].mean(axis=1).round(0).astype(int)
        )
    else:
        vista["Prom. meses cerrados"] = 0

    columnas_orden = (
        ["Producto", "Prom. meses cerrados"]
        + columnas_meses_cerrados
        + columnas_semanas_actuales
    )
    vista = vista[columnas_orden]
    return vista.sort_values("Prom. meses cerrados", ascending=False)


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
        if col in {"Cliente", "Producto"}:
            continue
        formatters[col] = fmt_num

    return df.style.apply(style_row, axis=1).format(formatters)


def style_montos_supermercado(df: pd.DataFrame):
    columnas_monto = [c for c in df.columns if c != "CLIENTE"]
    return df.style.format({col: fmt_money for col in columnas_monto})


def construir_tendencia_venta_periodos_monto(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    mapa = mapa_periodos(df)
    labels = meses_objetivo(df)

    for label in labels:
        slot = mapa.get(label)
        if not slot:
            continue
        tmp = pd.DataFrame({
            "Producto": df["Producto"].values,
            "Monto": df[f"MES_{slot}_VENTA_MONTO"].values,
        })
        tmp = tmp.groupby("Producto", as_index=False)["Monto"].sum()
        tmp["Período"] = label
        tmp["Serie"] = "Real"
        rows.append(tmp)

    if not rows:
        return pd.DataFrame(columns=["Producto", "Monto", "Período", "Serie"])

    tendencia = pd.concat(rows, ignore_index=True)
    ranking = (
        tendencia[tendencia["Serie"] == "Real"]
        .groupby("Producto", as_index=False)["Monto"]
        .mean()
        .sort_values("Monto", ascending=False)
    )
    top_productos = ranking.head(7)["Producto"].tolist()
    tendencia = tendencia[tendencia["Producto"].isin(top_productos)].copy()

    return agregar_proyeccion_mes_actual(
        tendencia,
        entidad_col="Producto",
        periodo_col="Período",
        labels=labels,
    )


def agregar_proyeccion_mes_actual(
    tendencia: pd.DataFrame,
    entidad_col: str,
    periodo_col: str,
    labels: list[str],
) -> pd.DataFrame:
    if tendencia.empty:
        return tendencia

    base = tendencia.copy()
    if "Serie" not in base.columns:
        base["Serie"] = "Real"

    labels_semanales = [label for label in labels if label.startswith("S")]
    if not labels_semanales:
        return base

    semanas_por_mes = {}
    patron = re.compile(r"^S(\d+)\s+([A-Z]{3})-(\d{4})$")
    for label in labels_semanales:
        match = patron.match(label)
        if not match:
            continue
        semana_idx = int(match.group(1))
        mes_txt = match.group(2)
        anio = int(match.group(3))
        mes_num = MESES_ES_REV.get(mes_txt)
        if not mes_num:
            continue
        semanas_por_mes.setdefault((anio, mes_num, mes_txt), []).append((semana_idx, label))

    proyecciones = []
    for (anio, mes_num, _mes_txt), semanas in semanas_por_mes.items():
        semanas_ordenadas = sorted(semanas, key=lambda x: x[0])
        semanas_mes = calendar.monthrange(anio, mes_num)[1] / 7
        entidades = (
            base[base["Serie"] == "Real"][entidad_col]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
        for entidad in entidades:
            acumulado = 0.0
            for posicion, (_semana_idx, label) in enumerate(semanas_ordenadas, start=1):
                actual = base[
                    (base[entidad_col] == entidad)
                    & (base[periodo_col] == label)
                    & (base["Serie"] == "Real")
                ]["Monto"].sum()
                acumulado += float(actual)
                proyectado = acumulado / posicion * semanas_mes if posicion else 0.0
                proyecciones.append({
                    entidad_col: entidad,
                    "Monto": proyectado,
                    periodo_col: label,
                    "Serie": "Proyección mes actual",
                })

    if proyecciones:
        base = pd.concat([base, pd.DataFrame(proyecciones)], ignore_index=True)

    return base


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
        return pd.DataFrame(columns=["CLIENTE", "Mes", "Monto", "Serie"])

    base = tabla[tabla["Producto"] == producto].copy()
    if base.empty:
        return pd.DataFrame(columns=["CLIENTE", "Mes", "Monto", "Serie"])

    top_clientes = (
        base.groupby("CLIENTE", as_index=False)[COL_PROM_MONTO]
        .sum()
        .sort_values(COL_PROM_MONTO, ascending=False)
        .head(8)["CLIENTE"]
        .tolist()
    )

    rows = []
    labels = meses_objetivo(df)
    for label in labels:
        col = f"Monto neto {label}"
        tmp = (
            base[base["CLIENTE"].isin(top_clientes)]
            .groupby("CLIENTE", as_index=False)[col]
            .sum()
            .rename(columns={col: "Monto"})
        )
        tmp["Mes"] = label
        tmp["Serie"] = "Real"
        rows.append(tmp)

    if not rows:
        return pd.DataFrame(columns=["CLIENTE", "Mes", "Monto", "Serie"])

    return agregar_proyeccion_mes_actual(
        pd.concat(rows, ignore_index=True),
        entidad_col="CLIENTE",
        periodo_col="Mes",
        labels=labels,
    )


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
        return pd.DataFrame(columns=["CLIENTE", "Mes", "Monto", "Serie"])

    top_clientes = (
        tabla.groupby("CLIENTE", as_index=False)["Total meses actuales monto"]
        .sum()
        .sort_values("Total meses actuales monto", ascending=False)
        .head(8)["CLIENTE"]
        .tolist()
    )

    rows = []
    labels = meses_objetivo(df)
    for label in labels:
        col = f"Monto neto {label}"
        tmp = (
            tabla[tabla["CLIENTE"].isin(top_clientes)]
            .groupby("CLIENTE", as_index=False)[col]
            .sum()
            .rename(columns={col: "Monto"})
        )
        tmp["Mes"] = label
        tmp["Serie"] = "Real"
        rows.append(tmp)

    if not rows:
        return pd.DataFrame(columns=["CLIENTE", "Mes", "Monto", "Serie"])

    return agregar_proyeccion_mes_actual(
        pd.concat(rows, ignore_index=True),
        entidad_col="CLIENTE",
        periodo_col="Mes",
        labels=labels,
    )


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
df["Sucursal"] = df["Sucursal"].fillna("").astype(str).str.strip()

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

st.subheader("Detalle por cliente y producto")

o1, o2 = st.columns([2, 2])

with o1:
    opciones_orden = {
        "Cliente": "Cliente",
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
ascending = col_orden in {"Cliente", "Producto"}
tabla_principal = tabla_principal.sort_values(col_orden, ascending=ascending)

tabla_principal = tabla_principal.head(ver_filas)
st.dataframe(
    style_detalle(tabla_principal, referencia_producto_detalle),
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

tendencia_productos = construir_tendencia_venta_periodos_monto(df_filtrado)
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
        line_dash="Serie",
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

tabla_venta_periodos_monto = build_tabla_venta_periodos_monto(df_filtrado)
st.markdown("**Venta por períodos en monto**")
if tabla_venta_periodos_monto.empty:
    st.info("No hay datos suficientes para construir la tabla de venta por períodos.")
else:
    st.dataframe(
        tabla_venta_periodos_monto.style.format({
            col: fmt_money for col in tabla_venta_periodos_monto.columns if col != "Producto"
        }),
        width="stretch",
        hide_index=True,
    )

tendencia_venta_monto = construir_tendencia_venta_periodos_monto(df_filtrado)
if tendencia_venta_monto.empty:
    st.info("No hay datos suficientes para construir la tendencia de venta por producto.")
else:
    fig_tendencia_venta_monto = px.line(
        tendencia_venta_monto,
        x="Período",
        y="Monto",
        color="Producto",
        line_dash="Serie",
        markers=True,
        line_shape="linear",
    )
    fig_tendencia_venta_monto.update_layout(
        height=420,
        margin=dict(l=20, r=20, t=20, b=20),
        yaxis_title="Monto vendido",
        xaxis_title="Período",
        legend_title="Producto",
    )
    fig_tendencia_venta_monto.update_yaxes(tickformat=",.0f")
    st.plotly_chart(fig_tendencia_venta_monto, use_container_width=True)
    st.caption("Línea continua: venta real del período. Línea punteada: proyección mensual del mes actual.")

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
    st.markdown("**Tendencia de venta por producto**")
    if tendencia_productos.empty:
        st.info("No hay datos suficientes para graficar la tendencia por producto.")
    else:
        fig_tendencia = px.line(
            tendencia_productos,
            x="Período",
            y="Monto",
            color="Producto",
            line_dash="Serie",
            markers=True,
            line_shape="linear",
        )
        fig_tendencia.update_layout(
            height=420,
            margin=dict(l=20, r=20, t=20, b=20),
            yaxis_title="Monto vendido",
            xaxis_title="Período",
            legend_title="Producto",
        )
        fig_tendencia.update_yaxes(tickformat=",.0f")
        st.plotly_chart(fig_tendencia, use_container_width=True, key="tendencia_venta_producto_monto")

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
            line_dash="Serie",
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
