# Spec: el "motor de consultas" de softrade-batch (Parte 1)

Spec y worklist de la **Parte 1**, que construye Claude Code: convertir un pedido en
un plan validado **sin abrir el navegador**. La Parte 2 (cobertura, también
browser-free) va por separado a ChatGPT — ver `docs/prompt-chatgpt-cobertura.md`.
La ejecución en vivo contra Softrade es una tercera etapa, con el login del usuario.

La costura entre Parte 1 y Parte 2 es la **lista canónica de `report_types`** de
este documento: mientras las dos la respeten, no se pisan.

---

## De qué se trata el proyecto

`softrade-batch` es una skill de Claude Code. El usuario pide en castellano
("necesito las impo de mi empresa MI EMPRESA S.A. de este año") y la skill:

1. resuelve empresa / país / reporte / rango de fechas,
2. arma un `manifest.json` en disco (fuente de verdad, sobrevive a que se corte el chat),
3. maneja el Chrome logueado del usuario para bajar los Excel de `app.softrade.info`,
4. cuenta filas y registros de cada archivo y detecta el corte silencioso.

Ya funciona el núcleo. Lo que falta es hacerlo **rápido y confiable cuando quien
pide es una IA**: hoy, para saber si una consulta es siquiera posible, hay que leer
4 archivos markdown de ~600 líneas. Eso tiene que ser una llamada determinística.

### Las dos reglas duras de Softrade

| Límite | Qué acota | Si te pasás |
|---|---|---|
| **12 meses** por query | el largo del período | Softrade **no te deja buscar**. `plan_run.py` ya parte cualquier rango en tramos de ≤12 meses. |
| **30.000 registros** por query | el volumen del resultado | Softrade busca igual y **te devuelve el Excel cortado sin avisar en el archivo**. Ojo: son **registros** (declaraciones aduaneras), no filas. Un archivo puede tener 53.000 filas y estar completo. `inspect_download.py` lo detecta contando `Identificador` distintos. |

Estas dos reglas ya están implementadas. La Parte 1 no las reimplementa: las
**valida antes** de que se dispare una corrida imposible.

---

## El corte del trabajo

| | **Parte 1 — motor de consultas** (Claude Code) | **Parte 2 — cobertura** (ChatGPT) | **Parte 3 — ejecución** (Claude + login) |
|---|---|---|---|
| Qué es | Convertir un pedido en un plan validado, sin abrir el navegador | Scaffolding de la capa 3: reorganizar el manifiesto, esqueletos de `columns-*.md`, expandir matriz y checklist, receta de medición | Correr las sesiones reales de Softrade y llenar los huecos que dejó la Parte 2 |
| Necesita navegador | No | No | Sí |
| Entregables | `catalog.json`, `preflight.py`, validación en `plan_run.py`, `next --json`, tests | `corrida-catalogo/manifest.json` v2, `columns-cargas.md`, `columns-world.md`, `columns-otras-familias.md`, `fields-matrix.md` expandida, `coverage.md` alineado, `docs/receta-medicion.md` | mediciones → `columns-*.md`, `fields-matrix.md`, `coverage.md`, `catalog.json` |

**La costura entre las partes es la lista canónica de `report_types` de abajo.**
El prompt completo de la Parte 2 está en `docs/prompt-chatgpt-cobertura.md`.

---

## Parte 1: alcance detallado

Trabajás dentro de `skills/softrade-batch/`. **No toques** `references/site-flow.md`
ni `references/cargas.md` ni nada sobre cómo se maneja el navegador.
Los markdown de `references/` son **fuente**, no los reescribas; su contenido se
destila a `catalog.json`.

### Entregable A — `references/catalog.json`

La fuente de verdad legible por máquina. Hoy ese conocimiento está disperso en
`references/catalog.md` (qué reportes existen), `entities-latam.md` y
`entities-world.md` (quién nombra empresas, hasta qué fecha llega la data) y
`fields-matrix.md` (columnas medidas, vitalidad). Hay que consolidarlo.

#### Esquema

```jsonc
{
  "meta": {
    "captured": "2026-09-02",              // fecha del relevamiento de las tablas fuente
    "record_cap": 30000,
    "max_months_per_query": 12,
    "vitality_thresholds_months": { "viva": 4, "rezagada": 18 }  // > rezagada = congelada
  },

  "report_types": {                         // LISTA CANÓNICA — ver tabla completa abajo
    "import":            { "label_es": "Importaciones",             "family": "customs",     "direction": "import", "detailed": false },
    "importDetalladas":  { "label_es": "Importaciones Detalladas",  "family": "customs",     "direction": "import", "detailed": true  },
    "cargasTotalesIngresos": { "label_es": "Cargas Totales - Ingresos", "family": "cargas", "direction": "import", "detailed": false }
    // ...
  },

  "countries": {
    "AR": {
      "name_es": "Argentina",
      "region": "sudamerica",
      "nomenclature": "NCM-SIM",            // el nombre del campo de posición arancelaria en el form
      "reports": {
        "import":           { "cutoff": "2026-07-31", "columns_measured": 13,   "names": { "local": "Importador",  "counterparty": null } },
        "importDetalladas": { "cutoff": "2026-07-31", "columns_measured": 36,   "names": { "local": "Importador",  "counterparty": null } },
        "export":           { "cutoff": "2026-07-31", "columns_measured": 9,    "names": { "local": null,          "counterparty": null }, "note": "no existe columna Exportador ni filtro" },
        "exportDetalladas": { "cutoff": "2026-07-31", "columns_measured": 31,   "names": { "local": "no_disponible","counterparty": null }, "note": "Exportador = 'No disponible' en 100% de filas, sin filtro" },
        "otrasOperaciones": { "cutoff": "2026-07-31", "columns_measured": 30,   "names": { "local": "Importador",  "counterparty": null } }
      }
    },

    "PY": {
      "name_es": "Paraguay", "region": "sudamerica", "nomenclature": "Codigo NCM",
      "reports": {
        "import": { "cutoff": "2026-07-31", "columns_measured": 42, "inferred": true,
                    "names": { "local": "Probable Importador", "counterparty": "Probable Proveedor" } },
        "export": { "cutoff": "2026-07-31", "columns_measured": null, "inferred": true,
                    "names": { "local": "Probable Exportador", "counterparty": "Probable Comprador" } }
      }
    },

    "MX": {
      "name_es": "México", "region": "norteamerica", "nomenclature": "Codigo SA",
      "reports": {
        "import":                { "cutoff": "2021-11-30", "columns_measured": 29, "names": { "local": null, "counterparty": null } },
        "cargasTotalesIngresos": { "cutoff": "2026-05-31", "columns_measured": null, "names": { "local": "Importador", "counterparty": "Proveedor" } },
        "cargasTotalesSalidas":  { "cutoff": "2026-05-31", "columns_measured": null, "names": { "local": "Exportador", "counterparty": "Comprador" } },
        "export":                { "cutoff": null, "columns_measured": null, "names": { "local": null, "counterparty": null } },
        "otrasOperaciones":      { "cutoff": null, "columns_measured": null, "names": { "local": null, "counterparty": null } }
      }
    }
  }
}
```

#### Reglas de cada campo

| Campo | Valor | De dónde sale |
|---|---|---|
| `countries.<CC>.reports` | solo las claves que ese país **ofrece** | `catalog.md`, tablas por continente |
| `cutoff` | ISO `YYYY-MM-DD` del último dato, o `null` si nunca se relevó | columna "Data through" / "Último dato" de `entities-*.md` y `fields-matrix.md` |
| `vitality` | **no se guarda** — `preflight.py` la calcula contra la fecha de hoy con `vitality_thresholds_months` | — |
| `names.local` | `"Importador"` / `"Exportador"` si hay columna **y filtro**; `null` si no hay columna; `"no_disponible"` si la columna existe pero es `No disponible` en el 100% y no hay filtro; `"Probable Importador"` etc. si es inferida | `entities-*.md` (columnas Importador/Exportador) + notas de `columns.md` para el caso `no_disponible` de AR |
| `names.counterparty` | `"Proveedor"` / `"Comprador"` / `"Shipper"` / `"Consignatario"` si existe, si no `null` | `entities-*.md` (Proveedor/Comprador), `cargas.md` (Shipper/Consignatario) |
| `inferred` | `true` en Paraguay (todos los reportes) y en AR `exportDetalladas` (aviso de estimación por IA) | `entities-latam.md`, `columns.md` |
| `columns_measured` | entero si hay un Excel real contado, `null` si no | `fields-matrix.md` + `columns-latam.md`; hoy solo 20 reportes tienen número |
| `nomenclature` | `NCM-SIM`, `NANDINA`, `SAC`, `SACH`, `Codigo NCM`, `Codigo SA`, `Codigo NC`, `Codigo JTS`, `UKTWED`, `Codigo CN FEA` | tabla "Nomenclature" de `entities-*.md` |
| `note` | texto corto en castellano, solo cuando hay una trampa puntual (AR export sin columna, UY sin CIF, EU en euros y FOB, etc.) | `fields-matrix.md` sección "las ⚠️ una por una" |

Cubrir **los 78 países**. Los que no nombran a nadie y no están medidos igual van,
con `names` en `null` y `columns_measured` en `null`: preflight necesita saber que
el reporte existe para no decir "IMPOSIBLE" cuando en realidad es "posible pero
anónimo".

#### Lista canónica de `report_types` (la costura entre Parte 1 y Parte 2 — congelada)

| id | label_es | family | direction | detailed | Países que lo ofrecen |
|---|---|---|---|---|---|
| `import` | Importaciones | customs | import | no | todos |
| `importDetalladas` | Importaciones Detalladas | customs | import | sí | AR BR GT NI DO RU TR |
| `export` | Exportaciones | customs | export | no | todos menos KE |
| `exportDetalladas` | Exportaciones Detalladas | customs | export | sí | AR BR GT NI DO RU TR |
| `otrasOperaciones` | Otras Operaciones | customs | both | no | AR MX |
| `historicoImport` | Histórico Importaciones | customs | import | no | BO CO EC HN VE PH ID VN AU CA KE |
| `historicoExport` | Histórico Exportaciones | customs | export | no | BO CO EC HN VE PH ID VN AU CA |
| `cargasIngresos` | Cargas - Ingresos | cargas | import | no | EC PE VE GT |
| `cargasSalidas` | Cargas - Salidas | cargas | export | no | EC PE VE GT |
| `cargasMaritimasIngresos` | Cargas Marítimas - Ingresos | cargas | import | no | BR PA US |
| `cargasMaritimasSalidas` | Cargas Marítimas - Salidas | cargas | export | no | BR PA US |
| `cargasHistoricoIngresos` | Cargas Histórico - Ingresos | cargas | import | no | BR |
| `cargasHistoricoSalidas` | Cargas Histórico - Salidas | cargas | export | no | BR |
| `cargasTotalesIngresos` | Cargas Totales - Ingresos | cargas | import | no | MX |
| `cargasTotalesSalidas` | Cargas Totales - Salidas | cargas | export | no | MX |
| `cargasMaritimas` | Cargas Marítimas | cargas | import | no | UY |
| `cargasAereas` | Cargas Aéreas | cargas | import | no | UY |
| `cargasTerrestres` | Cargas Terrestres | cargas | import | no | UY |
| `zonaFranca` | Zona Franca | zona | both | no | CR |
| `zonaLibreIngresos` | Zona Libre - Ingresos | zona | import | no | PA |
| `zonaLibreSalidas` | Zona Libre - Salidas | zona | export | no | PA |
| `transitos` | Tránsitos | transito | both | no | UY |
| `importTotalizadas` | Importaciones Totalizadas | customs | import | no | ES |
| `exportTotalizadas` | Exportaciones Totalizadas | customs | export | no | ES |
| `normativa` | Normativa | otro | n/a | no | UY (no es data de comercio; preflight siempre IMPOSIBLE) |

Los ids en camelCase siguen el esquema de URL de Softrade donde se conoce
(`import`, `importDetalladas`, `exportDetalladas` verificados en `site-flow.md`).

### Entregable B — `scripts/preflight.py`

Un comando que contesta, sin abrir nada, **si el pedido se puede resolver y con qué
salvedades**. Es lo que hace rápida a la skill: hoy eso es lectura manual de 4 md.

```
python scripts/preflight.py --country ar --report "impo detalladas" \
    [--by-company] [--from 2026-01 --to 2026-07] [--json]
```

- **Normaliza el reporte**: acepta alias en castellano ("impo", "las impo",
  "importaciones detalladas", "impo det", "expo", "cargas totales") y devuelve el id
  canónico. Si es ambiguo o no existe para ese país, lo dice.
- **Calcula vitalidad** de `cutoff` vs. hoy con los umbrales de `meta`.
- **`--by-company`**: marca que el usuario quiere atribuir a una empresa. Chequea
  `names.local`: si es `null` o `"no_disponible"`, es **IMPOSIBLE** por ese lado.
- **`--from/--to`**: si el rango entero cae después del `cutoff`, IMPOSIBLE
  ("pedís 2026 y la base está congelada en 2021"). Si parte del rango sirve, WARN
  con el rango efectivo.

Salida humana:

```
consulta      AR / importDetalladas   (impo detalladas)
vitalidad     VIVA        último dato 2026-07-31
por empresa   OK          filtro y columna: Importador
nomenclatura  NCM-SIM     (comparte 6 dígitos del SA con el resto)
columnas      36 medidas
veredicto     OK
```

```
consulta      AR / export   (las expo)
por empresa   IMPOSIBLE   AR no publica el exportador: no hay columna ni filtro.
                          Decíselo al usuario ANTES de planificar. Alternativa:
                          la columna Marca a veces nombra a la firma.
veredicto     IMPOSIBLE
```

Salida `--json`: `{ "country", "report", "report_alias_in", "vitality",
"cutoff", "by_company", "verdict", "warnings": [...], "messages_es": [...] }`.
`messages_es` son las frases exactas para que la IA se las repita al usuario.

**Exit codes:** `0` OK, `1` WARN (se puede, con salvedades), `2` IMPOSIBLE.

Casos que tienen que dar WARN o IMPOSIBLE (todos ya documentados en los md):

| Situación | Veredicto | Mensaje |
|---|---|---|
| reporte no ofrecido por el país | IMPOSIBLE | "CL no tiene Importaciones Detalladas; el estándar es lo máximo" |
| `--by-company` y `names.local` nulo | IMPOSIBLE | según país |
| `names.local` inferido (PY, AR expo det) | WARN | "Paraguay dice 'Probable': es inferido, no un registro oficial" |
| base congelada (>18 meses) | WARN o IMPOSIBLE si el rango es todo posterior | "MX Importaciones está congelada en 11/2021" |
| país que actualiza a diario (UY, EC…) y rango incluye el mes en curso | WARN | "el mes en curso todavía está cargándose; puede volver incompleto" |
| Europa (excepto ES/UA) | WARN | "valores en EUROS y FOB, no USD CIF; filtra por País de Procedencia, no origen" |
| `normativa` | IMPOSIBLE | "no es data de comercio exterior" |

### Entregable C — validación en `scripts/plan_run.py`

Hoy `plan_run.py` acepta cualquier `--country`/`--report` string y arma jobs aunque
el reporte no exista. Cambios (sin tocar la lógica de split de 12 meses, que ya
está bien):

1. Cargar `references/catalog.json` al arrancar.
2. Mapear alias de reporte → id canónico (misma función que `preflight.py`; que viva
   en un módulo compartido, p. ej. `scripts/_catalog.py`).
3. **Rechazar** (exit ≠ 0, mensaje claro) si algún `--country` no existe o no ofrece
   ese reporte.
4. **Rechazar** `--importador`/`--exportador` si ese lado no es filtrable para el
   país/reporte; `--proveedor` si no hay `counterparty`.
5. **Advertir** (no frenar) si `[--from,--to]` cae entero después del `cutoff`, o si
   la base está congelada. El usuario puede querer histórico igual.
6. Guardar en el manifest `"catalog_version": meta.captured` y el id canónico del
   reporte en cada job.
7. Que `plan_run.py` corra `preflight` internamente y pegue sus `messages_es` en un
   campo `"preflight": [...]` del manifest, para que una corrida retomada en otro
   chat los tenga sin recalcular.

### Entregable D — `scripts/run_state.py next --json`

`next` hoy imprime para humanos. Agregar `--json` que emita el job como objeto
(`country, report, date_from, date_to, filters, status, attempts, index,
download_dir`). Idem `status --json` (contadores + totales de filas/registros).
No cambiar el formato humano.

### Entregable E — tests

`tests/` en la raíz. `python -m unittest` o `pytest`, sin dependencias nuevas.

- `test_catalog.py`: `catalog.json` parsea; todo `report` de todo país está en
  `report_types`; los `report_types` cubren la tabla canónica; los 78 países están.
- `test_preflight.py`: los casos de la tabla de WARN/IMPOSIBLE de arriba, más
  AR importDetalladas = OK, EC import = OK, CL importDetalladas = IMPOSIBLE,
  MX import 2026 = IMPOSIBLE, MX cargasTotalesIngresos = OK.
- `test_plan_run.py`: combo inválido rechazado; `--exportador ar` rechazado;
  rango de 3 años → 3 jobs de ≤12 meses (comportamiento actual, no romperlo);
  el manifest queda con `catalog_version` y el id canónico.
- Para `inspect_download.py` no hace falta navegador: generar un `.xlsx` mínimo con
  `openpyxl` en un tmpdir (con columna `Identificador` repetida para simular
  filas/registros) y chequear el conteo y el exit 3 sobre 30.000 registros
  sintéticos.

### Criterios de aceptación — **hecho 2026-09-03**

- [x] `catalog.json` cubre 78 países y los 25 `report_types` (219 combinaciones
      país/reporte, 24 con conteo de columnas real). Generado por
      `tools/build_catalog.py`; `test_catalog.py` valida forma y cobertura.
- [x] `preflight.py` con veredictos OK / WARN / IMPOSSIBLE y exit 0/1/2;
      `--json` con `messages_es` para relevar al usuario. 14 casos en `test_preflight.py`.
- [x] `plan_run.py` rechaza país/reporte inexistente, filtro de empresa imposible y
      `--proveedor` sin contraparte; los WARN se imprimen y no frenan; el split de
      12 meses quedó igual. `catalog_version` e id canónico en el manifiesto.
      `--skip-preflight` para saltear.
- [x] `run_state.py next --json` y `status --json`; el formato humano intacto.
- [x] `python -m unittest discover -s tests` → 34 tests OK.
- [x] Ni una línea tocada en `site-flow.md`, `cargas.md`, ni en el manejo del navegador.

Módulo compartido nuevo: `scripts/_catalog.py` (carga, resolución de alias,
vitalidad). `preflight.py` y `plan_run.py` lo usan para no divergir.

Extra (no estaba en el spec): `run_state.py check RUN_DIR` valida un manifiesto
contra `catalog.json` (report canónico, país conocido, país que ofrece el report,
status válido, `done` con archivo). Es el gate de aceptación del Entregable 1 de
la Parte 2. `plan_run.py` también persiste los avisos de preflight en
`manifest["preflight"]`, y `next --json` / `status` los devuelven.

---

## Partes 2 y 3: para referencia

- **Parte 2 (ChatGPT):** el scaffolding browser-free de la capa de columnas. Prompt
  completo y entregables en `docs/prompt-chatgpt-cobertura.md`. Ya hecho de este
  lado: los 4 jobs `done rows:0` de `corrida-catalogo` (sesión degradada) quedaron
  corregidos — AR Exportaciones marcado `done` con sus números reales, BO/CL/CO
  reseteados a `pending`.
- **Parte 3 (Claude + login del usuario):** correr las sesiones de Softrade
  siguiendo `SKILL.md` + `site-flow.md`, con el canario primero, y volcar cada
  medición en los huecos que dejó la Parte 2.

Cuando la Parte 1 esté lista, se cierra el círculo: la Parte 3 mide, `catalog.json`
se actualiza (`columns_measured`, `cutoff`), y `preflight.py` deja de decir "no
relevado" para ese reporte.
