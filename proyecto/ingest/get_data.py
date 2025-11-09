import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

# ==========================================================
# ETAPA 1 + 2: Generación simulada de encuestas + INSUMO CSV
# ==========================================================

# Configuración básica
np.random.seed(datetime.now().month)  # genera distinto cada mes
N = 5_000  # número de datos a generar

# Configuración de rutas
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
DROPS_DIR = BASE_DIR / "data" / "drops"
RAW_DIR.mkdir(parents=True, exist_ok=True)
DROPS_DIR.mkdir(parents=True, exist_ok=True)

# Generar fechas dentro del mes actual
ahora = datetime.now()
inicio_mes = datetime(ahora.year, ahora.month, 1)
fin_mes = pd.Timestamp(inicio_mes) + pd.offsets.MonthEnd(1)
fechas = pd.date_range(inicio_mes, fin_mes, freq="D")

# Datos simulados
areas = ['Atención', 'Soporte', 'Ventas', 'Postventa']
comentarios = ["Muy bien", "Excelente", "Rápido", "Podría mejorar", "Mal servicio"] + [""] * 5

# Crear DataFrame
df = pd.DataFrame({
    'id_respuesta': [f'R{str(i).zfill(5)}' for i in range(1, N + 1)],
    'fecha': np.random.choice(fechas, size=N),
    'edad': np.random.choice(
        np.append(np.arange(18, 66), [np.nan]),
        size=N,
        p=[*[0.01]*48, 0.52]  # ~25% nulos
    ),
    'area': np.random.choice(areas, size=N, p=[0.4, 0.3, 0.2, 0.1]),
    'satisfaccion': np.random.choice(
        np.append(np.arange(1, 13), ["NS/NC"]),  # valores 1–12 + NaN
        size=N,
        p=[0.07, 0.08, 0.09, 0.1, 0.12,
           0.13, 0.1, 0.09, 0.08, 0.06, 0.01, 0.02, 0.05]
    ),
    'comentario': np.random.choice(comentarios, size=N)
})

# ==========================================================
# GUARDAR INSUMO (EXCEL HUMANO + CSV HOMOGÉNEO)
# ==========================================================

# Guardar Excel mensual
mes_actual = ahora.strftime("%Y%m")
excel_path = RAW_DIR / f"encuestas_{mes_actual}.xlsx"
df.to_excel(excel_path, index=False, engine='openpyxl')

# Guardar CSV homogéneo
hoy = ahora.strftime("%Y-%m-%d")
drop_dir = DROPS_DIR / hoy
drop_dir.mkdir(parents=True, exist_ok=True)

csv_path = drop_dir / "encuestas.csv"
df.to_csv(csv_path, index=False, encoding="utf-8")

# ==========================================================
# INFORME DE CONTROL
# ==========================================================

print(f"\n✅ Archivos generados correctamente:")
print(f"   - Excel (insumo humano): {excel_path}")
print(f"   - CSV homogéneo: {csv_path}")

print(f"\n[INFO] Registros totales: {len(df):,}")
print(f"[INFO] Nulos en edad: {df['edad'].isna().sum():,}  ({df['edad'].isna().mean()*100:.2f}%)")
print(f"[INFO] Nulos en satisfacción: {df['satisfaccion'].isna().sum():,}  ({df['satisfaccion'].isna().mean()*100:.2f}%)")
print("\nPrimeras 5 filas:")
print(df.head())
print("\nEstructura del DataFrame:")
print(df.info())
