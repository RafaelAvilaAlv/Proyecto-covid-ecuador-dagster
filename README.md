Proyecto-covid-ecuador-dagster

- Curso: Python – Análisis de Datos y Ecosistemas Modernos de Analítica
- Integrantes: Rafael Ávila, José Morocho
- Tema: Pipeline de datos COVID-19 (Ecuador y comparativo regional) con Dagster y salida a Excel.

- 1) Objetivo

Construimos un pipeline reproducible que:
Descargue los datos públicos de COVID-19 de Our World in Data (OWID).
Filtre y procese países seleccionados.
Calculamos métricas epidemiológicas (incidencia 7d y factor de crecimiento 7d).
Exporte un reporte en Excel con las métricas y controles de calidad.


2. Arquitectura (Dagster)

El proyecto está modelado como assets (recursos) y checks (controles) de Dagster:
- Assets
leer_datos
Descarga el CSV de OWID (con fallback si falla el dominio principal) y lo carga a un DataFrame.
Variables usadas:
+ OWID_URL (por defecto: https://covid.ourworldindata.org/data/owid-covid-data.csv)
+ OWID_URL_FALLBACK (por defecto: raw de GitHub de OWID, para evitar problemas DNS).

- datos_procesados
Filtra países (por variables de entorno; ver sección Ejecución), columnas mínimas y ordena por fecha.

- metrica_incidencia_7d
Incidencia por 100k habitantes con media móvil de 7 días.
- metrica_factor_crec_7d
Factor de crecimiento = casos 7d actuales / casos 7d previos (shift 7).
- reporte_excel_covid
Exporta las métricas a out/reporte_covid.xlsx (2 hojas: incidencias y factor de crecimiento).

Checks
+ check_entrada_basica (sobre leer_datos)
Claves no nulas, población > 0, fechas válidas y sin duplicados.
+ check_incidencia_rango (sobre metrica_incidencia_7d)
Sanidad del rango de la incidencia (detección de valores imposibles/erróneos).

3. Estructura del repo
.
├─ src/
│  └─ covid_ec/
│     ├─ defs/                # Definición de Definitions (entrypoint de Dagster)
│     ├─ __init__.py
│     ├─ assets.py            # Assets y checks del pipeline
│     └─ definitions.py       # Ensambla assets + checks en Definitions
├─ scripts/
│  └─ eda_inicial.py          # (opcional) Descarga/EDA manual para diagnóstico rápido
├─ out/
│  └─ reporte_covid.xlsx      # Salida final (git-ignored)
├─ data/                      # Archivos CSV generados por EDA (git-ignored)
├─ requirements.txt
└─ README.md

+ data/ y out/ están en .gitignore para no versionar datos pesados/derivados.

4. Requisitos
+ Python 3.11
+ requirements.txt incluye (resumen):
+ dagster>=1.6, dagster-webserver>=1.6, pandas>=2.1, requests>=2.31,
+ duckdb>=1.0, pyarrow>=15, openpyxl>=3.1.


5. Ejecución
# 1) Instalar
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2) Variables de entorno (países y fallback)
export PYTHONPATH=src
export PAISES_1="Ecuador"
export PAISES_2="Peru"
export OWID_URL_FALLBACK="https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv"

# 3) Levantar la UI de Dagster
dagster dev -m covid_ec.defs


Abre la UI (por defecto http://127.0.0.1:3000), entra a Assets → Materialize all (o “Open launchpad”) y ejecuta.
La salida quedará en out/reporte_covid.xlsx.


6. Datos
+ Fuente principal: Our World in Data (OWID) – COVID-19 dataset.
+ Fallback: raw de GitHub de OWID (útil cuando el DNS de covid.ourworldindata.org falla).
+ Licencia de datos: consultar OWID (usualmente CC BY). Citar la fuente cuando se usen tablas o gráficos.

7. Salidas y validación
- Excel: out/reporte_covid.xlsx (2 hojas: metrica_incidencia_7d, metrica_factor_crec_7d).
- Metadata en Dagster: cada asset muestra rutas de almacenamiento y logs.
- Checks: si check_entrada_basica marca Failed, revisar:
  + columnas clave vacías o nulas
  + fechas inválidas (muy antiguas/futuras)
  + población <= 0 o duplicados inesperados
  + si falla la descarga principal, verificar que se usó el fallback.
 
8. Troubleshooting
+ Error DNS/descarga OWID
Usa OWID_URL_FALLBACK (ya configurado arriba).
+ No se ve el módulo
Asegúrate de configurar PYTHONPATH=src (o $env:PYTHONPATH="src" en PowerShell). 
+ Excel vacío o incompleto
Verifica que los assets aguas arriba se materializaron con éxito y que los checks están OK.
+ Re-ejecución limpia
Desde la UI: Assets → Materialize all. Puedes inspeccionar “Runs” y “Events” para ver los pasos.
