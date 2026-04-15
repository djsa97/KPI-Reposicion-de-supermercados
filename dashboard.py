import streamlit as st
import pandas as pd
import gspread
import os
from google.oauth2.service_account import Credentials


# =========================
# CONFIG
# =========================
JSON_PATH = os.getenv("GOOGLE_CREDS_FILE", "automatizacion-sol-huevos-2-f02d718cb7d4.json")
SHEET_ID = "1B21HlZ5MBVj6Orc1rkLM1_mZycXLDEJDIT9OF9Gw9Kw"
SHEET_DASHBOARD_BASE = "dashboard_base"


# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Dashboard Sol Huevos",
    page_icon="🥚",
    layout="wide",
)


# =========================
# HELPERS
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


@st.cache_data(ttl=120)
def cargar_dashboard_base():
    spreadsheet = conectar_google_sheet()
    ws = spreadsheet.worksheet(SHEET_DASHBOARD_BASE)
    records = ws.get_all_records()
    df = pd.DataFrame(records)

    if df.empty:
        return df

    # columnas numéricas
    for col in ["ORDEN_CLIENTE", "VENTA", "NC", "ACUERDOS", "NETO"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # columnas texto
    for col in ["NIVEL", "CLIENTE", "Sucursal", "Producto"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    return df


def formato_monto(valor):
    try:
        return f"{int(round(valor)):,}".replace(",", ".")
    except Exception:
        return "0"


def init_state():
    if "expand_all" not in st.session_state:
        st.session_state.expand_all = False


def obtener_columna_orden(label_orden):
    mapping = {
        "Cliente": "CLIENTE",
        "Venta": "VENTA",
        "NC": "NC",
        "Acuerdos": "ACUERDOS",
        "Neto": "NETO",
    }
    return mapping[label_orden]


def ordenar_df(df, label_orden, descendente=True):
    col = obtener_columna_orden(label_orden)

    if col == "CLIENTE":
        return df.sort_values(by=col, ascending=not descendente)

    # para números
    return df.sort_values(by=col, ascending=not descendente)


# =========================
# APP
# =========================
init_state()

st.title("🥚 Dashboard Sol Huevos")
st.caption("Vista jerárquica por supermercado → sucursal → producto")

df = cargar_dashboard_base()

if df.empty:
    st.warning("La hoja dashboard_base está vacía.")
    st.stop()

# =========================
# FILTROS SIDEBAR
# =========================
clientes_disponibles = sorted(df["CLIENTE"].dropna().unique().tolist())

with st.sidebar:
    st.header("Filtros")

    cliente_sel = st.selectbox(
        "Supermercado",
        options=["Todos"] + clientes_disponibles,
        index=0,
    )

    mostrar_solo_clientes = st.checkbox("Mostrar solo fila cliente", value=False)
    incluir_otros = st.checkbox("Incluir sucursal OTROS", value=True)

    st.markdown("---")

    c1, c2 = st.columns(2)
    if c1.button("Expandir todo", use_container_width=True):
        st.session_state.expand_all = True

    if c2.button("Ocultar todo", use_container_width=True):
        st.session_state.expand_all = False


# =========================
# FILTROS PRINCIPALES
# =========================
df_filtrado = df.copy()

if cliente_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["CLIENTE"] == cliente_sel]

if not incluir_otros:
    mask_otros = (df_filtrado["NIVEL"] == "SUCURSAL") & (df_filtrado["Sucursal"].str.upper() == "OTROS")
    mask_otros_prod = (df_filtrado["NIVEL"] == "PRODUCTO") & (df_filtrado["Sucursal"].str.upper() == "OTROS")
    df_filtrado = df_filtrado[~(mask_otros | mask_otros_prod)]


# =========================
# KPIs
# =========================
df_clientes = df_filtrado[df_filtrado["NIVEL"] == "CLIENTE"].copy()

venta_total = df_clientes["VENTA"].sum()
nc_total = abs(df_clientes["NC"].sum())
acuerdos_total = df_clientes["ACUERDOS"].sum()
neto_total = df_clientes["NETO"].sum()
cant_super = df_clientes["CLIENTE"].nunique()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Supermercados", cant_super)
k2.metric("Venta total", formato_monto(venta_total))
k3.metric("NC total", formato_monto(nc_total))
k4.metric("Acuerdos", formato_monto(acuerdos_total))
k5.metric("Neto", formato_monto(neto_total))

st.markdown("---")

# =========================
# CONTROLES DE ORDEN
# =========================
o1, o2, o3 = st.columns([1.4, 1.4, 4])

with o1:
    orden_label = st.selectbox(
        "Ordenar por",
        ["Neto", "Venta", "NC", "Acuerdos", "Cliente"],
        index=0,
    )

with o2:
    sentido = st.selectbox(
        "Sentido",
        ["Mayor a menor", "Menor a mayor"],
        index=0,
    )

descendente = sentido == "Mayor a menor"

# ordenar clientes
df_clientes_ordenado = ordenar_df(df_clientes.copy(), orden_label, descendente)

# =========================
# HEADER TABLA
# =========================
if mostrar_solo_clientes:
    h1, h2, h3, h4, h5 = st.columns([3.2, 1.2, 1.2, 1.2, 1.2])
    h1.markdown("**CLIENTE**")
    h2.markdown("**VENTA**")
    h3.markdown("**NC**")
    h4.markdown("**ACUERDOS**")
    h5.markdown("**NETO**")
else:
    h1, h2, h3, h4, h5 = st.columns([4, 1.2, 1.2, 1.2, 1.2])
    h1.markdown("**CLIENTE / SUCURSAL / PRODUCTO**")
    h2.markdown("**VENTA**")
    h3.markdown("**NC**")
    h4.markdown("**ACUERDOS**")
    h5.markdown("**NETO**")

st.markdown("---")

# =========================
# TABLA SOLO CLIENTES
# =========================
if mostrar_solo_clientes:
    view = df_clientes_ordenado[["CLIENTE", "VENTA", "NC", "ACUERDOS", "NETO"]].copy()
    view["NC"] = view["NC"].abs()

    view["VENTA"] = view["VENTA"].apply(formato_monto)
    view["NC"] = view["NC"].apply(formato_monto)
    view["ACUERDOS"] = view["ACUERDOS"].apply(formato_monto)
    view["NETO"] = view["NETO"].apply(formato_monto)

    st.dataframe(view, use_container_width=True, hide_index=True)
    st.stop()

# =========================
# TABLA JERÁRQUICA
# =========================
for _, fila_cliente in df_clientes_ordenado.iterrows():
    cliente = fila_cliente["CLIENTE"]
    orden_cliente = fila_cliente["ORDEN_CLIENTE"]

    df_cliente_full = df_filtrado[df_filtrado["ORDEN_CLIENTE"] == orden_cliente].copy()
    if df_cliente_full.empty:
        continue

    label_cliente = (
        f"{cliente} | "
        f"Venta: {formato_monto(fila_cliente['VENTA'])} | "
        f"NC: {formato_monto(abs(fila_cliente['NC']))} | "
        f"Acuerdos: {formato_monto(fila_cliente['ACUERDOS'])} | "
        f"Neto: {formato_monto(fila_cliente['NETO'])}"
    )

    with st.expander(label_cliente, expanded=st.session_state.expand_all):
        sucursales_df = df_cliente_full[df_cliente_full["NIVEL"] == "SUCURSAL"].copy()

        # ordenar sucursales
        if orden_label == "Cliente":
            sucursales_df = sucursales_df.sort_values(by="Sucursal", ascending=not descendente)
        else:
            col_sort = obtener_columna_orden(orden_label)
            if col_sort in sucursales_df.columns:
                sucursales_df = sucursales_df.sort_values(by=col_sort, ascending=not descendente)

        for _, suc_row in sucursales_df.iterrows():
            sucursal = suc_row["Sucursal"]

            label_sucursal = (
                f"{sucursal} | "
                f"Venta: {formato_monto(suc_row['VENTA'])} | "
                f"NC: {formato_monto(abs(suc_row['NC']))} | "
                f"Neto: {formato_monto(suc_row['NETO'])}"
            )

            with st.expander(label_sucursal, expanded=st.session_state.expand_all):
                productos_df = df_cliente_full[
                    (df_cliente_full["NIVEL"] == "PRODUCTO") &
                    (df_cliente_full["Sucursal"] == sucursal)
                ].copy()

                if productos_df.empty:
                    st.caption("Sin productos.")
                else:
                    if orden_label == "Cliente":
                        productos_df = productos_df.sort_values(by="Producto", ascending=not descendente)
                    else:
                        col_sort = obtener_columna_orden(orden_label)
                        if col_sort in productos_df.columns:
                            productos_df = productos_df.sort_values(by=col_sort, ascending=not descendente)

                    prod_view = productos_df[["Producto", "VENTA", "NC", "NETO"]].copy()
                    prod_view["NC"] = prod_view["NC"].abs()

                    prod_view = prod_view.rename(columns={
                        "Producto": "Producto",
                        "VENTA": "Venta",
                        "NC": "NC",
                        "NETO": "Neto",
                    })

                    # formateo
                    for col in ["Venta", "NC", "Neto"]:
                        prod_view[col] = prod_view[col].apply(formato_monto)

                    st.dataframe(
                        prod_view,
                        use_container_width=True,
                        hide_index=True,
                    )

st.markdown("---")
st.caption("Siguiente paso: gráfico de tendencia de ventas por supermercado de las últimas 4 semanas.")
