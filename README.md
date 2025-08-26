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


2) Arquitectura (Dagster)

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
