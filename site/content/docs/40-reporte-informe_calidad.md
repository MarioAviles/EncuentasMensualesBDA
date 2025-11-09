# Diseño de reporte e informe de calidad

## Reporte histórico (`reporte_historico_*.md`)

### Descripción
El sistema genera automáticamente un **reporte histórico consolidado** con todos los lotes procesados (`clean_encuestas_*.parquet`).  
Este reporte resume la **distribución de satisfacción por área**, la **evolución temporal** y las **métricas globales** de calidad y volumen de datos.

### Ubicación
`output/reportes/reporte_historico_<batch_id>.md`

### Contenido
- **Encabezado informativo**
  - Periodo cubierto (`fecha mínima → fecha máxima`)
  - Fecha de generación (`_ingest_ts` en UTC)
  - Total de encuestas procesadas
- **Distribución de satisfacción (1–10)**
  - Tabla porcentual por `area`
  - Cálculo: frecuencia relativa de cada puntuación sobre el total del área
- **Evolución mensual**
  - Promedio de satisfacción por `mes` y `area`
  - Agrupación con `Period('M')` para consolidar las fechas

### Ejemplo de secciones en el Markdown

# Reporte · Encuestas de Satisfacción
**Periodo:** 2025-11-01 → 2025-11-30  
**Generado:** 2025-11-09T12:00:00Z  
**Total encuestas:** 5,000

## Distribución 1–10 (%)
| area      | 1 | 2 | 3 | ... | 10 |
|------------|---|---|---|-----|----|
| Atención   | … | … | … |     |    |
| Soporte    | … | … | … |     |    |

## Evolución mensual (promedio)
| mes      | Atención | Soporte | Ventas | Postventa |
|-----------|-----------|----------|---------|------------|
| 2025-11  | 7.8       | 8.2      | 7.5     | 8.0        |
