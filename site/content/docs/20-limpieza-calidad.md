# Reglas de limpieza y calidad

## Tipos y formatos
- `fecha`: ISO (`YYYY-MM-DD`) convertida con `pd.to_datetime(errors='coerce')`
- `edad`: entero entre 18 y 65 (valores fuera o nulos se excluyen)
- `satisfaccion`: entero entre 1 y 10  
  *(valores fuera de rango o "NS/NC" → enviados a cuarentena)*
- `area`: texto limpio, sin tildes ni espacios extra  
- `comentario`: texto normalizado (tildes y caracteres especiales eliminados)

---

## Nulos
- Campos obligatorios: (`fecha`, `edad`, `area`, `satisfaccion`)
- Tratamiento:
  - Filas con `edad` nula → **descartadas**
  - Filas con `satisfaccion` nula → **descartadas**
  - Filas con `satisfaccion` fuera de rango (1–10) → **quarantine** con causa `"Satisfacción fuera de rango (1–10)"`

---

## Rangos y dominios
- `edad`: entre 18 y 65 años  
- `satisfaccion`: entre 1 y 10  
- `area`: pertenece a uno de los valores definidos:  
  `["Atención", "Soporte", "Ventas", "Postventa"]`

---

## Deduplicación
- **Clave natural:** `id_respuesta`
- **Política:** **último gana** por `_ingest_ts`  
  *(si un mismo `id_respuesta` aparece en diferentes batches, se conserva el más reciente)*

---

## Estandarización de texto
- Aplicación de `.strip()` y eliminación de `None`, `NaN`, `null`  
- Normalización de tildes mediante `unicodedata.normalize('NFD')`  
- Sustitución de valores vacíos por espacio `" "` para evitar nulos en texto  
- Asegurar consistencia en `area` y `comentario` (sin acentos ni caracteres especiales)

---

## Trazabilidad
- Cada fila limpia conserva:
  - `_ingest_ts`: marca temporal UTC de la carga  
  - `_source_file`: nombre del archivo de origen (`encuestas.csv`)  
  - `_batch_id`: UUID único por ejecución  
- Las filas en cuarentena se almacenan en la tabla `quarantine_encuestas` junto con la columna `causa`.

---

## QA rápida
- **% de filas a cuarentena:** calculado y registrado en el informe de calidad (`informe_calidad_*.xlsx`)
- **Conteo total:** filas RAW vs limpias vs cuarentena
- **Control de dominio:** validación de satisfacciones fuera de rango (1–10)
- **Exportación validada:** CSV limpio (`encuestas_limpias.csv`) + Parquet y SQLite sincronizados
