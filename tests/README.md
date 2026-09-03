# Tests del motor de consultas (Parte 1)

Cubren la parte que **no toca el navegador**: `catalog.json`, `preflight.py`,
la validación de `plan_run.py`, y el conteo de `inspect_download.py`.

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
| `test_plan_run.py` | combo inválido rechazado, filtro de empresa imposible rechazado, split de 12 meses intacto, `catalog_version` + `preflight` en el manifiesto |
| `test_check_manifest.py` | `run_state.py check`: report no canónico / país desconocido / `done` sin archivo salen 1; placeholder de fecha permitido |
| `test_inspect_download.py` | registros ≠ filas, truncado sale 3, archivo vacío / HTML de login sale 2 |

Si cambia la lista de `report_types` o un hecho de `references/*.md`, corré
`python tools/build_catalog.py` y volvé a pasar los tests.
