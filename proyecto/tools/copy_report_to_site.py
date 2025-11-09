from pathlib import Path
import shutil

base = Path(__file__).resolve().parents[1]
src_dir = base / "output" / "reportes"
dst_dir = base.parents[0] / "content" / "reportes"

dst_dir.mkdir(parents=True, exist_ok=True)

for src_file in src_dir.glob("reporte_historico_*.md"):
    dst_file = dst_dir / src_file.name
    shutil.copy2(src_file, dst_file)
    print("Copiado:", dst_file)
