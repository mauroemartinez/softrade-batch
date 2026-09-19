# Tests

Cubren todo lo que **no toca el navegador**: `catalog.json`, `preflight.py`,
`plan_run.py`, `run_state.py` e `inspect_download.py`.

```bash
python -m unittest discover -s tests            # todo
python -m unittest discover -s tests -b         # -b silencia el stdout de los scripts salvo que falle algo
python -m unittest tests.test_preflight -v      # un módulo
```

Sin dependencias nuevas: `pandas` y `openpyxl` ya los pide la skill.

| Archivo | Qué chequea |
|---|---|
| `test_catalog.py` | `catalog.json` parsea, 78 países, los 25 `report_types` canónicos, cada `report` de cada país es conocido, alias resuelven |
| `test_preflight.py` | los veredictos OK / WARN / IMPOSSIBLE de la tabla de `docs/handoff-motor-consultas.md`, con `today` fijo |
| `test_plan_run.py` | combo inválido rechazado, filtro de empresa imposible rechazado, split de 12 meses intacto, `catalog_version` + `preflight` en el manifiesto; bordes de fechas (fin de mes, bisiesto, 12 vs 13 meses); filtros guardados, acumulados y deduplicados |
| `test_check_manifest.py` | `run_state.py check`: report no canónico / país desconocido / `done` sin archivo salen 1; placeholder de fecha permitido |
| `test_inspect_download.py` | registros ≠ filas, truncado sale 3, archivo vacío / HTML de login sale 2; `No disponible` cae a la numeración de `Item`; el `Ordinal` mexicano (`06255386-0001`) se cuenta por pedimento; `--record` escribe `done` / `skipped` / `failed` con los conteos reales |
| `test_run_state.py` | `split` marca al padre y agrega hijos que heredan los filtros, no parte un mes solo ni un job hecho; `next` da pendientes antes que fallidos, imprime los filtros, y el `--json` coincide; filas y operaciones por separado; `reset` limpia los conteos |

Si cambia la lista de `report_types` o un hecho de `references/*.md`, corré
`python tools/build_catalog.py` y volvé a pasar los tests.
