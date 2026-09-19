# Receta de medicion de columnas

Usar esta secuencia para completar un job de la corrida de cobertura.

La corrida esta partida en dos sub-corridas, `corrida-catalogo/split-claude/` y `corrida-catalogo/split-chatgpt/`, cada una con su manifiesto y su `downloads/`. El trabajo se avanza y se registra en el sub-manifiesto (`SUB` abajo es uno de esos dos directorios). `corrida-catalogo/manifest.json` es el maestro de 112 jobs: queda como referencia, no se edita durante la corrida, y los resultados se copian ahi a mano al final. `tools/split_run.py` se niega a pisar un sub-manifiesto que ya tiene avance (salvo `--force`), asi que re-partir no borra lo hecho.

1. Ver el proximo trabajo:

```bash
python skills/softrade-batch/scripts/run_state.py next corrida-catalogo/SUB
```

2. Abrir Softrade, elegir el pais y el reporte del job, usar `latest` como el ultimo mes cerrado que el formulario muestre cargado y aplicar el filtro chico del job (`8544`, o `854442` en CN/VN).

3. Descargar el Excel y renombrarlo con esta forma:

```text
<pais>_<report>_<yyyymm>_<partida>.xlsx
```

4. Medir y registrar contra el sub-manifiesto:

```bash
python skills/softrade-batch/scripts/inspect_download.py corrida-catalogo/SUB/downloads/ARCHIVO.xlsx --record corrida-catalogo/SUB --job N
```

5. Volcar la salida:

- Las lineas `rows`, `records`, `columns` y la lista completa de columnas van al `columns-*.md` que corresponda.
- Los campos clave (FOB, CIF, empresa local, contraparte, Incoterm, Marca) van a `skills/softrade-batch/references/fields-matrix.md`.
- Si el reporte tiene una trampa estructural nueva, documentarla en el archivo de referencia de su familia; si cambia el flujo del sitio, recien ahi tocar `site-flow.md`.

6. Tildar en `skills/softrade-batch/references/coverage.md` la casilla del mismo job. La casilla y el job del sub-manifiesto tienen que coincidir (el indice del job no es el mismo que en el maestro). Antes de retomar, o despues de editar un manifiesto a mano, `run_state.py check corrida-catalogo/SUB` valida que siga sano.
