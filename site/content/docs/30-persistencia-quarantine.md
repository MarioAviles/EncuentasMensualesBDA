# Uso de persistencia y cuarentena

## Persistencia principal
La persistencia se realiza en **SQLite** bajo la carpeta `output/sql/`, asegurando trazabilidad total y almacenamiento histórico de todas las ejecuciones de ingesta.

### Tablas principales
| Tabla | Descripción | Contenido |
|--------|--------------|-----------|
| `raw_encuestas` | Copia directa de las encuestas sin limpiar | Todos los campos originales (`id_respuesta`, `fecha`, `edad`, `area`, `satisfaccion`, `comentario`) |
| `clean_encuestas` | Datos validados y listos para análisis | Campos limpios + metadatos de trazabilidad (`_batch_id`, `_source_file`, `_ingest_ts`) |
| `quarantine_encuestas` | Registros válidos parcialmente pero con errores de dominio | Campos base + `causa` del rechazo |

---

## Motor y estructura
- **Motor:** SQLite (`raw_encuestas.db`)
- **Ubicación:** `output/sql/raw_encuestas.db`
- **Modo:** `append` (acumulativo, sin sobrescritura)
- **Control de duplicados:** si `_batch_id` ya existe, la carga se **aborta** automáticamente
- **Formato alternativo:** se exporta también a Parquet (`output/parquet/`) para análisis posterior

---

## Cuarentena (DLQ)
### Criterios de envío a cuarentena
- `satisfaccion` fuera de rango (valor <1 o >10)
- Registro con edad válida, pero error de dominio en satisfacción

### Estructura
- Columnas:  
  `id_respuesta`, `fecha`, `edad`, `area`, `satisfaccion`, `comentario`, `causa`
- Causa actual: `"Satisfacción fuera de rango (1–10)"`
- Persistencia: tabla `quarantine_encuestas` (SQLite) y Parquet (`quarantine_encuestas_<batch>.parquet`)

### Tratamiento posterior
- Los registros en cuarentena no se eliminan.  
  Se conservan para revisión y posible reintegración futura.
- El proceso de limpieza puede revalidar cuarentenas en una carga posterior.

---

## Esquema de trazabilidad
Cada registro limpio y cuarentenado incluye:
- `_batch_id`: UUID del lote de carga
- `_source_file`: nombre del archivo CSV origen
- `_ingest_ts`: timestamp ISO 8601 de la ingestión

---

## Estrategia de versionado
- Cada ejecución genera un nuevo `batch` independiente.
- Se mantienen históricos en:
  - **SQLite** → datos transaccionales
  - **Parquet** → datasets analíticos
  - **Reportes Markdown y Excel** → control de calidad y evolución

---

## Riesgos y controles
- **Duplicación accidental:** controlado por `_batch_id`
- **Reprocesamiento no intencionado:** aborta si el batch ya está en BD
- **Crecimiento del volumen:** mitigado por exportación periódica a Parquet
- **Fallo de calidad:** registros desviados a cuarentena sin interrumpir el flujo principal
