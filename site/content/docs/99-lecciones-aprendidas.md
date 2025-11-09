# Lecciones aprendidas

## Qué salió bien
- **Automatización completa del flujo ETL**: desde la generación de encuestas hasta el reporte final, sin intervención manual.  
- **Estructura modular y clara**: separación lógica por etapas (ingesta, limpieza, persistencia, reporte).  
- **Control de calidad integrado**: cuarentena automática de registros fuera de rango y trazabilidad completa por `_batch_id`.  
- **Reproducibilidad**: ejecución idempotente que evita duplicados y garantiza consistencia entre SQLite, CSV y Parquet.  
- **Documentación técnica estructurada** en formato Markdown, fácilmente integrable en Obsidian.  
- **Simulación de datos realista**: uso de distribuciones y probabilidades que reproducen comportamientos cercanos a un entorno real de encuestas.

---

## Qué mejorar
- **Gestión de logs**: implementar un sistema de logging estructurado (`logging` de Python) en lugar de `print()`.  
- **Alertas automáticas**: enviar notificaciones o correos si un lote contiene demasiadas filas en cuarentena.  
- **Validaciones dinámicas**: parametrizar los rangos (`edad`, `satisfaccion`) en un fichero de configuración (`YAML` o `.env`).  
- **Escalabilidad de almacenamiento**: migrar la persistencia de SQLite a PostgreSQL o DuckDB para manejar mayores volúmenes.  
- **Visualización**: generar gráficos automáticos (p. ej. evolución de satisfacción) a partir del reporte Parquet.  
- **Pipeline automatizado**: orquestar el flujo con `Airflow`, `Prefect` o `Dagster` para ejecución programada y controlada.

---

## Siguientes pasos
- [ ] Añadir un sistema de **validaciones configurables por metadatos**.  
- [ ] Implementar **logs de ejecución persistentes** (nivel INFO/ERROR).  
- [ ] Crear un **dashboard de calidad de datos** usando Streamlit o Power BI.  
- [ ] Integrar **alertas vía Telegram o correo** al detectar errores o anomalías.  
- [ ] Evaluar la integración con **BigQuery o Snowflake** para análisis a gran escala.  
- [ ] Documentar el pipeline con un **diagrama de flujo ETL** en Mermaid o Draw.io.

---

## Apéndice (evidencias)
- **Capturas de `Actions` (build Quartz):**  
  Evidencias visuales de la ejecución automática de los scripts y generación de reportes.

- **Fragmentos de log con errores resueltos:**  
  Ejemplo de errores detectados durante desarrollo y su corrección:

- **Evidencias de ejecución correcta:**  
- `encuestas_limpias.csv` generado con 0 duplicados  
- `informe_calidad_<batch>.xlsx` con validaciones correctas  
- `reporte_historico_<batch>.md` mostrando evolución mensual consolidada
