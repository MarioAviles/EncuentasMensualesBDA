# Proyecto_UT1_RA1_BA · Encuestas mensuales (Excel -> CSV/Parquet)

Este repositorio contiene:

- **project/**: código reproducible (ingesta → clean → oro → reporte Markdown).
- **content/**: web pública con **Quartz 4** (GitHub Pages). El reporte UT1 se publica en `site/content/reportes/`.

## Ejecución rápida

```bash
# 1) Dependencias
pip install -r project/requirements.txt

# 2) Generar datos de ejemplo
python project/ingest/get_data.py

# 3) Pipeline fin-a-fin (ingesta→clean→persistencia→reporte.md)
python project/ingest/run.py

# 4) Copiar el reporte a la web Quartz
python project/tools/copy_report_to_site.py

# 5) (Opcional) Previsualizar la web en local
cd site
npx quartz build --serve   # abre http://localhost:8080
```

## Publicación web (GitHub Pages)

- En **Settings → Pages**, selecciona **Source = GitHub Actions**.
- El workflow `./.github/workflows/deploy-pages.yml` compila `site/` y despliega.
