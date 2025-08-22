from dagster import asset, AssetExecutionContext, asset_check, AssetCheckResult
import os, io, datetime as dt
import pandas as pd
import numpy as np
import requests

OWID_URL = os.getenv("OWID_URL", "https://covid.ourworldindata.org/data/owid-covid-data.csv")
OWID_URL_FALLBACK = os.getenv(
    "OWID_URL_FALLBACK",
    "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv",
)
PAIS_1 = os.getenv("PAIS_1", "Ecuador")
PAIS_2 = os.getenv("PAIS_2", "Peru")

def _descargar(url: str) -> str:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.text

@asset
def leer_datos(context: AssetExecutionContext) -> pd.DataFrame:
    """Descarga el CSV (con fallback) y lo carga a DataFrame."""
    try:
        texto = _descargar(OWID_URL)
    except Exception as e:
        context.log.warning(f"Falla primaria: {e}; usando fallback")
        texto = _descargar(OWID_URL_FALLBACK)

    df = pd.read_csv(io.StringIO(texto))
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    context.log.info(f"Filas={len(df)} Cols={len(df.columns)}")
    return df

@asset_check(asset=leer_datos)
def check_entrada_basica(leer_datos: pd.DataFrame) -> AssetCheckResult:
    """Columnas clave no nulas, población > 0, fechas razonables y sin duplicados."""
    df = leer_datos
    ok = (
        df["location"].notna().all()
        and df["date"].notna().all()
        and df["population"].fillna(0).gt(0).all()
        and df.duplicated(["location", "date"]).sum() == 0
    )
    max_date = pd.to_datetime(df["date"]).max()
    ok = bool(ok and (max_date.date() <= dt.date.today()))
    return AssetCheckResult(passed=ok, metadata={"max_date": str(max_date)})

@asset
def datos_procesados(leer_datos: pd.DataFrame) -> pd.DataFrame:
    """Filtra países y columnas mínimas; ordena por fecha."""
    cols = ["location", "date", "new_cases", "people_vaccinated", "population"]
    df = leer_datos[cols].copy()
    df = df.dropna(subset=["location", "date", "population"])
    df["new_cases"] = df["new_cases"].fillna(0)
    df = df[df["location"].isin([PAIS_1, PAIS_2])].sort_values(["location", "date"])
    return df

@asset
def metrica_incidencia_7d(datos_procesados: pd.DataFrame) -> pd.DataFrame:
    """Incidencia por 100k con media móvil de 7 días."""
    df = datos_procesados.copy()
    df["incidencia_diaria"] = df["new_cases"] / df["population"] * 100000
    df["incidencia_7d"] = (
        df.groupby("location")["incidencia_diaria"]
        .transform(lambda s: s.rolling(7, min_periods=1).mean())
    )
    return df[["location", "date", "incidencia_7d"]]

@asset_check(asset=metrica_incidencia_7d)
def check_incidencia_rango(metrica_incidencia_7d: pd.DataFrame) -> AssetCheckResult:
    """Rango razonable para la serie de incidencia."""
    s = metrica_incidencia_7d["incidencia_7d"].dropna()
    ok = bool(s.between(0, 2000).all())
    return AssetCheckResult(passed=ok, metadata={"n_rows": int(len(s))})

@asset
def metrica_factor_crec_7d(datos_procesados: pd.DataFrame) -> pd.DataFrame:
    """Factor de crecimiento = casos 7d / casos 7d previos (shift 7)."""
    df = datos_procesados.copy()
    df["cases_7d"] = df.groupby("location")["new_cases"].transform(
        lambda s: s.rolling(7, min_periods=7).sum()
    )
    df["cases_7d_prev"] = df.groupby("location")["cases_7d"].shift(7)
    df["factor_crec_7d"] = (df["cases_7d"] / df["cases_7d_prev"]).replace(
        [np.inf, -np.inf], pd.NA
    )
    return df[["location", "date", "factor_crec_7d"]]

@asset
def reporte_excel_covid(
    context: AssetExecutionContext,
    metrica_incidencia_7d: pd.DataFrame,
    metrica_factor_crec_7d: pd.DataFrame,
) -> str:
    """Exporta las métricas a Excel (2 hojas)."""
    os.makedirs("out", exist_ok=True)
    path = "out/reporte_covid.xlsx"
    with pd.ExcelWriter(path) as w:
        metrica_incidencia_7d.to_excel(w, index=False, sheet_name="incidencia7d")
        metrica_factor_crec_7d.to_excel(w, index=False, sheet_name="factor7d")
    context.log.info(f"Reporte generado: {path}")
    return path
