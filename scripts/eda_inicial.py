import os
import requests
import pandas as pd

PRIMARY = os.getenv("OWID_URL", "https://covid.ourworldindata.org/data/owid-covid-data.csv")
FALLBACK = os.getenv("OWID_URL_FALLBACK", "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv")
PAISES = [p.strip() for p in os.getenv("PAISES", "Ecuador,Peru").split(",")]

def descargar(url: str) -> str:
    print(f"Descargando: {url}")
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.text

os.makedirs("data", exist_ok=True)

# Descarga con fallback
try:
    texto = descargar(PRIMARY)
except Exception as e:
    print(f"⚠️ Falla con primaria: {e}\n→ Probando fallback…")
    texto = descargar(FALLBACK)

raw_path = "data/owid_raw.csv"
with open(raw_path, "w", encoding="utf-8") as f:
    f.write(texto)
print(f"Guardado: {raw_path}")

# Perfilado básico solicitado
df = pd.read_csv(raw_path, parse_dates=["date"])
df = df[df["location"].isin(PAISES)].copy()

total = len(df)
fecha_min = df["date"].min()
fecha_max = df["date"].max()
dupes = int(df.duplicated(["location","date"]).sum())
unicos_ok = dupes == 0

tabla = pd.DataFrame([
    {"kpi":"filas","valor": total},
    {"kpi":"fecha_min","valor": fecha_min.date().isoformat() if pd.notna(fecha_min) else None},
    {"kpi":"fecha_max","valor": fecha_max.date().isoformat() if pd.notna(fecha_max) else None},
    {"kpi":"unicos_location_date","valor": unicos_ok},
])

def resumen_col(col):
    nulos = int(df[col].isna().sum()) if col in df.columns else total
    pct = round(nulos*100.0/total, 2) if total else 0.0
    minimo = df[col].min(skipna=True) if col in df.columns else None
    maximo = df[col].max(skipna=True) if col in df.columns else None
    return {"columna": col, "n_nulos": nulos, "pct_nulos": pct, "min": minimo, "max": maximo}

detalle = pd.DataFrame([resumen_col(c) for c in ["new_cases", "people_vaccinated", "population"]])

tabla.to_csv("data/tabla_perfilado.csv", index=False)
detalle.to_csv("data/tabla_perfilado_detalle.csv", index=False)

print("Perfil general -> data/tabla_perfilado.csv")
print("Perfil por columna -> data/tabla_perfilado_detalle.csv")
print("Listo.")
