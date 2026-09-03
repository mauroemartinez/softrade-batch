# Softrade: how the site actually behaves

Verified live against `app.softrade.info` on 2026-09-02, Argentina / Importaciones
Detalladas. Softrade is an Ionic + Angular app, which is the source of most of the
gotchas below.

## Session

The session token is held **per tab**, not in a shared cookie. A tab you open
yourself lands on `/login` even when the user has another tab logged in, in the
same Chrome profile. There is no way around this from outside the tab.

So: ask the user to log in **in the tab you opened**, the one inside your tab
group, and to tell you when they are done. Never type their credentials. If the
group's tab gets recreated mid task, the login is lost and you have to ask again.

Both `localStorage` and `sessionStorage` hold an `auth_token`, but a fresh tab
still lands on the login screen, so treat the session as per tab regardless. Never
read, copy or reuse those tokens.

Once the session dies, exports quietly return an HTML login page with a
spreadsheet filename. `inspect_download.py` catches that and reports `NOT DATA`.

## Navigation: you must use the flag menu

The address bar shows tidy URLs like:

```
https://app.softrade.info/home/formulario/AR/importDetalladas
https://app.softrade.info/home/detalle/AR/importDetalladas     <- results view
```

**These are not entry points. Do not navigate to them.** Verified: loading any of
them directly, including one known to be valid, silently redirects to
`/home/dashboard`. The route needs app state that a cold load does not have. The
URL is an output, useful for reading where you are, never for getting there.

The only way in is the dashboard:

1. Pick the continent tab (Africa, Asia, Centroamerica, Europa, Norteamerica,
   Oceania, Sudamerica), or Global / Regional.
2. Click the country flag. A popover opens, titled with the country name.
3. Click the report.

Argentina's popover offers: Importaciones, Importaciones Detalladas,
Exportaciones, Exportaciones Detalladas, Otras Operaciones. **The list varies by
country**, so read the popover rather than assuming these five.

Read the popover items reliably with JS instead of guessing coordinates:

```js
[...document.querySelectorAll('ion-popover ion-item, ion-list ion-item')]
  .map(e => e.innerText.replace(/\s+/g,' ').trim()).filter(Boolean)
```

Confirm where you landed with:

```js
document.querySelector('ion-title.spanPaisOperacionCabezalEscritorio').textContent
// " Argentina  -  Importaciones Detalladas "
```

Report ids appearing in the URL, for recognising state: `import`,
`importDetalladas`, `exportDetalladas`. These are correct ids, they simply cannot
be used as entry points.

**Do not navigate rapidly.** Chaining several navigations in one batch left the SPA
in a blank blue broken state that needed a reload. Let each page settle.

## Verified live 2026-09-03 on AR Exportaciones and AR Otras Operaciones

A second live pass corrected several things below. Where this section contradicts
an older one, this section is what was actually observed.

### The period already defaults to the last loaded month

Both Periodo fields arrive pre-filled with the newest month Softrade holds
(`07/2026` on Argentina). **A single-month query on the newest month therefore
needs no calendar interaction at all**: read the two fields back, confirm, and
search. That removes the most fragile step in the whole flow from the majority of
coverage-style queries. Only reach for the widget when you need an older period.

### JS .click() does not fire Buscar

This is the one that wastes the most time, because it fails silently in both
directions:

| Control | JS `.click()` | Real coordinate click |
|---|---|---|
| Country flag | works | works |
| Popover report item | works | works |
| **Buscar** | **does nothing** | works |
| Excel download `ion-img` | works | works |

A JS click on Buscar returns without error and leaves you on the form, which looks
exactly like a search that returned nothing. Always click Buscar by coordinate,
taking the position from `getBoundingClientRect()` rather than from a screenshot:

```js
const b = [...document.querySelectorAll('ion-button,button')]
  .find(e => /^Buscar$/i.test((e.innerText||'').trim()));
const r = b.getBoundingClientRect();   // then click (left+width/2, top+height/2)
```

### Zero results looks identical to a search that never ran

When a query matches nothing, Softrade **stays on `/home/formulario/...`, shows no
message, and raises no alert**. There is no "sin resultados" anywhere. So "still on
the form" has three possible meanings: the click missed, the query is still
running, or the answer is genuinely empty.

Tell them apart in this order:

1. `document.querySelector('ion-loading,.loading-wrapper')`, still running.
2. URL changed to `/home/detalle/...`, it worked.
3. Neither, after the spinner is gone, either an empty result or a dead click.
   Re-click Buscar by coordinate once. If it still does not move, treat it as
   genuinely empty and `skip` the job.

### NCM-SIM is a p-autoComplete in chip mode

Not `p-chips`, which is why a `p-chips` selector finds nothing. The real structure
is `p-auto-complete` > `.p-autocomplete-chip-item` > `p-chip`. On AR Exportaciones
the same field is a **plain text input** with no chips at all, so check per report
rather than assuming.

A 6-digit code typed as `854442` is normalised by Softrade to `8544.42`.

### Filters survive leaving the report, and Reset does not clear them

Two separate traps that compound:

- **Reset does not empty the chip fields.** The codes stay.
- **Neither does navigating away and back** through the flag menu. Re-entering the
  report shows the previous query's chips still loaded.

In a batch run that means one tramo's filter silently contaminates the next, and
the results look perfectly plausible. **Read the filter fields back before every
search**, and clear chips explicitly by dispatching a click on their remove icon:

```js
const ac = [...document.querySelectorAll('p-auto-complete')]
  .find(e => /8544/.test(e.innerText || ''));
[...ac.querySelectorAll('[data-pc-section="removeicon"], .p-chip-remove-icon')]
  .forEach(i => i.dispatchEvent(new MouseEvent('click', {bubbles: true})));
```

### The date widget is PrimeNG, not Ionic

The Periodo control is a `p-datepicker` (`span.p-datepicker` wrapping the readonly
input, with its own trigger button), not an `ion-datetime`. Any guidance written
against Ionic selectors will not find it.

### A whole session can start returning empty results, and it looks like missing data

**This is the most important thing learned on 2026-09-03, and it invalidated four
wrong conclusions before it was spotted.**

In one session: the first search returned data and downloaded fine. Every search
after it returned nothing, across three countries, five reports, filtered and
unfiltered. The run ended by searching **AR Importaciones Detalladas, one month, no
filters at all**, a query whose result is known to be 25,061 records. It returned
nothing, with no message.

That single result rules out every per-report explanation. Along the way these
conclusions were drawn and are all **unsafe**:

- "the pre-filled default month is empty"
- "Ecuador has no recent export data"
- "AR Otras Operaciones has no data for 07/2026"
- "the account is not subscribed to Mexico"

Each looked well-evidenced. All of them are equally explained by the session
degrading after the first successful query.

**Leading hypotheses, none confirmed:** the account's monthly row allowance is
exhausted (Softrade shows consumption nowhere, so this is invisible), or the server
throttles after a burst of queries.

**What to do about it.** Before concluding that any report lacks data, run a
**canary query**: a report and period known to return a large result, AR
Importaciones Detalladas, one recent month, no filters, which should trigger
`demasiado extensa` immediately. If the canary comes back empty, the session is
broken and **every "sin datos" result since the last good download is worthless**.
Stop, tell the user, and do not record any of it in the manifest as `skipped`.

Run the canary at the start of a batch, and again after any unexpected empty
result. It costs one query and it is the difference between documenting the
database and documenting a broken session.

### Reports whose default period returned nothing (2026-09-03, UNRELIABLE)

Measured 2026-09-03 on Ecuador, whose header advertises `23/8/2026`:

| Report | Period | Filter | Result |
|---|---|---|---|
| EC Importaciones | 08/2026 | NANDINA 8544 | **0 rows** |
| EC Importaciones | 08/2026 | NANDINA 8544.42 | **0 rows** |
| EC Exportaciones | 08/2026 | none at all | **0 rows** |
| EC Exportaciones | 07/2026 | none at all | **0 rows** |
| EC Exportaciones | 01/2026 | NANDINA 0803.90 | **0 rows** |
| EC Importaciones | (an earlier month) | NANDINA 8544 | 3,391 rows, per `columns-latam.md` |

**Treat this table as evidence of the broken session above, not as evidence about
these databases.** It is kept only so the pattern is recognisable next time.

What does still stand, independently: empty results are **silent**. Softrade stays
on the form, shows no message and raises no alert, so "no data" and "the session is
broken" and "the click missed" all look identical. That is why the canary matters.

### Calendar coordinates do not transfer between forms

The month grid is positioned relative to the field, and forms differ in height, so
the pixel coordinates that hit "Jul" on one report land on nothing on the next.
Re-derive them per form, and **always read the field back**: a failed calendar
click is silent, and on a form where the default period is empty it looks exactly
like a report with no data.

This was hit live: coordinates taken from EC Exportaciones did nothing on EC
Importaciones, and only the read-back revealed the fields still said `08/2026`.

### The header cutoff is per country, not per report

The blue header showed `31/7/2026` on Argentina, and AR Importaciones does hold
July. **AR Otras Operaciones returned zero rows for 07/2026 with no filters at
all.** The cutoff in the header is the country's newest data in general, and an
individual report can lag far behind it.

So an empty month is not proof of an empty database. Before recording "sin datos",
try an older period on that specific report.

### Download icons differ by report

AR Exportaciones offers `excel_off.svg`, `mail_off.svg` and
`excel_personalizado_off.svg`. There is no `report_off.svg` on this form, so match
on `excel_off` rather than on position.

## The data cutoff tells you itself

The blue header shows the last loaded date, e.g. `31/7/2026`, and the month picker
**greys out months past the cutoff**. Read it instead of assuming the current month
exists. Asking for "este ano" in September 2026 means January through July, not
January through September, and a range past the cutoff just returns less than the
user expects with no warning.

## Filling the Periodo fields: the big trap

The Periodo fields are month pickers (`MM/YYYY`), not free text.

**`form_input` on them does not work.** It updates the visible text and leaves the
Angular model untouched, so the search silently runs on the *old* period. This
fails without any error: the form reads `01/2026`, the query runs on `07/2026`, and
you get a plausible, wrong dataset.

Always use the widget:

1. Click the "Choose Date" button next to the field.
2. Click the year arrows until you are on the right year.
3. Click the month.

### Verify the field, do not trust the click

This is the single most fragile step in the whole flow, and it fails in a way that
looks like success. **Clicks on the calendar have been observed applying even
though the browser tool reported a timeout**, so a reported failure is not evidence
that nothing happened, and a reported success is not evidence that it did. Blind
retries after a "timeout" therefore double-click months and land on the wrong one.

Never retry on the tool's return value. Retry on the field's value:

1. Open the picker.
2. Pick the month **by index** rather than by hunting for its label, the grid is
   a fixed 12-cell layout, so January is cell 0 and December is cell 11.
3. **Read the field back** and compare against what you intended:

```js
document.querySelectorAll('input[readonly]')  // the Periodo inputs
```

4. Retry **only if the value did not change.** If it changed to the wrong month,
   that is a different bug: fix it by picking again, not by repeating the click
   that produced it.
5. After at most two corrective attempts, stop and tell the user, rather than
   thrashing the widget.

Treat every calendar interaction as write-then-read. The read is not optional and
it is not a screenshot.

Then **verify against the results sidebar**, not against the form. After searching,
the left panel shows the period the query actually used:

```
Periodo    1/2026 al 7/2026
Importador NOMBRE DE LA EMPRESA S.A.
```

That sidebar is the only trustworthy confirmation of what was queried. Check it
before recording a job as done.

## The 12-month ceiling on a single query

**Softrade will not run a query spanning more than 12 months.** Three years is
three searches minimum, never one. `plan_run.py` enforces this by splitting any
longer range into chunks of at most `--max-months` (default 12), so a planned run
never produces an illegal job.

Do not confuse this with the 30,000-record truncation. They are independent limits
that stack:

| Limit | Constrains | Failure mode |
|---|---|---|
| 12 months | period length | Refuses to search no loud, you notice |
| 30,000 records | result volume | Searches anyway and **silently truncates the export** |

A period that fits inside 12 months says nothing about whether the result fits
inside 30,000 records. Ask for the full period first and split only when Softrade
actually complains, see "Plan wide, narrow only when Softrade complains" in
`SKILL.md`.

## The Importador field

It is a chip multi-select with its own nested search box, not a text input.

1. Click the Importador combobox. A dropdown opens showing "Ingrese su consulta..".
2. Typing now goes nowhere. Click the **"Buscar" box inside the dropdown** first,
   then type.
3. Results appear as checkboxes. Tick one or more, they become chips in the field.
4. Close the dropdown with its X.

**Always show the user the candidates before picking.** Real pattern seen in testing: one search term returned two entities, a foreign
parent company whose name merely contains the term, and the local operating
company the user actually meant.

A user naming the local operating company means the second. The first would return
a different, entirely plausible dataset. There is no way to tell
from the numbers afterwards that you picked wrong, so confirm before searching.

Marca works the same way. NCM-SIM is a chips input.

## NCM-SIM creates a phantom empty chip

Typing a code into NCM-SIM and pressing Enter produces **two** chips: the real one
and an empty one. The empty chip is nearly invisible in the UI and it **breaks the
search**: a real run lost its first query this way, and the failure looks like the
filter simply not matching rather than like a malformed input.

Softrade appears to commit the chip as you type and again on Enter. Either way,
never assume the field holds what you meant.

**Count the chips before every search.** There must be exactly one non-empty chip
per code you intended, and no empty ones:

```js
[...document.querySelectorAll('ion-chip')].map(c => c.innerText.trim())
// ["6309", ""]  <- the second one is the phantom; remove it before searching
```

Delete any blank chip with its own X before firing Buscar. If the search returns
nothing, check this first: an empty chip is a far more common cause than a genuinely
empty period.

## Filters on the Consulta por Parametros form

In order: Periodo (desde / al), Identificador (desde / al), NCM-SIM, Importador,
Pais de Origen, Marca, Tipo de Documento, Transporte, Aduana de Ingreso, Pais de
Procedencia, GATT-NALADISA, Acuerdo ALADI, U$S CIF (desde / hasta), U$S Unitario
(desde / hasta), Kgs Brutos (desde / hasta). Then Ayuda, Reset and Buscar.

`read_page` returns these **without labels**, as a flat run of comboboxes and
textboxes. Map them by position against this list rather than by name.

## Results view

`Volver` returns to the form **with the filters still set**, which makes stepping
through consecutive periods cheap: go back, change only the month, search again.

The left panel carries the download controls under **Descargas**, plus **Totales**
and **Rankings** (por Codigo NCM-SIM, por Importador, por Mes). Results are paged,
with the page selector at the bottom left.

Do not read the results grid. The export has the same data, and reading the table
on screen is the single most expensive thing you can do in a long run.

## Confirming a download: not by HTTP

There is no REST API to watch. The app talks over SockJS/WebSocket, so
`read_network_requests` shows **only static assets** and never the query or the
export. Watching network traffic to confirm a download does not work here.

Confirm two ways instead:

1. **Ask the app whether the page even offers an export**, before clicking:

```js
JSON.parse(localStorage.getItem('sesion')).paginaActual
// { pagina, consulta, modulo, desglose, tieneExcel, tienePdf,
//   tieneTotales, tieneDesgloses, tieneFavoritos, ... }
```

`tieneExcel` false means this view has no Excel export, so stop rather than hunting
for a button.

2. **Check the filesystem.** List the download directory before and after, and
confirm a new file appeared and grew. That is the only real evidence, and it works
whether the file comes from an HTTP response or is built client-side as a blob.
Then run `inspect_download.py` on it.

## Clicking things reliably

Coordinates drift. The viewport `read_page` reports and the screenshot's coordinate
frame did not agree in testing, and a click computed from a screenshot landed one
form row off, silently filling the wrong filter. Prefer, in order:

1. **JS `.click()` by text** for menu items. This is the most reliable way into a
   report:

```js
[...document.querySelectorAll('ion-item')]
  .find(e => e.innerText.replace(/\s+/g,' ').trim() === 'Importaciones Detalladas')
  .click()
```

2. **`find` + `ref`** for form controls. Note that `find` sometimes returns a
   **tooltip** rather than the button it describes, and clicking a tooltip does
   nothing while looking like it worked. If an action seems to have no effect,
   re-query for the `button` role specifically.

3. **Coordinates** only as a last resort.

## Screenshots stop working when the tab is backgrounded

If `computer:screenshot` starts timing out with "renderer may be frozen" while JS
still evaluates fine, the tab is simply not visible. Check:

```js
document.hidden   // true means Chrome is not rendering this tab
```

A native "Save as" dialog, or the user switching tabs, causes this. It is not a
crash, and it is another reason to read state with JS instead of pictures.

## The Descargas panel

`Descargas` in the left sidebar is a collapsible accordion, collapsed by default in
some states. Expand it before looking for the export buttons, and note that
clicking the header toggles, so clicking twice closes it again. The panel holds
Excel and other export options; `paginaActual.tieneExcel` tells you whether an
Excel export exists for the current view before you go looking.

## Triggering the Excel export

Expand **Descargas** in the left sidebar. It holds three controls, none of which is
a `<button>`, so `find` tends to return their tooltips instead. Clicking a tooltip
does nothing while looking like a successful click, which is how a run can appear
to download and produce no file.

Target the images directly:

```js
[...document.querySelectorAll('ion-img.imgBotonDescarga')]
  .find(e => /excel_off/.test(e.src)).click()
```

| icon `src` | what it does |
|---|---|
| `excel_off.svg` | download the full result as .xlsx |
| `mail_off.svg` | send the result by email (imports) |
| `report_off.svg` | generate a report (exports) |
| `excel_personalizado_off.svg` | custom Excel, pick your own columns |

The `_off` suffix is the idle sprite and swaps on hover, so match with a substring,
not the whole filename. Both Excel controls sit inside an `<app-descarga-excel>`
element, which is another way to find them.

A plain `.click()` on the `ion-img` does not need the tab focused, but **it is not
reliable on its own.** In real runs the selector was correct and the click still
did nothing, repeatedly. The Descargas panel also renders its icons **partially
clipped**, so the element's geometric centre can fall outside the visible area and
a coordinate click aimed there hits nothing.

Work through it in this order, and do not skip a step because the previous one
reported success:

1. **Confirm the panel is actually expanded.** Clicking the header toggles, so a
   "click to expand" that ran twice has closed it again. Check that the icons are
   in the DOM *and* have a non-zero box:

```js
[...document.querySelectorAll('ion-img.imgBotonDescarga')]
  .map(e => { const r = e.getBoundingClientRect();
              return {src: e.src.split('/').pop(), w: r.width, h: r.height, top: r.top}; })
```

2. **Try `.click()` on the element first.** It is the cheapest path and it often
   works.
3. **If no file appears, fall back to a coordinate click inside the visible part
   of the icon.** Intersect the element's rect with the viewport and aim at the
   centre of the intersection, not the centre of the element:

```js
const r = el.getBoundingClientRect();
const x = (Math.max(r.left, 0) + Math.min(r.right, innerWidth)) / 2;
const y = (Math.max(r.top, 0) + Math.min(r.bottom, innerHeight)) / 2;
```

   Scroll the panel so the icon is fully visible before computing this, if it is
   clipped by its own container rather than by the viewport.
4. **Check the filesystem. Always.** This step is mandatory and it is the only
   evidence that exists. Softrade moves its data over a WebSocket, so there is no
   HTTP request to watch, and the screen says "descargando" whether or not a file
   was ever produced. List the download directory and confirm a **new** file
   appeared, compare against the listing you took before clicking, since an older
   export with a similar name is not proof of anything.
5. Only after a new file exists, rename it and inspect it.

Never report a download as done on the strength of a click returning successfully.

## Downloaded file names

Exports land in Chrome's download directory as:

```
detalle_{CC}{report}_{Y}-{M}-{D}-{HHMMSS}.xlsx
detalle_ARimportDetalladas_2026-8-3-125819.xlsx
```

Month and day are not zero padded, and the timestamp is the browser's. Since the
name encodes country and report but **not the period queried**, two tramos of the
same report differ only by timestamp. Rename each file to something meaningful as
soon as it lands, and record that name in the manifest, or a long run becomes a
directory of indistinguishable files.

## Large exports take time

A single month of Argentine exports to one destination country was 53,525 rows and
7 MB, and the file sat as a `.crdownload` for around a minute before it appeared.
Do not conclude a download failed because the directory looks unchanged after a few
seconds. Poll for the final filename, and treat a lingering `.crdownload` as
in progress rather than as a failure.

## The 30,000 record cap, and why row counts lie about it

Softrade refuses to return more than **30,000 customs records** per query. When a
query exceeds it, the results screen shows:

> Consulta demasiado extensa
> Solo se toman en cuenta los primeros 30.000 registros

**The Excel carries no trace of that warning.** It just contains the first 30,000
records and looks perfectly normal.

### A record is not a row

This is the part that catches people. One customs record is one declaration, and
the export writes **one row per line item**, so a complete file routinely holds
far more than 30,000 rows. Measured on real files:

| Report | Rows | Records | Rows per record |
|---|---|---|---|
| AR Importaciones Detalladas, one company, 7 months | 143 | 22 | 6.50 |
| AR Importaciones Detalladas, heading 8544, 1 month | 25,061 | 3,180 | **7.88** |
| AR Exportaciones Detalladas, one destination, 1 month | 53,525 | 25,162 | 2.13 |
| AR Otras Operaciones, one code, 1 month | 25 | 12 | 2.08 |

A 53,525-row file was **complete**, because it held only 25,162 records. Meanwhile
a 30,000-row file could easily be truncated. **Counting rows tells you nothing
about truncation**, and the ratio swings from 2 to 6.5 between reports, so it
cannot be predicted either.

### An over-cap query produces no file at all

Verified three times on 2026-09-02, with Mexico Cargas Totales, Vietnam
Importaciones and China Importaciones: when the screen shows "Consulta demasiado
extensa", clicking the Excel button **downloads nothing**. Not a truncated file, no
file. The click reports success, the download never starts, and repeating it does
not help.

So the practical rule is simpler than "detect truncation in the file":

1. Read `window.__estado()` or the page text for `demasiado extensa` **before**
   clicking Excel.
2. If it fired, narrow the query and search again. Do not click the download.
3. The record-count check in `inspect_download.py` stays as the backstop for files
   that do arrive.

### A 4-digit heading is not small everywhere

Sizing depends enormously on the country. Heading 8544 over one month:

| Country | Result |
|---|---|
| Argentina | 3,180 records, fine |
| Honduras, El Salvador | under 200 rows |
| **Vietnam** | **over the cap** |
| **China** *(even at 6 digits, 854442)* | **over the cap** |

For the large Asian manufacturing economies, start at **6 digits and one month**,
and be ready to go narrower still. For small economies a 4-digit heading over a
year is often fine.

### How to detect truncation

Count records, not rows:

- Use **distinct `Identificador`** where it is populated.
- Where `Identificador` is the literal `No disponible`, as in Argentine exports,
  count **rows where the first `Item` column equals 1**, since items are numbered
  from 1 within each record.

`scripts/inspect_download.py` does both automatically and exits 3 on a truncated
file. Run it after every download. It also warns when a file passes 27,000
records, because the next period is then likely to truncate.

### The pager saturates too

The grid pages at exactly 100 rows and the pager reads `1 de N`:

```js
document.querySelectorAll('tbody tr').length         // 100 on a full page
document.body.innerText.match(/(\d+)\s*de\s*(\d+)/)  // ["1 de 300", ...]
```

`1 de 300` is the ceiling, matching the 30,000 cap. It means "at or over the cap",
never how far over. Treat `1 de 300` as a tripwire: split the query before
downloading.

### Sizing a query with a tariff filter

A **4-digit HS heading over one month** is a good unit of work. Measured on
Argentina, heading 8544 for July 2026 came to 3,180 records, roughly a tenth of the
cap, in a 4 MB file. That leaves comfortable headroom even for a busy chapter.

The nomenclature field accepts a 4-digit prefix and turns it into a chip, so you do
not need a full national code. Since every country's system shares the first 6
digits of the Harmonized System, the same 4-digit heading works everywhere, which
makes it the natural way to slice a query that would otherwise truncate.

### What to do about it

Plan in **monthly** tramos for anything high volume, not yearly ones. A single
month of one country pair already reached 25,162 records, which is 84% of the cap.
If a month still truncates, split further by NCM chapter, customs office or
destination country, and record each slice as its own job in the manifest.

## Estimating a period's size

Estimating before downloading is unreliable, since the pager saturates. When a
period's size is unknown, download one month first, then extrapolate from its
actual row count.
