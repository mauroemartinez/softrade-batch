# Receta de medicion de columnas

Usar esta secuencia para completar un job de `corrida-catalogo/manifest.json`.

1. Ver el proximo trabajo:

```bash
python skills/softrade-batch/scripts/run_state.py next corrida-catalogo
```

2. Abrir Softrade, elegir el pais y el reporte del job, usar `latest` como el ultimo mes cerrado que el formulario muestre cargado y aplicar el filtro chico del job (`8544`, o `854442` en CN/VN).

3. Descargar el Excel y renombrarlo con esta forma:

```text
<pais>_<report>_<yyyymm>_<partida>.xlsx
```

4. Medir y registrar contra el manifest:

```bash
python skills/softrade-batch/scripts/inspect_download.py corrida-catalogo/downloads/ARCHIVO.xlsx --record corrida-catalogo --job N
```

5. Volcar la salida:

- Las lineas `rows`, `records`, `columns` y la lista completa de columnas van al `columns-*.md` que corresponda.
- Los campos clave (FOB, CIF, empresa local, contraparte, Incoterm, Marca) van a `skills/softrade-batch/references/fields-matrix.md`.
- Si el reporte tiene una trampa estructural nueva, documentarla en el archivo de referencia de su familia; si cambia el flujo del sitio, recien ahi tocar `site-flow.md`.

6. Tildar en `skills/softrade-batch/references/coverage.md` la casilla del mismo job. La casilla, el indice del manifest y el `next` tienen que coincidir.
