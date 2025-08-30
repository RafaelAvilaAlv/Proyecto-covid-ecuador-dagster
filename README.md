# Proyecto-covid-ecuador-dagster

Pipeline reproducible de datos COVID-19 (Ecuador y comparativo regional) construido con **Dagster**, con exportación a **Excel** y controles de calidad.

- **Curso:** Python – Análisis de Datos y Ecosistemas Modernos de Analítica  
- **Integrantes:** Rafael Avila, José Morocho, Karla Méndez  
- **Tema:** Pipeline de datos COVID-19 (Ecuador y comparativo regional) con Dagster y salida a Excel  
- 📄 Aquí el **[Informe Técnico](https://github.com/RafaelAvilaAlv/Proyecto-covid-ecuador-dagster/blob/main/Informe%20T%C3%A9cnico.pdf)**

## 1) Objetivo

Construir un pipeline que:
- Se descargua los datos públicos de COVID-19 de **Our World in Data (OWID)**.
- Se filtra y se procesa países seleccionados.
- Calculamos métricas epidemiológicas (incidencia 7d y factor de crecimiento 7d).
- Exportamos un **reporte en Excel** con métricas y resultados de controles.

---

## 2) Arquitectura (Dagster)

El proyecto está modelado como **assets** (recursos) y **checks** (controles) de Dagster.

### Assets
- **leer_datos**  
  Descarga el CSV de OWID (con fallback si falla el dominio principal) y lo carga a un DataFrame.  
  Variables usadas:  
  - `OWID_URL` (por defecto: `https://covid.ourworldindata.org/data/owid-covid-data.csv`)  
  - `OWID_URL_FALLBACK` (por defecto: raw de GitHub de OWID).

- **datos_procesados**  
  Filtra países (por variables de entorno; ver Ejecución), selecciona columnas mínimas y ordena por fecha.

- **metrica_incidencia_7d**  
  Incidencia por 100k habitantes con media móvil de 7 días.

- **metrica_factor_crec_7d**  
  Factor de crecimiento = casos 7d actuales / casos 7d previos (`shift(7)`).

- **reporte_excel_covid**  
  Exporta métricas a `out/reporte_covid.xlsx` (2 hojas: incidencias y factor de crecimiento).

### Checks
- **check_entrada_basica** (sobre `leer_datos`)  
  Claves no nulas, población > 0, fechas válidas y sin duplicados.

- **check_incidencia_rango** (sobre `metrica_incidencia_7d`)  
  Sanidad del rango de la incidencia (detección de valores imposibles/erróneos).

---

## 3) Estructura del repositorio

```
.
├─ src/
│  └─ covid_ec/
│     ├─ defs/                # Definitions (entrypoint de Dagster)
│     ├─ __init__.py
│     ├─ assets.py            # Assets y checks del pipeline
│     └─ definitions.py       # Ensambla assets + checks en Definitions
├─ scripts/
│  └─ eda_inicial.py          # (opcional) Descarga/EDA manual para diagnóstico rápido
├─ out/
│  └─ reporte_covid.xlsx      # Salida final (git-ignored)
├─ data/                      # CSVs generados por EDA (git-ignored)
├─ requirements.txt
└─ README.md
```

> `data/` y `out/` están en `.gitignore` para no versionar datos pesados o derivados.

---

## 4) Requisitos

- Python 3.11 o superior
- Dependencias (resumen de `requirements.txt`):  
  `dagster>=1.6`, `dagster-webserver>=1.6`, `pandas>=2.1`, `requests>=2.31`,  
  `duckdb>=1.0`, `pyarrow>=15`, `openpyxl>=3.1`

---

## 5) Instalación y ejecución

### 5.1 Crear entorno e instalar dependencias

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
python -m pip install -U pip
pip install -r requirements.txt
```

### 5.2 Variables de entorno (países y fallback)

```powershell
$env:PYTHONPATH="src"   # para la sesión actual
$env:PAISES_1="Ecuador"
$env:PAISES_2="Peru"
$env:OWID_URL_FALLBACK="https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv"
# (opcional) persistir: setx PYTHONPATH "src"
```

> Puedes ajustar `PAISES_1`, `PAISES_2`, etc., según los países a analizar.

### 5.3 Levantar la UI de Dagster

```bash
dagster dev -m covid_ec.defs
```

Luego abre `http://127.0.0.1:3000`, entra a **Assets** → **Materialize all** (o “Open launchpad”) y ejecuta.  
La salida quedará en `out/reporte_covid.xlsx`.

---

## 6) Datos

- Fuente principal: Our World in Data (OWID) – COVID-19 dataset.
- Fallback: raw de GitHub de OWID (útil cuando falla el DNS de `covid.ourworldindata.org`).
- Licencia de datos: consultar OWID (usualmente CC BY). Citar la fuente al usar tablas o gráficos.

---

## 7) Salidas y validación

- Excel: `out/reporte_covid.xlsx`  
  - Hojas: `metrica_incidencia_7d`, `metrica_factor_crec_7d`
- Metadata en Dagster: cada asset muestra rutas de almacenamiento y logs.
- Checks: si `check_entrada_basica` marca Failed, revisar:
  - columnas clave vacías o nulas
  - fechas inválidas (muy antiguas o futuras)
  - población <= 0 o duplicados inesperados
  - si falla la descarga principal, verificar que se usó el fallback

---

## 8) Troubleshooting

- Error DNS o descarga OWID  
  Verifica que `OWID_URL_FALLBACK` esté configurado (ver 5.2).

- No se ve el módulo (imports fallan)  
  Asegura `PYTHONPATH=src` (o `$env:PYTHONPATH="src"` en PowerShell).

- Excel vacío o incompleto  
  Confirma que los assets aguas arriba se materializaron con éxito y que los checks están OK.

- Re-ejecución limpia  
  En la UI: **Assets → Materialize all**. Revisa **Runs** y **Events** para auditar pasos.

---
