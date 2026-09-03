# Prompt para ChatGPT — Parte 2: cobertura de Softrade

Reparto acordado:

- **Parte 1 (la hace Claude Code):** `catalog.json` + `preflight.py` + validación en
  `plan_run.py` + `next --json` + tests. Es la parte que valida una consulta sin
  abrir el navegador.
- **Parte 2 (esta, para ChatGPT):** todo lo de *cobertura* que es texto y estructura
  y **no** necesita una sesión viva de Softrade — reorganizar el manifiesto de la
  corrida, crear los esqueletos de documentación de columnas de las familias sin
  medir, expandir la matriz y el checklist, y escribir la receta de medición.

## Qué pegarle a ChatGPT junto con el prompt

1. Este archivo.
2. `docs/handoff-motor-consultas.md` (trae la **lista canónica congelada de 25
   `report_types`**, que es la costura entre las dos partes).
3. `skills/softrade-batch/SKILL.md`
4. `skills/softrade-batch/references/`: `catalog.md`, `coverage.md`, `columns.md`,
   `columns-latam.md`, `fields-matrix.md`, `entities-latam.md`, `entities-world.md`,
   `cargas.md`
5. `skills/softrade-batch/scripts/`: `run_state.py`, `plan_run.py`,
   `inspect_download.py` (para que conozca el esquema del manifiesto y el formato de
   salida de `inspect_download.py`)
6. `corrida-catalogo/manifest.json` (estado actual)

---

## EL PROMPT (copiá de acá para abajo)

Sos el encargado de la **Parte 2 (cobertura)** del proyecto `softrade-batch`, una
skill que baja datos de comercio exterior de `app.softrade.info`. Trabajás **solo
con texto y archivos**: no tenés acceso al navegador ni a una sesión de Softrade, y
no lo necesitás para lo que te toca.

### Contexto del proyecto

La skill recibe un pedido en castellano, resuelve país/reporte/empresa/fechas, arma
un `manifest.json` en disco (fuente de verdad, resiste que se corte el chat), maneja
el Chrome logueado del usuario y baja los Excel. Dos reglas duras de Softrade, ya
implementadas: **12 meses máximo por query** y **30.000 registros máximo por query**
(son registros = declaraciones aduaneras, no filas; un archivo puede tener 53.000
filas y estar completo).

El relevamiento tiene tres capas. Las dos primeras (qué reportes existen en cada uno
de los 78 países; quién nombra a las empresas y hasta qué fecha llega la data) están
**completas**. La tercera (qué columnas trae de verdad el Excel de cada reporte)
está en **20 de ~130 combinaciones país/reporte**. Tu trabajo es dejar todo listo
para completar esa tercera capa rápido, salvo la medición en vivo, que la hace otro.

### Lo que NO tenés que tocar

- `catalog.json`, `preflight.py`, `plan_run.py`, `run_state.py`,
  `inspect_download.py` — son de la Parte 1. Los podés **leer** para conocer el
  esquema del manifiesto y el formato de `inspect_download.py`, pero no los editás.
- `references/site-flow.md` y cualquier cosa sobre cómo se maneja el navegador.
- Los datos descargados (`ejemplos_queries/`, `runs/*/downloads/`): están en
  `.gitignore`, no los vas a tener y no los necesitás.

### La lista canónica de `report_types` (congelada — usala tal cual)

Está en `docs/handoff-motor-consultas.md`. Son 25 ids en camelCase: `import`,
`importDetalladas`, `export`, `exportDetalladas`, `otrasOperaciones`,
`historicoImport`, `historicoExport`, `cargasIngresos`, `cargasSalidas`,
`cargasMaritimasIngresos`, `cargasMaritimasSalidas`, `cargasHistoricoIngresos`,
`cargasHistoricoSalidas`, `cargasTotalesIngresos`, `cargasTotalesSalidas`,
`cargasMaritimas`, `cargasAereas`, `cargasTerrestres`, `zonaFranca`,
`zonaLibreIngresos`, `zonaLibreSalidas`, `transitos`, `importTotalizadas`,
`exportTotalizadas`, `normativa`. Toda referencia a un reporte en tus entregables
usa uno de estos ids.

### Entregables

#### 1. `corrida-catalogo/manifest.json` reorganizado

Hoy tiene 46 jobs con `"date_from": "ultimo mes cargado"` (un placeholder) y nombres
de reporte en texto libre ("Cargas Maritimas - Ingresos"). Reescribilo:

- Un job = un país × un reporte, un solo mes reciente.
- Campo `report` = el id canónico (`cargasMaritimasIngresos`, no el texto libre).
- **Orden** = el de `coverage.md`: primero Pass A (una familia sin abrir por vez,
  país representante más barato), después Pass B, después Pass C.
- **Preservá los 8 jobs ya hechos** con su `status: done`, `file`, `rows`,
  `records`. No los rehagas.
- Mantené el esquema exacto que leen `run_state.py` / `plan_run.py` (mirá esos
  scripts): `version`, `label`, `created_at`, `download_dir`, `max_months`,
  `catalog_version` (poné `"2026-09-02"`), `jobs[]` con `country, report,
  date_from, date_to, filters, status, file, rows, records, attempts, note,
  updated_at`. Validá con `run_state.py check corrida-catalogo` hasta que salga 0.
- Para `date_from`/`date_to`, en vez del placeholder usá una convención clara y
  fija — proponé una y documentala arriba del archivo o en un `README` corto de la
  carpeta (p. ej. `"latest"` para "el último mes cerrado que corresponda", que la
  Parte 2-ejecución resuelve al abrir el form).
- Cada job lleva en `note` el filtro de partida a 4 dígitos (6 en CN/VN) que ya
  figura en el manifiesto actual, más la familia de `coverage.md` a la que pertenece
  (p. ej. `"F7 Cargas Ingresos · pass A · partida 4 díg"`).

#### 2. Esqueletos de documentación de columnas

Siguiendo **exactamente** el formato de `columns-latam.md` (encabezado por
país/reporte, tabla `# | Column | Example`, sección "Reading this correctly",
conteos de filas/registros/columnas):

- `references/columns-cargas.md` — familia Cargas. Consolidá lo que ya está medido
  de BR Cargas Marítimas Ingresos (está en `cargas.md`) y agregá secciones vacías
  con `<!-- PENDIENTE: medición en vivo -->` para: US `cargasMaritimasIngresos`,
  PE/EC `cargasIngresos`, PA `cargasMaritimasIngresos`, VE `cargasIngresos`,
  UY `cargasMaritimas`/`cargasAereas`/`cargasTerrestres`, GT `cargasIngresos`,
  MX `cargasTotalesIngresos`/`cargasTotalesSalidas`, y los Salidas de BR/PA/US.
- `references/columns-world.md` — Asia, África y Ucrania. Todas las secciones
  vacías con el placeholder, una por país que nombre empresas (los de la tabla
  "Summary: where company names exist" de `entities-world.md`).
- `references/columns-otras-familias.md` — Histórico, Zona Franca/Libre, Tránsitos,
  Totalizadas, Otras Operaciones (lista completa AR). Secciones vacías.

Cada sección vacía tiene que traer ya escrito, de `entities-*.md` y `catalog.md`:
la nomenclatura del país, la fecha de corte conocida, y qué nombres de empresa se
esperan (Importador / Proveedor / Shipper / Consignatario / ninguno).

#### 3. `fields-matrix.md` — NO la reescribas

Es una tabla curada de lo **medido** más 3 bloques de análisis en prosa ("cómo leer
la vitalidad", "las ⚠️ una por una", "lo que se lee de la matriz"). **Esa prosa no
se toca ni se borra.** Lo único que se cambia es una línea en la sección "Lo que
falta medir" apuntando al manifiesto como el tracker del pendiente. No metas 90
filas `<!-- pendiente -->` en el medio de la matriz: el objetivo completo ya vive
en el manifiesto.

#### 4. `coverage.md` — NO la reescribas

Ya tiene la estructura Pass A / B / C con las notas por casilla (el aviso del
canario, "establecer qué es Histórico", "confirmar si Totalizadas exporta Excel",
Vista Global / Consulta Regional / Acumulados). **Esas notas son el valor del
archivo, no se borran.** Lo único que se agrega es un párrafo arriba diciendo que
el checklist operativo es `corrida-catalogo/manifest.json` y que este archivo es el
*por qué* de ese orden. El 1:1 casilla↔job lo da el manifiesto vía `run_state.py
next`, no hace falta forzarlo en el markdown.

#### 5. `docs/receta-medicion.md`

La secuencia copy-paste para medir un reporte nuevo, destilada de la sección
"Learning a new report type" de `SKILL.md` y del formato de salida de
`inspect_download.py`: bajar → renombrar con la convención → correr
`inspect_download.py FILE --record corrida-catalogo --job N` → qué líneas de la
salida van a `columns-*.md`, cuáles a `fields-matrix.md`, cómo se tilda la casilla
en `coverage.md`. Media carilla, sin vueltas.

#### 6. (Opcional, si sobra tiempo) generador de informe

Un script o plantilla que tome un Excel descargado de Softrade y saque un informe
ejecutivo en HTML como `runs/centro-negocios-chino-argentino-2026/informe_importaciones_cnca_2026.html`
(FOB total, despachos distintos = `Identificador` únicos, ranking de NCM, por aduana,
por mes). Que lea el Excel con `pandas`, no que pida pegar datos. Marcalo como
entregable aparte, no bloquea a los otros cinco.

### Criterios de aceptación

- [ ] **`python skills/softrade-batch/scripts/run_state.py check corrida-catalogo` sale 0.**
      Ese comando valida cada job contra `catalog.json`: report canónico, país
      conocido, país que ofrece ese report, status válido, `done` con `file`.
      Hoy sale 1 justamente porque los reports están en texto libre; tu Entregable 1
      es dejarlo en 0.
- [ ] `run_state.py status corrida-catalogo` y `next corrida-catalogo` corren sin error, y `next` devuelve el primer job de Pass A.
- [ ] Los 8 jobs ya hechos siguen `done` con sus números.
- [ ] Todo `report` del manifiesto es uno de los 25 ids canónicos.
- [ ] Los tres `columns-*.md` nuevos siguen el formato de `columns-latam.md` y cada sección vacía trae nomenclatura + corte + nombres esperados.
- [ ] `fields-matrix.md` lista todos los reportes objetivo, medidos y pendientes.
- [ ] Las casillas de `coverage.md` mapean 1:1 con los jobs del manifiesto.
- [ ] Nada tocado en `site-flow.md` ni en los 5 scripts de la Parte 1.

### Después de esto

Cuando el scaffolding esté, seguís como **copiloto de la corrida en vivo**: el
usuario abre Softrade en su Chrome y vos lo guiás job por job siguiendo `SKILL.md`
y `site-flow.md` (que te va a pegar), y cada medición se vuelca en los huecos que
dejaste preparados.
