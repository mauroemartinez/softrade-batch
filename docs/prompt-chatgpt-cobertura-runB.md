# Prompt para ChatGPT — sub-corrida B (descargas en vivo, cuenta #2)

Ahora ChatGPT SÍ maneja navegador. La corrida de cobertura (112 jobs) se parte en
dos manifiestos disjuntos, uno por cuenta de Softrade, para correr en paralelo sin
pisarse:

| Sub-run | Manifiesto | Jobs | Quién |
|---|---|---|---|
| A | `corrida-catalogo/split-claude/manifest.json` | 37 (Pass A + Detalladas + Cargas restantes) | Claude Code + tu cuenta #1 |
| **B** | **`corrida-catalogo/split-chatgpt/manifest.json`** | **75 (Exportaciones LatAm + Asia/África + anónimos)** | **ChatGPT + tu cuenta #2** |

El `corrida-catalogo/manifest.json` original (112 jobs) queda como referencia, **nadie
lo edita**. Al final Claude fusiona los dos resultados ahí y en los `.md`.

## Qué pegarle a ChatGPT junto con el prompt

Todo el repo, o como mínimo:
`skills/softrade-batch/SKILL.md`, **`skills/softrade-batch/references/site-flow.md`** (crítico),
`skills/softrade-batch/references/catalog.json`, `skills/softrade-batch/references/columns-latam.md`
(formato de salida), `docs/receta-medicion.md`, `skills/softrade-batch/scripts/` completo,
`corrida-catalogo/split-chatgpt/manifest.json`.

---

## EL PROMPT (copiá de acá para abajo)

Sos el driver de la **sub-corrida B** de `softrade-batch`: bajás reportes de
`app.softrade.info` con tu navegador y tu propia cuenta de Softrade (la #2, distinta
de la que usa Claude Code), y medís las columnas de cada uno. 75 jobs, todos en
`corrida-catalogo/split-chatgpt/manifest.json`.

### Reglas de oro

1. **El manifiesto en disco es la verdad.** Después de cada archivo, escribís el
   resultado con `inspect_download.py --record`. Si se corta el chat, otro retoma
   con `run_state.py next` sin releer nada.
2. **Sólo tocás `corrida-catalogo/split-chatgpt/`.** Nunca `split-claude/`, nunca el
   `corrida-catalogo/manifest.json` de 112 jobs, nunca `catalog.json` (Claude lo
   regenera al final).
3. **Nunca escribís credenciales de Softrade.** Abrís la pestaña, te logueás vos a
   mano, seguís.
4. **Leé `site-flow.md` entero antes de tocar el navegador.** Softrade es Ionic +
   Angular y casi todo falla en silencio. Lo mínimo:
   - El período va con el **calendarito**, no con texto. `form_input` en ese campo
     "anda" y la consulta corre con el mes anterior. Leé el campo después de tocarlo.
   - **Buscar no dispara con click de JS.** Click por coordenada.
   - **NCM/partida crea un chip fantasma vacío** que rompe la búsqueda. Contá los
     chips: exactamente uno no vacío por código.
   - **"Consulta demasiado extensa"** (>30.000 registros) = el botón de Excel **no
     baja nada**. Chequeá ese cartel *antes* de bajar. Si salió, entrás con 6
     dígitos de partida en vez de 4 (obligatorio en CN y VN) o un mes más corto.
   - La descarga se confirma **mirando el filesystem** (listar el dir antes y
     después), no la pantalla: Softrade manda el archivo por WebSocket, no hay HTTP
     que mirar y la pantalla dice "descargando" igual aunque no baje nada.
   - **Canario:** al empezar la sesión y después de cualquier resultado vacío
     inesperado, corré una consulta que sabés que es grande (AR Importaciones
     Detalladas, un mes, sin filtros → debe dar "demasiado extensa"). Si el canario
     vuelve vacío, la sesión se degradó: pará, no registres nada como `skipped`.

### El loop, por job

1. `python skills/softrade-batch/scripts/run_state.py next corrida-catalogo/split-chatgpt`
   — un job. El `note` te dice la familia y que el filtro es partida a **4 dígitos**
   (`8544`), **6 en China y Vietnam** (`854442`).
2. Listá `corrida-catalogo/split-chatgpt/downloads/` (foto "antes").
3. En Softrade: entrá por el menú de banderas (no por URL), elegí país y reporte,
   poné `latest` = el último mes cerrado que el form muestre cargado, aplicá la
   partida. Verificá los filtros contra el **panel de resultados** (no contra el
   form).
4. Chequeá "demasiado extensa". Si salió: `run_state.py split corrida-catalogo/split-chatgpt --job N`
   y seguís con los sub-jobs mensuales; si un mes solo también se pasa, narrow por
   6 dígitos.
5. Dispará el Excel desde Descargas (click en el `ion-img`, no en el tooltip).
   Confirmá con el filesystem (foto "después" ≠ "antes").
6. Renombrá: `<pais>_<report>_<yyyymm>_<partida>.xlsx`.
7. `python skills/softrade-batch/scripts/inspect_download.py corrida-catalogo/split-chatgpt/downloads/ARCHIVO.xlsx --record corrida-catalogo/split-chatgpt --job N`
   — cuenta filas/registros, detecta truncado (exit 3) y HTML de login (NOT DATA),
   y escribe el resultado en el manifiesto con el status correcto.
8. Si exit 3 (truncado): `run_state.py split ... --job N`, rehacé.
9. Volcá la salida a **`corrida-catalogo/split-chatgpt/RESULTS.md`** (NO a los
   `columns-*.md` ni a `fields-matrix.md` del repo — esos los fusiona Claude para
   evitar choques de merge). Formato: una sección por job, con el bloque de
   `inspect_download.py` (rows, records, columns y la lista completa de columnas) y
   una línea con los campos clave: FOB / CIF / empresa local / contraparte /
   Incoterm / Marca (✅ / ⚠️ / no).

### Cuando pares

`run_state.py status corrida-catalogo/split-chatgpt` y contá done / skipped /
failed. Entregá de vuelta: el `split-chatgpt/manifest.json` actualizado y el
`split-chatgpt/RESULTS.md`. Si algún job falló repetido, decilo con la nota, no lo
presentes como completo.

### Diferencia registros vs filas

El tope de 30.000 cuenta **declaraciones aduaneras**, no filas. Un archivo puede
tener 50.000 filas y estar completo. `inspect_download.py` cuenta bien; nunca
estimes registros mirando filas.
