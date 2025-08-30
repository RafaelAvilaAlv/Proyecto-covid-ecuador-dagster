from dagster import Definitions
from .assets import (
    leer_datos,
    datos_procesados,
    metrica_incidencia_7d,
    metrica_factor_crec_7d,
    resumen_metricas,        # <-- nuevo
    reporte_excel_covid,
     reporte_resumen_excel,     # <- NUEVO
    casos_vacunados,
    check_entrada_basica,
    check_incidencia_rango,
)

defs = Definitions(
    assets=[
        leer_datos,
        datos_procesados,
        metrica_incidencia_7d,
        metrica_factor_crec_7d,
        resumen_metricas,     # <-- aquí para que esté disponible al Excel
        reporte_excel_covid,
         reporte_resumen_excel,   # <- NUEVO
        casos_vacunados,
    ],
    asset_checks=[check_entrada_basica, check_incidencia_rango],
)
