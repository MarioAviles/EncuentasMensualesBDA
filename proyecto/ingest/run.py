import pandas as pd, numpy as np, sqlite3, unicodedata
from pathlib import Path
from datetime import datetime, timezone
import uuid

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
csv, batch, ts = csvs[-1], str(uuid.uuid4()), datetime.now().isoformat()

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

tablas = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", con)
if "clean_encuestas" in tablas["name"].values:
    batches = pd.read_sql("SELECT DISTINCT _batch_id FROM clean_encuestas", con)
    if batch in batches["_batch_id"].values:
        print(f"⛔ Batch {batch} ya procesado. Abortando inserción.")
        con.close(); exit()

# RAW: sin trazabilidad
df[COLS].to_sql("raw_encuestas", con, if_exists="append", index=False)
# CLEAN: con trazabilidad
dfc = df_clean.assign(_batch_id=batch, _source_file=csv.name, _ingest_ts=ts)
dfc.to_sql("clean_encuestas", con, if_exists="append", index=False)
# QUARANTINE: con causa
if not df_quar.empty:
    df_quar[COLS+['causa']].to_sql("quarantine_encuestas", con, if_exists="append", index=False)
con.commit(); con.close()
print("✅ SQLite actualizado")

# Convertir satisfaccion a string antes de exportar a Parquet (evita ArrowTypeError)
dfc['satisfaccion'] = dfc['satisfaccion'].astype(str)
if not df_quar.empty:
    df_quar['satisfaccion'] = df_quar['satisfaccion'].astype(str)

dfc.to_parquet(PARQ / f"clean_encuestas_{batch}.parquet", index=False)
if not df_quar.empty:
    df_quar.to_parquet(PARQ / f"quarantine_encuestas_{batch}.parquet", index=False)

print("✅ Exportación Parquet completada")

# ================================================================
# 4️⃣ REPORTE HISTÓRICO
# ================================================================
print("\n===== [4] REPORTE =====")
dfs = [pd.read_parquet(f) for f in sorted(PARQ.glob("clean_encuestas_*.parquet"))]
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
