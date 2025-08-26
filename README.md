# Proyecto-covid-ecuador-dagster

Pipeline reproducible de datos COVID-19 (Ecuador y comparativo regional) construido con **Dagster**, con exportación a **Excel** y controles de calidad.

- **Curso:** Python – Análisis de Datos y Ecosistemas Modernos de Analítica
- **Integrantes:** Rafael Ávila, José Morocho
- **Tema:** Pipeline de datos COVID-19 (Ecuador y comparativo regional) con Dagster y salida a Excel

---

## 1) Objetivo

Construir un pipeline que:
- Descargue los datos públicos de COVID-19 de **Our World in Data (OWID)**.
- Filtre y procese países seleccionados.
- Calcule métricas epidemiológicas (incidencia 7d y factor de crecimiento 7d).
- Exporte un **reporte en Excel** con métricas y resultados de controles.

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
.
├─ src/
│ └─ covid_ec/
│ ├─ defs/ # Definitions (entrypoint de Dagster)
│ ├─ init.py
│ ├─ assets.py # Assets y checks del pipeline
│ └─ definitions.py # Ensambla assets + checks en Definitions
├─ scripts/
│ └─ eda_inicial.py # (opcional) Descarga/EDA manual para diagnóstico rápido
├─ out/
│ └─ reporte_covid.xlsx # Salida final (git-ignored)
├─ data/ # CSVs generados por EDA (git-ignored)
├─ requirements.txt
└─ README.md




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

**Linux/macOS**
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt


