import pandas as pd, numpy as np, sqlite3, unicodedata
from pathlib import Path
from datetime import datetime, timezone
import uuid
import hashlib, os

# ================================================================
# CONFIGURACIÓN GLOBAL
# ================================================================
BASE = Path(__file__).resolve().parent.parent
DATA, OUT = BASE / "data", BASE / "output"
DROPS, SQL, PARQ, REP = DATA / "drops", OUT / "sql", OUT / "parquet", OUT / "reportes"
for d in [SQL, PARQ, REP, DROPS]: d.mkdir(parents=True, exist_ok=True)
COLS = ['id_respuesta', 'fecha', 'edad', 'area', 'satisfaccion', 'comentario']

# ================================================================
# 1️⃣ INGESTA
# ================================================================
print("\n===== [1] INGESTA =====")
csvs = sorted(DROPS.glob("*/encuestas.csv"))
if not csvs: raise FileNotFoundError("⚠️ No se encontró 'encuestas.csv' en data/drops/")
csv = csvs[-1]
hash_input = f"{csv.name}_{os.path.getsize(csv)}_{datetime.timestamp(datetime.now())}"
batch = hashlib.md5(hash_input.encode()).hexdigest()
ts = datetime.now().isoformat()

df = pd.read_csv(csv, dtype=str)
for c in COLS: df[c] = df.get(c, np.nan)
df = df[COLS]
df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
df['edad'] = pd.to_numeric(df['edad'], errors='coerce')
df['satisfaccion'] = pd.to_numeric(df['satisfaccion'].replace(["NS/NC"], np.nan), errors='coerce')

print(f"✅ Ingesta completada: {len(df):,} filas")

# ================================================================
# 2️⃣ LIMPIEZA Y CUARENTENA
# ================================================================
print("\n===== [2] LIMPIEZA =====")

def limpiar(s):
    if pd.isna(s) or str(s).strip().lower() in ["", "nan", "none", "null"]:
        return " "
    s = ''.join(c for c in unicodedata.normalize('NFD', str(s).strip())
                if unicodedata.category(c) != 'Mn')
    return s or " "

# --- Normalización de texto ---
df['area'] = df['area'].apply(limpiar)
df['comentario'] = df['comentario'].apply(limpiar)

# --- Conversión de tipos ---
df['satisfaccion'] = pd.to_numeric(df['satisfaccion'], errors='coerce')
df['edad'] = pd.to_numeric(df['edad'], errors='coerce')

# --- Filtrar edad válida ---
df_valid_age = df.dropna(subset=['edad']).copy()

# --- Clasificación ---
mask_valid_satis = df_valid_age['satisfaccion'].between(1, 10, inclusive="both")

# Limpios
df_clean = df_valid_age[mask_valid_satis].copy()

# Cuarentena: edad válida + satisfacción fuera de rango (pero no nula)
mask_quar = df_valid_age['satisfaccion'].notna() & ~mask_valid_satis
df_quar = df_valid_age[mask_quar].copy()
df_quar['causa'] = "Satisfacción fuera de rango (1–10)"

# Descartadas: satisfacción nula (no van a cuarentena)
df_descartadas = df_valid_age[df_valid_age['satisfaccion'].isna()].copy()

# --- Reconversión de tipos ---
for dfx in [df_clean, df_quar]:
    dfx['edad'] = dfx['edad'].astype('Int64')
    dfx['satisfaccion'] = dfx['satisfaccion'].astype('Int64')

# --- Exportar CSV limpio ---
clean_csv = csv.parent / "encuestas_limpias.csv"
df_clean.to_csv(clean_csv, index=False, encoding="utf-8", na_rep=" ", quoting=1)
print(f"✅ Limpios: {len(df_clean):,} | ⚠️ Cuarentena: {len(df_quar):,} | 🗑️ Descartadas (satisf. nula): {len(df_descartadas):,}")
print(f"📁 CSV limpio: {clean_csv}")

# ================================================================
# 3️⃣ PERSISTENCIA
# ================================================================
print("\n===== [3] PERSISTENCIA =====")
con = sqlite3.connect(SQL / "raw_encuestas.db")

# Crear tablas si no existen
con.execute("""
    CREATE TABLE IF NOT EXISTS raw_encuestas (
        id_respuesta TEXT PRIMARY KEY,
        fecha TEXT, edad INTEGER, area TEXT, satisfaccion INTEGER, comentario TEXT
    )
""")
con.execute("""
    CREATE TABLE IF NOT EXISTS clean_encuestas (
        id_respuesta TEXT PRIMARY KEY,
        fecha TEXT, edad INTEGER, area TEXT, satisfaccion INTEGER, comentario TEXT,
        _batch_id TEXT, _source_file TEXT, _ingest_ts TEXT
    )
""")
con.execute("""
    CREATE TABLE IF NOT EXISTS quarantine_encuestas (
        id_respuesta TEXT PRIMARY KEY,
        fecha TEXT, edad INTEGER, area TEXT, satisfaccion INTEGER, comentario TEXT, causa TEXT
    )
""")
con.commit()

# Obtener IDs ya existentes en la BD
ids_bd_raw = set(pd.read_sql("SELECT id_respuesta FROM raw_encuestas", con)['id_respuesta'].values) if "raw_encuestas" in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() else set()
ids_bd_clean = set(pd.read_sql("SELECT id_respuesta FROM clean_encuestas", con)['id_respuesta'].values) if "clean_encuestas" in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() else set()
ids_bd_quar = set(pd.read_sql("SELECT id_respuesta FROM quarantine_encuestas", con)['id_respuesta'].values) if "quarantine_encuestas" in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() else set()

# Filtrar DataFrames: solo registros que NO están en la BD
df_new = df[~df['id_respuesta'].isin(ids_bd_raw)].drop_duplicates(subset=['id_respuesta'], keep='last')
df_clean_new = df_clean[~df_clean['id_respuesta'].isin(ids_bd_clean)].drop_duplicates(subset=['id_respuesta'], keep='last')
df_quar_new = df_quar[~df_quar['id_respuesta'].isin(ids_bd_quar)].drop_duplicates(subset=['id_respuesta'], keep='last')

# Reportar duplicados encontrados
dup_raw = len(df) - len(df_new)
dup_clean = len(df_clean) - len(df_clean_new)
dup_quar = len(df_quar) - len(df_quar_new)

if dup_raw > 0 or dup_clean > 0 or dup_quar > 0:
    print(f"⚠️ Duplicados encontrados en BD: {dup_raw} (raw) | {dup_clean} (clean) | {dup_quar} (quar)")

# Insertar solo registros nuevos (convertir tipos a compatibles con SQLite)
if not df_new.empty:
    df_new_copy = df_new.copy()
    df_new_copy['fecha'] = df_new_copy['fecha'].astype(str)
    df_new_copy['edad'] = df_new_copy['edad'].astype('Int64').fillna(0).astype(int)
    df_new_copy['satisfaccion'] = df_new_copy['satisfaccion'].astype('Int64').fillna(0).astype(int)
    for _, row in df_new_copy[COLS].iterrows():
        placeholders = ','.join(['?' for _ in COLS])
        try:
            con.execute(f"INSERT INTO raw_encuestas ({','.join(COLS)}) VALUES ({placeholders})", tuple(row))
        except sqlite3.IntegrityError:
            pass

if not df_clean_new.empty:
    df_clean_copy = df_clean_new.copy()
    df_clean_copy['fecha'] = df_clean_copy['fecha'].astype(str)
    df_clean_copy['edad'] = df_clean_copy['edad'].astype('Int64').fillna(0).astype(int)
    df_clean_copy['satisfaccion'] = df_clean_copy['satisfaccion'].astype('Int64').fillna(0).astype(int)
    dfc_new = df_clean_copy.assign(_batch_id=batch, _source_file=csv.name, _ingest_ts=ts)
    cols_clean = list(COLS) + ['_batch_id', '_source_file', '_ingest_ts']
    for _, row in dfc_new.iterrows():
        placeholders = ','.join(['?' for _ in cols_clean])
        try:
            con.execute(f"INSERT INTO clean_encuestas ({','.join(cols_clean)}) VALUES ({placeholders})", tuple(row))
        except sqlite3.IntegrityError:
            pass

if not df_quar_new.empty:
    df_quar_copy = df_quar_new.copy()
    df_quar_copy['fecha'] = df_quar_copy['fecha'].astype(str)
    df_quar_copy['edad'] = df_quar_copy['edad'].astype('Int64').fillna(0).astype(int)
    df_quar_copy['satisfaccion'] = df_quar_copy['satisfaccion'].astype('Int64').fillna(0).astype(int)
    cols_quar = list(COLS) + ['causa']
    for _, row in df_quar_copy[cols_quar].iterrows():
        placeholders = ','.join(['?' for _ in cols_quar])
        try:
            con.execute(f"INSERT INTO quarantine_encuestas ({','.join(cols_quar)}) VALUES ({placeholders})", tuple(row))
        except sqlite3.IntegrityError:
            pass

con.commit()
con.close()
print(f"✅ SQLite actualizado: {len(df_new):,} (raw) + {len(df_clean_new):,} (clean) + {len(df_quar_new):,} (quar) registros insertados")

# Convertir satisfaccion a string antes de exportar a Parquet (evita ArrowTypeError)
if not df_clean_new.empty:
    df_clean_copy['satisfaccion'] = df_clean_copy['satisfaccion'].astype(str)
    dfc_for_parquet = df_clean_copy.assign(_batch_id=batch, _source_file=csv.name, _ingest_ts=ts)
    dfc_for_parquet.to_parquet(PARQ / "clean_encuestas.parquet", index=False)
    
if not df_quar_new.empty:
    df_quar_copy['satisfaccion'] = df_quar_copy['satisfaccion'].astype(str)
    df_quar_copy.to_parquet(PARQ / "quarantine_encuestas.parquet", index=False)

print("✅ Exportación Parquet completada")

# ================================================================
# 4️⃣ REPORTE HISTÓRICO
# ================================================================
print("\n===== [4] REPORTE =====")
dfs = [pd.read_parquet(f) for f in sorted(PARQ.glob("clean_encuestas.parquet"))]
allc = pd.concat(dfs, ignore_index=True)
allc['fecha'] = pd.to_datetime(allc['fecha'], errors='coerce')
allc['mes'] = allc['fecha'].dt.to_period('M')

# 👇 Convertir satisfaccion a numérico solo para el reporte
allc['satisfaccion'] = pd.to_numeric(allc['satisfaccion'], errors='coerce')

dist = (allc.groupby(['area','satisfaccion']).size()
        .groupby(level=0).apply(lambda x: 100*x/x.sum())
        .unstack(fill_value=0).round(2))
evol = allc.groupby(['mes','area'])['satisfaccion'].mean().unstack(fill_value=0).round(2)

txt = (
    f"# Reporte · Encuestas de Satisfacción\n"
    f"**Periodo:** {allc['fecha'].min():%Y-%m-%d} → {allc['fecha'].max():%Y-%m-%d}\n"
    f"**Generado:** {datetime.now(timezone.utc).isoformat()}\n\n"
    f"**Total encuestas:** {len(allc):,}\n\n"
    "## Distribución 1–10 (%)\n" + dist.to_markdown() +
    "\n\n## Evolución mensual (promedio)\n" + evol.to_markdown()
)
(REP / f"reporte_historico_{batch}.md").write_text(txt, encoding="utf-8")
print("✅ Reporte generado")

# ================================================================
# 5️⃣ INFORME DE CALIDAD
# ================================================================
print("\n===== [5] INFORME DE CALIDAD =====")
nulos = df.isna().sum(); pct = (df.isna().mean()*100).round(2)
info = pd.DataFrame({"Campo":df.columns, "Nulos":nulos, "% Nulos":pct})
fuera = ((pd.to_numeric(df['satisfaccion'], errors='coerce')<1)|
         (pd.to_numeric(df['satisfaccion'], errors='coerce')>10)|
         (pd.to_numeric(df['satisfaccion'], errors='coerce').isna())).sum()
info.loc[info["Campo"]=="satisfaccion", ["Fuera de dominio (1–10)","% Fuera dominio"]] = [fuera, round(fuera/len(df)*100,2)]

res = pd.DataFrame({"Métrica":["Filas totales (raw)","Filas limpias","Filas en cuarentena"],
                    "Valor":[len(df), len(df_clean), len(df_quar)]})
with pd.ExcelWriter(REP / f"informe_calidad_{batch}.xlsx", engine="openpyxl") as w:
    info.to_excel(w, index=False, sheet_name="Errores_por_campo")
    res.to_excel(w, index=False, sheet_name="Resumen")
print("✅ Informe de calidad generado\n==== FIN DE PROCESO ETL ====")
