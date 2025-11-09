# Diseño de ingestión

## Resumen
La ingesta consiste en la **lectura y procesamiento de encuestas de satisfacción simuladas**, generadas mensualmente en formato Excel (para uso humano) y exportadas automáticamente a CSV homogéneo.  
El proceso de ingesta se ejecuta **en modo batch diario**, incorporando los nuevos ficheros generados en `data/drops/` con trazabilidad completa y validaciones automáticas.  
Las garantías mínimas incluyen:
- Detección de duplicados mediante `_batch_id`.
- Validación de tipos y dominio (edad y satisfacción).
- Reprocesamiento seguro e idempotente.

---

## Fuente
- **Origen:** `data/drops/<YYYY-MM-DD>/encuestas.csv`  
  (archivo generado automáticamente desde Excel mensual `data/raw/encuestas_<YYYYMM>.xlsx`)
- **Formato:** CSV (UTF-8)
- **Frecuencia:** Diario (una ingesta por día)
- **Generación:** Script Python ETL (simulación y exportación automática)

---

## Estrategia
- **Modo:** `batch`
- **Incremental:** controlado por `_batch_id` (UUID) y fecha de ingestión (`_ingest_ts`)
- **Particionado:** por fecha (`data/drops/YYYY-MM-DD/`)
- **Lectura:** última carpeta `encuestas.csv` disponible en `data/drops/`

---

## Idempotencia y deduplicación
- **batch_id:** UUID generado por `uuid.uuid4()` en cada ejecución  
- **clave natural:** `id_respuesta`
- **Política:** “último gana por `_ingest_ts`”  
- **Control de duplicidad:** antes de insertar, se valida si `_batch_id` ya existe en la tabla `clean_encuestas` (abortando la carga si está repetido).

---

## Checkpoints y trazabilidad
- **checkpoints/offset:** no aplica (modo batch)
- **trazabilidad:**  
  - `_ingest_ts`: marca temporal ISO 8601 de ingestión  
  - `_source_file`: nombre del archivo origen (`encuestas.csv`)  
  - `_batch_id`: identificador único de ejecución  
- **DLQ/quarantine:**  
  - Ubicación lógica: tabla `quarantine_encuestas` (SQLite)  
  - Motivos:
    - “Satisfacción fuera de rango (1–10)”

---

## SLA
- **Disponibilidad:** datos disponibles el mismo día antes de las 03:00 UTC  
- **Alertas:** mensajes de consola informativos (sin sistema de alertas automatizado por ahora)

---

## Riesgos / Antipatrones
- **Batch con necesidad de segundos:** no aplicable (el proceso es diario y controlado).  
- **Falta de clave natural:** el campo `id_respuesta` actúa como clave natural única por encuesta.  
- **Errores de formato manual (Excel):** mitigados al homogeneizar el formato a CSV automático.
