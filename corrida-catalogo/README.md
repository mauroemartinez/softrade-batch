# Corrida catalogo

Esta carpeta contiene el manifiesto de medicion de columnas. `manifest.json` es el maestro de 112 jobs y queda como referencia: el trabajo se registra en `split-claude/` y `split-chatgpt/` (ver `docs/receta-medicion.md`), y los resultados se copian al maestro a mano al final.

## Convencion de fechas

`latest` significa: usar el ultimo mes cerrado que el formulario de Softrade muestre como cargado. La ejecucion en vivo lo resuelve al abrir cada reporte.

Cada job usa un filtro chico de partida para medir columnas sin descargar volumen innecesario: `8544` en general y `854442` para China/Vietnam, donde conviene entrar con 6 digitos.

Los Excel descargados van en el `downloads/` de cada sub-corrida (`split-*/downloads/`) y no se versionan.

## Segunda pasada del 2026-09-18, fuera de estos manifiestos

Hubo una segunda pasada de relevamiento que no pasó por `manifest.json` ni por los sub-manifiestos: sus 8 muestras quedaron en `runs/cobertura-2026-09-18/downloads/` (no versionado, sin manifiesto propio). Sus resultados están en `catalog.json` (entradas con `"surveyed": "2026-09-18"`), en `fields-matrix.md` y en las casillas de `coverage.md`, pero los jobs equivalentes del maestro (BO/CL/CO export, EC historicoImport/cargasIngresos, BR cargasMaritimasSalidas/cargasHistoricoIngresos, entre otros) siguen en `pending`. Al copiar resultados al maestro, tenerlo en cuenta para no volver a medirlos sin querer.

La fecha en el nombre que pone Softrade (`detalle_{CC}{report}_{Y}-{M}-{D}-{HMMSS}.xlsx`) no es una fecha de calendario: el mes es el de JavaScript, base 0 (`8` = septiembre), `D` parece ser el dia de la semana (0 = domingo) y la hora no lleva ceros. Para fechar una muestra, usar la fecha de modificacion del archivo.
