from dagster import asset, AssetExecutionContext, asset_check, AssetCheckResult
import os, io, datetime as dt
import pandas as pd
import numpy as np
import requests

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
OWID_URL = os.getenv("OWID_URL", "https://covid.ourworldindata.org/data/owid-covid-data.csv")
OWID_URL_FALLBACK = os.getenv(
    "OWID_URL_FALLBACK",
    "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv",
)
PAIS_1 = os.getenv("PAIS_1", "Ecuador")
PAIS_2 = os.getenv("PAIS_2", "Peru")


# ---------------------------------------------------------------------
# Util
# ---------------------------------------------------------------------
def _descargar(url: str) -> str:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.text


# ---------------------------------------------------------------------
# Assets & Checks
# ---------------------------------------------------------------------
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
    cols = [
        "location",
        "date",
        "new_cases",
        "total_cases",          # <-- importante para 'casos_vacunados'
        "people_vaccinated",
        "population",
    ]
    df = leer_datos[cols].copy()

    # Limpieza básica
    df = df.dropna(subset=["location", "date", "population"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Fuerza numéricos para evitar errores aguas abajo
    for c in ["new_cases", "total_cases", "people_vaccinated", "population"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["new_cases"] = df["new_cases"].fillna(0)

    # Filtra los países configurados y ordena por fecha
    df = df[df["location"].isin([PAIS_1, PAIS_2])].sort_values(["location", "date"])
    return df


@asset
def metrica_incidencia_7d(datos_procesados: pd.DataFrame) -> pd.DataFrame:
    """Incidencia por 100k con media móvil de 7 días."""
    df = datos_procesados.copy()
    df["incidencia_diaria"] = df["new_cases"] / df["population"] * 100_000
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
    resumen_metricas: pd.DataFrame,   # <-- añade esta dependencia
) -> str:
    os.makedirs("out", exist_ok=True)
    path = "out/reporte_covid.xlsx"
    with pd.ExcelWriter(path) as w:
        metrica_incidencia_7d.to_excel(w, index=False, sheet_name="incidencia7d")
        metrica_factor_crec_7d.to_excel(w, index=False, sheet_name="factor7d")
        resumen_metricas.to_excel(w, index=False, sheet_name="resumen")  # <-- nueva hoja
    context.log.info(f"Reporte generado: {path}")
    return path



# ---------------------------------------------------------------------
# NUEVO: resumen de casos confirmados y personas vacunadas
# ---------------------------------------------------------------------
@asset(group_name="default")
def casos_vacunados(datos_procesados: pd.DataFrame) -> pd.DataFrame:
    """
    Para cada país configurado, toma la ÚLTIMA fila disponible con:
    - total_cases (Confirmed cases)
    - people_vaccinated (People vaccinated)
    y guarda out/casos_vacunados.csv
    """
    cols = ["location", "date", "total_cases", "people_vaccinated"]
    df = datos_procesados[cols].dropna(subset=["location", "date"]).copy()

    for c in ["total_cases", "people_vaccinated"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Última fecha por país
    df = (
        df.sort_values(["location", "date"])
          .groupby("location", as_index=False)
          .tail(1)
          .reset_index(drop=True)
    )

    os.makedirs("out", exist_ok=True)
    df.to_csv("out/casos_vacunados.csv", index=False)
    return df



@asset(group_name="default")
def resumen_metricas(
    datos_procesados: pd.DataFrame,      # ya viene filtrado a PAIS_1 y PAIS_2
    metrica_incidencia_7d: pd.DataFrame, # para la última incidencia
) -> pd.DataFrame:
    """
    Un renglón por país (PAIS_1 y PAIS_2) con:
    ultima_fecha, fecha_incidencia, incidencia_7, fecha_factor,
    factor_crec_7d, casos_7d, casos_7d_prev.
    Guarda out/resumen_metricas.csv
    """
    # ---- Factor de crecimiento (y casos_7d) a partir de datos_procesados ----
    df = datos_procesados.copy()
    df["cases_7d"] = df.groupby("location")["new_cases"].transform(
        lambda s: s.rolling(7, min_periods=7).sum()
    )
    df["cases_7d_prev"] = df.groupby("location")["cases_7d"].shift(7)
    df["factor_crec_7d"] = (df["cases_7d"] / df["cases_7d_prev"]).replace([np.inf, -np.inf], pd.NA)

    # Último registro por país para factor/7d
    ultimo_factor = (
        df[["location", "date", "factor_crec_7d", "cases_7d", "cases_7d_prev"]]
        .dropna(subset=["location", "date"])
        .sort_values(["location", "date"])
        .groupby("location", as_index=False)
        .tail(1)
        .rename(columns={"date": "fecha_factor"})
    )

    # Último registro por país para incidencia_7d
    ultima_incid = (
        metrica_incidencia_7d.copy()
        .dropna(subset=["location", "date"])
        .sort_values(["location", "date"])
        .groupby("location", as_index=False)
        .tail(1)
        .rename(columns={"date": "fecha_incidencia", "incidencia_7d": "incidencia_7"})
    )

    # Merge y columnas en el orden del screenshot
    out = ultimo_factor.merge(ultima_incid, on="location", how="outer")
    out["ultima_fecha"] = out[["fecha_factor", "fecha_incidencia"]].max(axis=1)
    out = out[
        [
            "location",
            "ultima_fecha",
            "fecha_incidencia",
            "incidencia_7",
            "fecha_factor",
            "factor_crec_7d",
            "cases_7d",
            "cases_7d_prev",
        ]
    ]

    # Formateo para que se vea igual que tu tabla (fechas dd/mm/yyyy, redondeos)
    for c in ["fecha_incidencia", "fecha_factor", "ultima_fecha"]:
        out[c] = pd.to_datetime(out[c], errors="coerce").dt.strftime("%d/%m/%Y")

    # Redondeo y nulos a 0 donde aplica (igual que en tu captura)
    out["incidencia_7"] = pd.to_numeric(out["incidencia_7"], errors="coerce").round(3).fillna(0)
    for c in ["cases_7d", "cases_7d_prev"]:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int)
    out["factor_crec_7d"] = pd.to_numeric(out["factor_crec_7d"], errors="coerce").round(2).fillna(0)

    os.makedirs("out", exist_ok=True)
    out.to_csv("out/resumen_metricas.csv", index=False)
    return out



# --- NUEVO: Excel con el resumen en una sola hoja ---
from dagster import asset, AssetExecutionContext
import os
import pandas as pd

@asset(group_name="default")
def reporte_resumen_excel(
    context: AssetExecutionContext, 
    resumen_metricas: pd.DataFrame
) -> str:
    """
    Genera un Excel de una sola hoja con el resumen de métricas por país.
    Guarda el archivo en: out/reporte_resumen.xlsx
    """
    os.makedirs("out", exist_ok=True)
    path = "out/reporte_resumen.xlsx"

    # Solo por seguridad, ordenamos/seleccionamos columnas esperadas:
    cols = [
        "location",
        "ultima_fecha",
        "fecha_incidencia",
        "incidencia_7d",
        "fecha_factor",
        "factor_crec_7d",
    ]
    df = resumen_metricas.copy()
    df = df[[c for c in cols if c in df.columns]]

    # Una sola hoja llamada 'resumen'
    with pd.ExcelWriter(path) as w:
        df.to_excel(w, index=False, sheet_name="resumen")

    context.log.info(f"Reporte generado: {path}")
    return path
