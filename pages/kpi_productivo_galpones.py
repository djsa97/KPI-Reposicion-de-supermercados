from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "data" / "galpones" / "informe_galpones.xlsx"
CLASSIFICATION_PATH = BASE_DIR / "data" / "galpones" / "produccion_respuestas.xlsx"

DATE_COL = "Fecha"
HOUSE_COL = "Galpon"
NUMERIC_COLS = [
    "Gallinas",
    "Cons. Balanceado",
    "Huevos",
    "Mortandad",
    "Produccion",
    "Calc. Balanceado",
    "Temperatura",
    "consumo_agua",
]

PALETTE = {
    "bg": "#0d1117",
    "panel": "#151b23",
    "panel_2": "#1b2330",
    "border": "#2a3545",
    "text": "#f4f7fb",
    "muted": "#98a6ba",
    "blue": "#4f8cff",
    "green": "#35c88a",
    "amber": "#f2b84b",
    "red": "#e45d5d",
    "teal": "#55d6c2",
}

AGE_ANCHORS = {
    "GALPON 1": {"date": "2026-05-08", "week": 80},
    "GALPON 2": {"date": "2026-05-08", "week": 15},
    "GALPON 3": {"date": "2026-05-08", "week": 80},
    "GALPON 6": {"date": "2026-05-08", "week": 57},
    "GALPON 7": {"date": "2026-05-08", "week": 36},
}

TARGET_ROWS = [
    (18, 1.1, 7.7, 0.05, 73, 88),
    (19, 8.2, 27.1, 0.08, 85, 94),
    (20, 30.8, 57.3, 0.13, 90, 99),
    (21, 61.4, 80.5, 0.20, 95, 103),
    (22, 82.4, 90.6, 0.27, 99, 107),
    (23, 90.6, 94.1, 0.34, 102, 111),
    (24, 93.2, 95.5, 0.40, 106, 114),
    (25, 94.2, 96.2, 0.46, 108, 115),
    (26, 94.6, 96.4, 0.50, 109, 116),
    (27, 94.8, 96.6, 0.55, 109, 116),
    (28, 94.8, 96.6, 0.61, 109, 116),
    (29, 94.8, 96.6, 0.66, 109, 117),
    (30, 94.8, 96.5, 0.71, 109, 117),
    (31, 94.7, 96.5, 0.76, 109, 117),
    (32, 94.7, 96.5, 0.80, 109, 117),
    (33, 94.6, 96.3, 0.86, 109, 117),
    (34, 94.4, 96.1, 0.92, 109, 117),
    (35, 94.2, 96.0, 0.97, 109, 117),
    (36, 94.0, 95.8, 1.02, 109, 116),
    (37, 93.7, 95.7, 1.08, 109, 116),
    (38, 93.5, 95.5, 1.12, 109, 116),
    (39, 93.3, 95.3, 1.18, 109, 116),
    (40, 93.1, 95.0, 1.24, 108, 116),
    (41, 92.8, 94.9, 1.30, 108, 116),
    (42, 92.5, 94.6, 1.35, 108, 116),
    (43, 92.1, 94.4, 1.41, 108, 116),
    (44, 91.8, 94.1, 1.47, 108, 116),
    (45, 91.5, 93.8, 1.52, 108, 116),
    (46, 91.2, 93.5, 1.59, 108, 116),
    (47, 90.9, 93.3, 1.64, 108, 116),
    (48, 90.7, 93.1, 1.70, 108, 116),
    (49, 90.4, 92.8, 1.76, 108, 116),
    (50, 90.0, 92.7, 1.83, 108, 116),
    (51, 89.8, 92.4, 1.89, 108, 116),
    (52, 89.6, 92.2, 1.95, 108, 116),
    (53, 89.4, 91.9, 2.01, 108, 116),
    (54, 89.3, 91.7, 2.09, 108, 116),
    (55, 88.9, 91.5, 2.16, 108, 116),
    (56, 88.7, 91.4, 2.24, 108, 116),
    (57, 88.4, 91.2, 2.33, 108, 116),
    (58, 88.2, 91.0, 2.40, 108, 116),
]

TARGETS = pd.DataFrame(
    TARGET_ROWS,
    columns=[
        "Edad semana",
        "Meta prod min",
        "Meta prod max",
        "Mortandad acum ref %",
        "Balanceado min g",
        "Balanceado max g",
    ],
)


st.set_page_config(
    page_title="KPI Productivo Galpones",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    f"""
    <style>
        .stApp {{
            background: {PALETTE["bg"]};
            color: {PALETTE["text"]};
        }}
        [data-testid="stSidebar"] {{
            background: #101620;
            border-right: 1px solid {PALETTE["border"]};
        }}
        [data-testid="stSidebar"] * {{
            color: {PALETTE["text"]} !important;
        }}
        .block-container {{
            max-width: 1480px;
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: {PALETTE["text"]};
            letter-spacing: 0;
        }}
        p, label, span, div {{
            color: {PALETTE["muted"]};
        }}
        .hero-band {{
            border-bottom: 1px solid {PALETTE["border"]};
            margin-bottom: 18px;
            padding-bottom: 10px;
        }}
        .hero-title {{
            color: {PALETTE["text"]};
            font-size: 2.2rem;
            line-height: 1.05;
            font-weight: 800;
            margin-bottom: 6px;
        }}
        .hero-subtitle {{
            color: {PALETTE["muted"]};
            font-size: 1rem;
        }}
        .metric-card {{
            background: {PALETTE["panel"]};
            border: 1px solid {PALETTE["border"]};
            border-radius: 8px;
            padding: 17px 18px 15px 18px;
            min-height: 122px;
        }}
        .metric-label {{
            color: {PALETTE["muted"]};
            font-size: 0.86rem;
            margin-bottom: 9px;
        }}
        .metric-value {{
            color: {PALETTE["text"]};
            font-size: 1.85rem;
            line-height: 1.1;
            font-weight: 760;
            white-space: nowrap;
        }}
        .metric-delta {{
            margin-top: 9px;
            font-size: 0.86rem;
            font-weight: 650;
        }}
        .delta-good {{ color: {PALETTE["green"]}; }}
        .delta-bad {{ color: {PALETTE["red"]}; }}
        .delta-neutral {{ color: {PALETTE["muted"]}; }}
        .section-title {{
            color: {PALETTE["text"]};
            font-size: 1.25rem;
            font-weight: 760;
            margin: 18px 0 6px 0;
        }}
        .section-note {{
            color: {PALETTE["muted"]};
            margin-bottom: 12px;
        }}
        div[data-testid="stDataFrame"] {{
            border: 1px solid {PALETTE["border"]};
            border-radius: 8px;
            overflow: hidden;
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}
        .stTabs [data-baseweb="tab"] {{
            background: {PALETTE["panel"]};
            border: 1px solid {PALETTE["border"]};
            border-radius: 8px;
            padding: 8px 14px;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


def fmt_int(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "0"
    return f"{int(round(float(value))):,}".replace(",", ".")


def fmt_pct(value: float | int | None, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "0,0%"
    return f"{float(value):.{decimals}f}%".replace(".", ",")


def fmt_float(value: float | int | None, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "0"
    return f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def find_header_row(raw: pd.DataFrame) -> int:
    for idx in range(min(12, len(raw))):
        values = {str(v).strip().lower() for v in raw.iloc[idx].dropna().tolist()}
        if {"fecha", "galpon", "huevos", "produccion"}.issubset(values):
            return idx
    return 0


@st.cache_data(ttl=300)
def load_excel(file_bytes: bytes | None = None) -> pd.DataFrame:
    source = file_bytes if file_bytes is not None else DATA_PATH
    raw = pd.read_excel(source, header=None)
    header_row = find_header_row(raw)
    df = raw.iloc[header_row + 1 :].copy()
    df.columns = [str(c).strip() for c in raw.iloc[header_row].tolist()]
    df = df.loc[:, [c for c in df.columns if c and c.lower() != "nan"]]
    df = df.dropna(how="all")

    required = [DATE_COL, HOUSE_COL, "Huevos", "Produccion"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {', '.join(missing)}")

    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df[HOUSE_COL] = df[HOUSE_COL].astype(str).str.strip()
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=[DATE_COL, HOUSE_COL]).sort_values([DATE_COL, HOUSE_COL])
    df["Semana"] = df[DATE_COL].dt.to_period("W-MON").apply(lambda p: p.start_time)
    df["Mes"] = df[DATE_COL].dt.to_period("M").dt.to_timestamp()
    df["Huevos x gallina"] = (df["Huevos"] / df["Gallinas"]).where(df["Gallinas"].gt(0))
    df["Mortandad % diaria"] = (df["Mortandad"] / df["Gallinas"] * 100).where(df["Gallinas"].gt(0))
    df["Agua x gallina"] = (df["consumo_agua"] / df["Gallinas"]).where(df["Gallinas"].gt(0))
    df["Balanceado g ave dia"] = (df["Cons. Balanceado"] * 1000 / df["Gallinas"]).where(df["Gallinas"].gt(0))
    df["Edad semana"] = df.apply(lambda row: age_for_house(row[HOUSE_COL], row[DATE_COL]), axis=1)
    df = add_targets(df)
    return df


def normalize_house(value: object) -> str:
    text = str(value or "").strip().upper()
    if text.startswith("GALPON"):
        number = "".join(ch for ch in text if ch.isdigit())
        return f"GALPON {number}" if number else text
    number = "".join(ch for ch in text if ch.isdigit())
    return f"GALPON {number}" if number else text


def age_for_house(house: object, date_value: object) -> float | None:
    house_key = normalize_house(house)
    anchor = AGE_ANCHORS.get(house_key)
    date = pd.to_datetime(date_value, errors="coerce")
    if not anchor or pd.isna(date):
        return None
    anchor_date = pd.Timestamp(anchor["date"])
    delta_weeks = (date.normalize() - anchor_date).days // 7
    return anchor["week"] + delta_weeks


def target_for_week(week: float | int | None) -> pd.Series:
    if week is None or pd.isna(week):
        return pd.Series(
            {
                "Meta prod min": pd.NA,
                "Meta prod max": pd.NA,
                "Mortandad acum ref %": pd.NA,
                "Balanceado min g": pd.NA,
                "Balanceado max g": pd.NA,
            }
        )
    target = TARGETS.iloc[(TARGETS["Edad semana"] - float(week)).abs().argsort()].iloc[0]
    return target.drop(labels=["Edad semana"])


def add_targets(df: pd.DataFrame) -> pd.DataFrame:
    target_values = df["Edad semana"].apply(target_for_week)
    enriched = pd.concat([df.reset_index(drop=True), target_values.reset_index(drop=True)], axis=1)
    enriched["Brecha prod vs meta"] = enriched["Produccion"] - enriched["Meta prod min"]
    enriched["Balanceado dentro meta"] = (
        enriched["Balanceado g ave dia"].ge(enriched["Balanceado min g"])
        & enriched["Balanceado g ave dia"].le(enriched["Balanceado max g"])
    )
    return enriched


def extract_first_number(value: object) -> float:
    if pd.isna(value):
        return 0.0
    text = str(value).strip().lower().replace(",", ".")
    if not text or text == "nan":
        return 0.0
    match = pd.Series([text]).str.extract(r"(\d+(?:\.\d+)?)", expand=False).iloc[0]
    return float(match) if pd.notna(match) else 0.0


@st.cache_data(ttl=300)
def load_classification() -> pd.DataFrame:
    if not CLASSIFICATION_PATH.exists():
        return pd.DataFrame()

    raw = pd.read_excel(CLASSIFICATION_PATH, sheet_name="Respuestas de formulario 1")
    raw.columns = [str(col).strip() for col in raw.columns]
    if raw.empty or "Número de galpón" not in raw.columns:
        return pd.DataFrame()

    df = raw.copy()
    df["Fecha"] = pd.to_datetime(df.get("Fecha de puesta"), errors="coerce")
    df["Fecha clasificado"] = pd.to_datetime(df.get("Fecha de clasificado"), errors="coerce")
    house_raw = df["Número de galpón"].astype(str).str.split("/", n=1, expand=True)[0]
    df[HOUSE_COL] = house_raw.apply(normalize_house)

    category_cols = ["Tipo A", "Tipo S", "Tipo B", "Tipo C", "Tipo Yumbo"]
    for col in category_cols + ["Total de huevos"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    for col in ["Rotos", "Picado", "Huevos Sucios"]:
        if col in df.columns:
            df[col] = df[col].apply(extract_first_number)
        else:
            df[col] = 0

    df = df[df["Fecha"].ge(pd.Timestamp("2026-04-27"))].copy()
    df["Clasificados"] = df[category_cols + ["Rotos", "Picado", "Huevos Sucios"]].sum(axis=1)
    df["Base pct"] = df["Total de huevos"].where(df["Total de huevos"].gt(0), df["Clasificados"])
    for col in category_cols + ["Rotos", "Picado", "Huevos Sucios"]:
        df[f"{col} %"] = (df[col] / df["Base pct"] * 100).where(df["Base pct"].gt(0), 0)

    return df.dropna(subset=["Fecha", HOUSE_COL])


def period_delta(current: float, previous: float, higher_is_good: bool = True, suffix: str = "") -> str:
    if previous == 0 or pd.isna(previous):
        return "Sin comparativo"
    delta = current - previous
    sign = "+" if delta >= 0 else ""
    klass = "delta-good" if (delta >= 0) == higher_is_good else "delta-bad"
    return f'<span class="{klass}">{sign}{fmt_float(delta, 1)}{suffix} vs. periodo anterior</span>'


def metric_card(label: str, value: str, delta_html: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-delta">{delta_html or '<span class="delta-neutral">Periodo filtrado</span>'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def chart_layout(fig: go.Figure, height: int = 430) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor=PALETTE["bg"],
        plot_bgcolor=PALETTE["bg"],
        font_color=PALETTE["muted"],
        margin=dict(l=10, r=12, t=78, b=18),
        title=dict(y=0.98, yanchor="top", pad=dict(b=22)),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="left",
            x=0,
            bgcolor="rgba(13,17,23,0.78)",
            bordercolor="rgba(42,53,69,0.55)",
            borderwidth=1,
            font=dict(size=12),
        ),
    )
    fig.update_xaxes(gridcolor="#202a37", zerolinecolor="#202a37")
    fig.update_yaxes(gridcolor="#202a37", zerolinecolor="#202a37")
    return fig


def aggregate_period(df: pd.DataFrame, period_col: str) -> pd.DataFrame:
    grouped = (
        df.groupby([period_col, HOUSE_COL], as_index=False)
        .agg(
            Huevos=("Huevos", "sum"),
            Gallinas=("Gallinas", "mean"),
            Mortandad=("Mortandad", "sum"),
            Produccion=("Produccion", "mean"),
            Balanceado=("Cons. Balanceado", "sum"),
            Balanceado_calc=("Calc. Balanceado", "mean"),
            Temperatura=("Temperatura", "mean"),
            Agua=("consumo_agua", "sum"),
            Agua_x_gallina=("Agua x gallina", "mean"),
            Edad_semana=("Edad semana", "max"),
        )
        .sort_values(period_col)
    )
    grouped["Edad semana"] = grouped["Edad_semana"]
    return grouped


def build_house_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby(HOUSE_COL, as_index=False)
        .agg(
            Dias=(DATE_COL, "nunique"),
            Desde=(DATE_COL, "min"),
            Hasta=(DATE_COL, "max"),
            Huevos=("Huevos", "sum"),
            Produccion_prom=("Produccion", "mean"),
            Gallinas_prom=("Gallinas", "mean"),
            Mortandad=("Mortandad", "sum"),
            Balanceado=("Cons. Balanceado", "sum"),
            Agua=("consumo_agua", "sum"),
            Temp_prom=("Temperatura", "mean"),
        )
        .sort_values("Huevos", ascending=False)
    )
    summary["Mortandad %"] = summary["Mortandad"] / summary["Gallinas_prom"] * 100
    summary["Huevos / ave / dia"] = summary["Huevos"] / summary["Gallinas_prom"] / summary["Dias"]
    return summary


def build_latest_status(df: pd.DataFrame) -> pd.DataFrame:
    latest = df.sort_values(DATE_COL).groupby(HOUSE_COL, as_index=False).tail(1).copy()
    latest["Estado producción"] = latest["Brecha prod vs meta"].apply(
        lambda gap: "OK" if pd.notna(gap) and gap >= 0 else "Bajo meta"
    )
    latest["Estado balanceado"] = latest["Balanceado dentro meta"].apply(lambda ok: "OK" if ok else "Revisar")
    latest["Fecha"] = latest[DATE_COL].dt.strftime("%d/%m/%Y")
    latest["Meta producción"] = latest.apply(
        lambda row: f'{fmt_pct(row["Meta prod min"])} - {fmt_pct(row["Meta prod max"])}',
        axis=1,
    )
    latest["Meta balanceado"] = latest.apply(
        lambda row: f'{fmt_int(row["Balanceado min g"])} - {fmt_int(row["Balanceado max g"])}',
        axis=1,
    )
    cols = [
        HOUSE_COL,
        "Fecha",
        "Edad semana",
        "Produccion",
        "Meta producción",
        "Brecha prod vs meta",
        "Estado producción",
        "Mortandad",
        "Mortandad % diaria",
        "Calc. Balanceado",
        "Meta balanceado",
        "Estado balanceado",
        "Huevos",
        "Gallinas",
    ]
    return latest[cols].sort_values([HOUSE_COL])


def build_classification_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    cols = ["Tipo A", "Tipo S", "Tipo B", "Tipo C", "Tipo Yumbo", "Rotos", "Picado", "Huevos Sucios", "Total de huevos"]
    summary = df.groupby(HOUSE_COL, as_index=False)[cols].sum()
    base = summary["Total de huevos"].where(summary["Total de huevos"].gt(0), summary[cols[:-1]].sum(axis=1))
    for col in cols[:-1]:
        summary[f"{col} %"] = (summary[col] / base * 100).where(base.gt(0), 0)
    summary["A + S %"] = summary["Tipo A %"] + summary["Tipo S %"]
    return summary.sort_values("A + S %", ascending=False)


uploaded = st.sidebar.file_uploader("Informe de galpones", type=["xlsx"])
file_bytes = uploaded.getvalue() if uploaded else None

try:
    df_all = load_excel(file_bytes)
except Exception as exc:
    st.error(f"No pude leer el informe: {exc}")
    st.stop()

min_date = df_all[DATE_COL].min().date()
max_date = df_all[DATE_COL].max().date()
houses = sorted(df_all[HOUSE_COL].dropna().unique().tolist())
classification_all = load_classification()

st.sidebar.markdown("### Filtros")
selected_houses = st.sidebar.multiselect("Galpones", houses, default=houses)
focus_house = st.sidebar.selectbox("Galpón foco", selected_houses or houses)
date_range = st.sidebar.date_input(
    "Rango de fechas",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
trend_grain = st.sidebar.radio("Tendencia", ["Diaria", "Semanal", "Mensual"], horizontal=True)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

mask = (
    df_all[HOUSE_COL].isin(selected_houses)
    & df_all[DATE_COL].dt.date.ge(start_date)
    & df_all[DATE_COL].dt.date.le(end_date)
)
df = df_all.loc[mask].copy()
class_mask = classification_all[HOUSE_COL].isin(selected_houses) if not classification_all.empty else pd.Series(dtype=bool)
classification = classification_all.loc[class_mask].copy() if not classification_all.empty else pd.DataFrame()

st.markdown(
    f"""
    <div class="hero-band">
        <div class="hero-title">KPI Productivo Galpones</div>
        <div class="hero-subtitle">
            Evolución por edad semanal: producción vs meta, mortandad, balanceado y clasificación de huevos.
            Datos del {min_date.strftime('%d/%m/%Y')} al {max_date.strftime('%d/%m/%Y')}.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if df.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

days = max(df[DATE_COL].nunique(), 1)
current_start = pd.Timestamp(end_date) - pd.Timedelta(days=13)
previous_start = current_start - pd.Timedelta(days=14)
current_14 = df_all[
    (df_all[HOUSE_COL].isin(selected_houses))
    & df_all[DATE_COL].ge(current_start)
    & df_all[DATE_COL].le(pd.Timestamp(end_date))
]
previous_14 = df_all[
    (df_all[HOUSE_COL].isin(selected_houses))
    & df_all[DATE_COL].ge(previous_start)
    & df_all[DATE_COL].lt(current_start)
]

total_eggs = float(df["Huevos"].sum())
avg_prod = float(df["Produccion"].mean())
avg_hens = float(df.groupby(DATE_COL)["Gallinas"].sum().mean())
total_deaths = float(df["Mortandad"].sum())
daily_mortality = float(df["Mortandad"].sum() / df["Gallinas"].sum() * 100)
eggs_per_hen_day = float(total_eggs / df["Gallinas"].sum())
focus_latest = df[df[HOUSE_COL] == focus_house].sort_values(DATE_COL).tail(1)
if focus_latest.empty:
    focus_latest = df.sort_values(DATE_COL).tail(1)
focus_row = focus_latest.iloc[0]
focus_gap = float(focus_row.get("Brecha prod vs meta", 0))

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    metric_card("Galpón foco", focus_house.replace("GALPON", "Galpón"), f'<span class="delta-neutral">Semana {fmt_int(focus_row["Edad semana"])}</span>')
with k2:
    metric_card(
        "Producción actual",
        fmt_pct(focus_row["Produccion"]),
        f'<span class="{"delta-good" if focus_gap >= 0 else "delta-bad"}">{fmt_float(focus_gap, 1)} pp vs meta min.</span>',
    )
with k3:
    metric_card("Mortandad actual", fmt_int(focus_row["Mortandad"]), f'<span class="delta-neutral">{fmt_pct(focus_row["Mortandad % diaria"], 3)} diaria</span>')
with k4:
    metric_card(
        "Balanceado",
        f'{fmt_float(focus_row["Balanceado g ave dia"], 1)} g',
        f'<span class="delta-neutral">Meta {fmt_int(focus_row["Balanceado min g"])}-{fmt_int(focus_row["Balanceado max g"])} g/ave</span>',
    )
with k5:
    metric_card("Huevos acumulados", fmt_int(total_eggs), period_delta(current_14["Huevos"].sum(), previous_14["Huevos"].sum(), True, ""))

period_col = {"Diaria": DATE_COL, "Semanal": "Semana", "Mensual": "Mes"}[trend_grain]
trend = aggregate_period(df, period_col)

tab_general, tab_galpones, tab_clasificacion, tab_relaciones, tab_datos = st.tabs(
    ["Por galpón", "Semaforo", "Clasificacion", "Relaciones", "Datos"]
)

with tab_general:
    focus_df = df[df[HOUSE_COL] == focus_house].copy()
    focus_trend = aggregate_period(focus_df, period_col)
    focus_trend["Meta min"] = focus_trend["Edad semana"].apply(lambda w: target_for_week(w)["Meta prod min"])
    focus_trend["Meta max"] = focus_trend["Edad semana"].apply(lambda w: target_for_week(w)["Meta prod max"])
    focus_trend["Balanceado min g"] = focus_trend["Edad semana"].apply(lambda w: target_for_week(w)["Balanceado min g"])
    focus_trend["Balanceado max g"] = focus_trend["Edad semana"].apply(lambda w: target_for_week(w)["Balanceado max g"])
    st.markdown('<div class="section-title">Producción por edad semanal</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-note">La meta se calcula por semana de edad del lote; la edad avanza automáticamente cada 7 días.</div>',
        unsafe_allow_html=True,
    )
    fig_prod = go.Figure()
    fig_prod.add_trace(go.Scatter(x=focus_trend[period_col], y=focus_trend["Meta min"], name="Meta min", line=dict(color=PALETTE["amber"], dash="dot")))
    fig_prod.add_trace(go.Scatter(x=focus_trend[period_col], y=focus_trend["Meta max"], name="Meta max", line=dict(color=PALETTE["green"], dash="dot")))
    fig_prod.add_trace(go.Scatter(x=focus_trend[period_col], y=focus_trend["Produccion"], name="Producción real", mode="lines+markers", line=dict(color=PALETTE["blue"], width=3)))
    fig_prod.update_layout(title=f"{focus_house.replace('GALPON', 'Galpón')} | Producción real vs curva objetivo")
    st.plotly_chart(chart_layout(fig_prod), width='stretch')

    left, right = st.columns([1.15, 0.85])
    with left:
        fig_mort_focus = px.bar(
            focus_trend,
            x=period_col,
            y="Mortandad",
            labels={"Mortandad": "Mortandad", period_col: "Fecha"},
            title=f"{focus_house.replace('GALPON', 'Galpón')} | Mortandad por periodo",
            color_discrete_sequence=[PALETTE["red"]],
        )
        st.plotly_chart(chart_layout(fig_mort_focus), width='stretch')
    with right:
        fig_feed_focus = go.Figure()
        fig_feed_focus.add_trace(go.Scatter(x=focus_trend[period_col], y=focus_trend["Balanceado min g"], name="Min g/ave", line=dict(color=PALETTE["amber"], dash="dot")))
        fig_feed_focus.add_trace(go.Scatter(x=focus_trend[period_col], y=focus_trend["Balanceado max g"], name="Max g/ave", line=dict(color=PALETTE["green"], dash="dot")))
        fig_feed_focus.add_trace(go.Scatter(x=focus_trend[period_col], y=focus_trend["Balanceado_calc"], name="Calc. ERP", mode="lines+markers", line=dict(color=PALETTE["teal"], width=3)))
        fig_feed_focus.update_layout(title=f"{focus_house.replace('GALPON', 'Galpón')} | Balanceado vs meta")
        st.plotly_chart(chart_layout(fig_feed_focus), width='stretch')

with tab_galpones:
    latest_status = build_latest_status(df)
    st.markdown('<div class="section-title">Semáforo actual por galpón</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-note">Cada fila toma el último dato disponible de cada galpón y compara contra la meta por edad semanal.</div>',
        unsafe_allow_html=True,
    )
    st.dataframe(
        latest_status.assign(
            **{
                "Edad semana": latest_status["Edad semana"].round(0).astype("Int64"),
                "Produccion": latest_status["Produccion"].round(2),
                "Brecha prod vs meta": latest_status["Brecha prod vs meta"].round(2),
                "Mortandad % diaria": latest_status["Mortandad % diaria"].round(3),
                "Calc. Balanceado": latest_status["Calc. Balanceado"].round(1),
            }
        ),
        width='stretch',
        hide_index=True,
        column_config={
            "Produccion": st.column_config.ProgressColumn("Producción %", min_value=0, max_value=100, format="%.2f"),
            "Brecha prod vs meta": st.column_config.NumberColumn("Brecha pp", format="%.2f"),
            "Mortandad % diaria": st.column_config.NumberColumn("Mort. diaria %", format="%.3f"),
            "Calc. Balanceado": st.column_config.NumberColumn("Balanceado g/ave", format="%.1f"),
        },
    )

    a, b = st.columns(2)
    with a:
        fig_mort = px.line(
            trend,
            x=period_col,
            y="Mortandad",
            color=HOUSE_COL,
            markers=True,
            labels={"Mortandad": "Mortandad", period_col: "Fecha"},
            title="Mortandad por periodo",
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        st.plotly_chart(chart_layout(fig_mort), width='stretch')
    with b:
        fig_stock = px.line(
            trend,
            x=period_col,
            y="Gallinas",
            color=HOUSE_COL,
            markers=True,
            labels={"Gallinas": "Gallinas promedio", period_col: "Fecha"},
            title="Evolución de aves por galpón",
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        st.plotly_chart(chart_layout(fig_stock), width='stretch')

with tab_clasificacion:
    st.markdown('<div class="section-title">Clasificación de huevos desde 27/04/2026</div>', unsafe_allow_html=True)
    if classification.empty:
        st.info("No hay datos de clasificación para los filtros seleccionados.")
    else:
        class_summary = build_classification_summary(classification)
        pct_cols = ["Tipo S %", "Tipo A %", "Tipo B %", "Tipo C %", "Tipo Yumbo %", "Rotos %", "Picado %", "Huevos Sucios %"]
        class_long = class_summary.melt(
            id_vars=[HOUSE_COL],
            value_vars=pct_cols,
            var_name="Tipo",
            value_name="Porcentaje",
        )
        class_long["Tipo"] = class_long["Tipo"].str.replace(" %", "", regex=False)
        fig_class = px.bar(
            class_long,
            x=HOUSE_COL,
            y="Porcentaje",
            color="Tipo",
            barmode="stack",
            labels={"Porcentaje": "% sobre total clasificado", HOUSE_COL: "Galpón"},
            title="Mix porcentual por galpón",
            color_discrete_map={
                "Tipo S": PALETTE["green"],
                "Tipo A": PALETTE["blue"],
                "Tipo B": PALETTE["amber"],
                "Tipo C": PALETTE["red"],
                "Tipo Yumbo": PALETTE["teal"],
                "Rotos": "#9b6bff",
                "Picado": "#c08457",
                "Huevos Sucios": "#8a95a8",
            },
        )
        st.plotly_chart(chart_layout(fig_class), width='stretch')

        c1, c2 = st.columns([1, 1])
        with c1:
            focus_class = classification[classification[HOUSE_COL] == focus_house].copy()
            daily_class = (
                focus_class.groupby("Fecha", as_index=False)[["Tipo A", "Tipo S", "Tipo B", "Tipo C", "Total de huevos"]]
                .sum()
                .sort_values("Fecha")
            )
            if not daily_class.empty:
                for col in ["Tipo A", "Tipo S", "Tipo B", "Tipo C"]:
                    daily_class[f"{col} %"] = daily_class[col] / daily_class["Total de huevos"].where(daily_class["Total de huevos"].gt(0), 1) * 100
                daily_long = daily_class.melt(
                    id_vars=["Fecha"],
                    value_vars=["Tipo S %", "Tipo A %", "Tipo B %", "Tipo C %"],
                    var_name="Tipo",
                    value_name="Porcentaje",
                )
                daily_long["Tipo"] = daily_long["Tipo"].str.replace(" %", "", regex=False)
                fig_daily = px.line(
                    daily_long,
                    x="Fecha",
                    y="Porcentaje",
                    color="Tipo",
                    markers=True,
                    title=f"{focus_house.replace('GALPON', 'Galpón')} | Evolución del mix",
                )
                st.plotly_chart(chart_layout(fig_daily), width='stretch')
        with c2:
            st.dataframe(
                class_summary[[HOUSE_COL, "Total de huevos", "A + S %", "Tipo S %", "Tipo A %", "Tipo B %", "Tipo C %", "Rotos %", "Picado %", "Huevos Sucios %"]]
                .round(2),
                width='stretch',
                hide_index=True,
                column_config={
                    "Total de huevos": st.column_config.NumberColumn("Total clasificado", format="%d"),
                    "A + S %": st.column_config.NumberColumn("A+S %", format="%.2f"),
                },
            )

with tab_relaciones:
    st.markdown('<div class="section-title">Señales de eficiencia y ambiente</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        fig_feed = px.scatter(
            df,
            x="Calc. Balanceado",
            y="Produccion",
            color=HOUSE_COL,
            size="Huevos",
            hover_data=[DATE_COL, "Gallinas", "Mortandad", "Temperatura"],
            labels={"Calc. Balanceado": "Balanceado calculado", "Produccion": "Producción %"},
            title="Producción vs. balanceado calculado",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        st.plotly_chart(chart_layout(fig_feed), width='stretch')
    with c2:
        fig_temp = px.scatter(
            df,
            x="Temperatura",
            y="Produccion",
            color=HOUSE_COL,
            size="consumo_agua",
            hover_data=[DATE_COL, "Huevos", "Gallinas"],
            labels={"Temperatura": "Temperatura", "Produccion": "Producción %"},
            title="Producción vs. temperatura",
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        st.plotly_chart(chart_layout(fig_temp), width='stretch')

    water = aggregate_period(df, period_col)
    fig_water = px.line(
        water,
        x=period_col,
        y="Agua_x_gallina",
        color=HOUSE_COL,
        markers=True,
        labels={"Agua_x_gallina": "Agua por gallina", period_col: "Fecha"},
        title="Consumo de agua por ave",
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    st.plotly_chart(chart_layout(fig_water), width='stretch')

with tab_datos:
    st.markdown('<div class="section-title">Base filtrada</div>', unsafe_allow_html=True)
    visible = df[
        [
            DATE_COL,
            HOUSE_COL,
            "Gallinas",
            "Huevos",
            "Produccion",
            "Mortandad",
            "Cons. Balanceado",
            "Calc. Balanceado",
            "Temperatura",
            "consumo_agua",
            "Observaciones",
        ]
    ].copy()
    visible[DATE_COL] = visible[DATE_COL].dt.strftime("%d/%m/%Y")
    st.dataframe(visible, width='stretch', hide_index=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Descargar datos filtrados",
        data=csv,
        file_name="galpones_filtrado.csv",
        mime="text/csv",
    )
