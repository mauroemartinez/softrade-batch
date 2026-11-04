# Tests

Cubren todo lo que **no toca el navegador**: `catalog.json`, `preflight.py`,
`plan_run.py`, `run_state.py`, `inspect_download.py`, `party_check.py`,
`merge_run.py`, `tools/split_run.py`, `tools/save_sample.py` y `tools/build_catalog.py`.

```bash
python -m unittest discover -s tests            # todo
python -m unittest discover -s tests -b         # -b silencia el stdout de los scripts salvo que falle algo
python -m unittest tests.test_preflight -v      # un módulo
```

Necesitan lo mismo que los scripts, listado en [`requirements.txt`](../requirements.txt)
(`pandas`, `openpyxl`, `xlrd`). Desde la raíz del repo:

```bash
pip install -r requirements.txt
```

Sin eso, los tests de `inspect_download.py`, `party_check.py` y `merge_run.py` dan error en vez de pasar.

| Archivo | Qué chequea |
|---|---|
| `test_catalog.py` | `catalog.json` parsea, 78 países, los 25 `report_types` canónicos, cada `report` de cada país es conocido, alias resuelven |
| `test_preflight.py` | los veredictos OK / WARN / IMPOSSIBLE de la tabla de `docs/handoff-motor-consultas.md`, con `today` fijo; fechas mal formadas o invertidas; fecha de relevamiento por entrada (segunda pasada); el aviso de manifiestos de Cargas solo en reportes de importación por empresa, nunca en Salidas, y apagado cuando la nota del catálogo dice "funciona como importador real" (la forma negada no cuenta); CLI: exit 0/1/2, `--json` parseable, catálogo faltante, roto, con otra forma o con una entrada incompleta sale 2 sin traceback |
| `test_plan_run.py` | combo inválido rechazado, filtro de empresa imposible rechazado, split de 12 meses intacto, `catalog_version` + `preflight` en el manifiesto; bordes de fechas (fin de mes, bisiesto, 12 vs 13 meses); filtros guardados, acumulados y deduplicados; re-planificar un período solapado agrega solo los días que faltan (también con jobs de medio mes); filtro de empresa del lado equivocado rechazado; mes, día o fecha inválidos y período invertido rechazados aun con `--skip-preflight`; `--max-months` fuera de 1..12 rechazado; escritura atómica del manifiesto (un fallo a mitad deja el anterior, sin temporales, mismo formato); re-planificar con `download_dir` relativo |
| `test_check_manifest.py` | `run_state.py check`: report no canónico / país desconocido / `done` sin archivo salen 1; placeholder de fecha permitido; jobs solapados y padre con hijos que no está en `split` salen 1, meses contiguos o filtros distintos no |
| `test_inspect_download.py` | registros ≠ filas, truncado sale 3, archivo vacío / HTML de login sale 2; xlsx corrupto sale 2 sin traceback; sin columna de registro el tope se mide por filas; `No disponible` cae a la numeración de `Item`; el `Ordinal` mexicano (`06255386-0001`) se cuenta por pedimento; `--record` escribe `done` / `skipped` / `failed` con los conteos reales, y no toca el manifiesto si falta pandas/openpyxl; `.csv` / `.txt` con coma, punto y coma, tab o pipe, BOM UTF-8, CSV en cp1252, una coma en el encabezado de un archivo con `;` no decide el separador, una empresa que se llama "login" no es una página HTML, extensión no soportada; la `NOTE` de cerca del tope (más del 90%) por registros o por filas |
| `test_run_state.py` | `split` marca al padre y agrega hijos que heredan los filtros, no parte un mes solo ni un job hecho, ni un job ya partido; `next` da pendientes antes que fallidos, no entrega un padre con hijos, imprime los filtros, y el `--json` coincide; filas y operaciones por separado; `reset` limpia los conteos y se niega sobre un padre partido; `status --json` no escribe; errores claros (índice fuera de rango, `--job` faltante, manifiesto faltante o corrupto, fecha imposible); un `download_dir` relativo se resuelve contra RUN_DIR y no contra el cwd; escritura atómica en `run_state.py` y en `inspect_download --record` |
| `test_split_run.py` | `tools/split_run.py` no pisa sub-manifiestos con avance salvo `--force`; volver a correrlo con todo pendiente está permitido; el `download_dir` de los sub-manifiestos es relativo (`downloads`) y resuelve a la carpeta de cada sub-corrida; los avisos de `preflight` del maestro pasan a los sub-manifiestos (lista vacía si no hay); una escritura fallida deja el sub-manifiesto anterior |
| `test_party_check.py` | `party_check.py`: TO ORDER, marcas de forwarders y navieras, palabras logísticas como bucket aparte, una empresa común sigue siendo empresa; marcas ambiguas (EVERGREEN, AGILITY, MSC, ZIM) solo cuentan como logística con contexto naviero; porcentajes por columna, `Operador` de zona franca, nombres de columna sin importar mayúsculas, tildes o espacios; CLI: reporte de texto, `--json`, `--no-names` oculta todo nombre, archivo sin columnas de partes, archivo faltante |
| `test_merge_run.py` | `merge_run.py`: une los hijos y deja afuera al padre partido aunque esté `done`; una hoja por país/reporte; csv de entrada y de salida, y csv con más de un grupo rechazado; se niega con jobs pendientes o fallidos salvo `--allow-partial`; columnas distintas rechazadas (el orden solo no cuenta); archivo faltante, fuera del `download_dir` o HTML rechazado; números y fechas quedan con su tipo y los códigos con sus ceros; quita duplicados solo entre tramos solapados; marca tramos vacíos, chicos, mayoría vacía o con filas distintas a las del manifiesto (exit 3), y todo vacío es rechazo; resumen `--json` |
| `test_save_sample.py` | `tools/save_sample.py`: mueve la descarga y escribe `info.md`; sin descarga reciente sale con error; una segunda muestra va a `info-2.md` sin pisar la anterior; mismo nombre de archivo rechazado sin `--force`; `--force` reemplaza el archivo y su propio info, también saltando un hueco en la numeración |
| `test_build_catalog.py` | `tools/build_catalog.py`: `--help` no escribe nada; sin argumentos y con `--out`; `--check` pasa sobre el `catalog.json` del repo (el control de deriva), detecta un archivo viejo sin reescribirlo, ignora finales de línea, falla limpio con un archivo faltante o un JSON que no es un objeto; `build()` determinístico; `meta.catalog_version` arranca con la fecha de relevamiento más nueva y cambia con cualquier entrada; `_catalog.version()` cae a `meta.captured` |

Si cambia la lista de `report_types` o un hecho de `references/*.md`, pasalo a
`tools/build_catalog.py`, corré `python tools/build_catalog.py` desde la raíz del
repo y volvé a pasar los tests. Es un paso de mantenimiento del repo: la skill
instalada no trae `tools/`.

`python tools/build_catalog.py --check` (desde la raíz del repo) es el control de
deriva: arma el catálogo en memoria, lo compara con `catalog.json` sin escribir
nada y sale `1` con un resumen de diferencias si alguien editó el builder sin
regenerar, o `0` ("al día", con la `catalog_version`). `test_build_catalog.py` lo
corre sobre el archivo del repo. `--out PATH` escribe en otra ruta (con `--check`,
compara contra esa).
