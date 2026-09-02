---
name: softrade-batch
description: Pull foreign-trade data out of Softrade (app.softrade.info) from a plain-language request such as "necesito las impo de mi empresa de este ano", resolving the company, country, report type and date range before touching the browser. Drives the user's own logged-in Chrome tab. Built for batches that are too long for one conversation: keeps a manifest.json on disk as the single source of truth so a run that dies halfway resumes from a fresh chat instead of restarting. Knows all 78 countries and which reports each one offers. Detects the silent truncation that hits any query over 30,000 customs records, and tracks the account's monthly row quota, which Softrade displays nowhere. Use whenever the user asks for imports or exports of a named company, asks to pull, export, resume or bulk-download Softrade data, mentions "importaciones detalladas", "exportaciones detalladas", a Softrade "consulta por parametros", says a previous Softrade run never finished, or wants trade data spanning more than one year or country.
---

# Softrade batch downloads

Downloading one Softrade report is easy. Downloading forty is where runs die: each
query costs a page of navigation, a filter check and a download confirmation, and a
long enough batch fills the context window. When the conversation gets summarized,
the thing that gets lost is exactly the thing that matters, which tramos already
landed on disk. The run then looks stuck or silently repeats work.

This skill fixes that by keeping the run state in a file instead of in the chat.

## The rule that makes this work

**The manifest on disk is the truth. The conversation is disposable.**

Never track progress in your head or in prose. After every single download, write
the result to the manifest immediately. If the chat dies mid batch, a new one runs
`run_state.py next` and continues at the right place with no re-reading of history.

## Before starting

Softrade holds its session per tab. A tab you open yourself will land on the login
screen even when the user has another tab logged in. **Never type the user's
credentials.** Ask the user to log in themselves in the tab you opened, and to say
when they are done.

If the session expires mid run, downloads start returning an HTML login page
instead of a spreadsheet. `inspect_download.py` detects this and reports
`NOT DATA`. Stop, mark the job failed, and ask the user to log back in.

## Step 0: turn the request into a query

Most requests arrive as a sentence, not as parameters: *"necesito las impo de mi
empresa, <nombre>, de este ano"*. Resolve it before opening anything.

Four things have to be pinned down:

| From the request | What you need |
|---|---|
| "las impo" / "las expo" | report type, and whether the detailed variant is wanted |
| the company name | the entity as Softrade actually spells it, plus whether it is the importer or the exporter side |
| implied by the company | the country whose database to query |
| "de este ano" | a concrete date range |

Rules:

- **Resolve relative dates against today and state them back.** "Este ano" means
  January 1 of the current year through today, not through December. Say the
  literal range you are going to use before starting.
- **Never assume the company name matches.** Softrade stores names as they appear
  in customs records, with suffixes, abbreviations and spelling that rarely match
  how the user says it. Search the entity filter first and show the user the
  candidates. Picking the wrong one silently returns a plausible, wrong dataset,
  which is worse than returning nothing.
- **Check the request is even answerable before planning.** Consult
  `references/entities-latam.md` first. It records, per country and per direction,
  whether the form can filter by company at all, and how current the data is. Six
  Latin American countries name nobody on either side. Argentina names importers
  but not exporters. Paraguay's names are labelled *Probable*, meaning inferred,
  and that word must reach the user. Brasil Detalladas, Mexico and Guatemala
  Detalladas are frozen in 2021, so any request for recent data there returns
  nothing and looks like a filter mistake. Say all of this before planning, not
  after downloading.
- **China, Japan, India, Taiwan, Korea, Thailand, Israel, Australia, New Zealand
  and all of Europe except Ukraine name nobody.** See `references/entities-world.md`.
  Roughly, the wealthier the country the less it publishes, which is the opposite of
  what users assume. When someone asks who imports into China, the answer is that
  Softrade cannot say, but the `Proveedor` column of an importing country names the
  Chinese exporter, which is usually the real question.
- **When the obvious report names nobody, check the Cargas family.** Brasil and
  Mexico look anonymous through Importaciones and are not: Mexico's Cargas Totales
  names both importer and supplier and runs to May 2026, and Brasil's Cargas
  Maritimas carries consignee and shipper with contact details. Never tell a user a
  country has no company data without checking its other reports.
- **The company's country is not always the query country.** A user asking for
  "las impo de mi empresa" wants the country where the company imports, which is
  usually where it operates, but confirm rather than infer when the name carries a
  country in it.
- **Watch the importer/exporter direction.** "Las impo de X" means rows where X is
  the importer, which is a different filter from rows where the goods merely went
  to that country.

Restate the resolved query in one line and get a yes before building the manifest:

> Importaciones detalladas, Argentina, importador <NOMBRE EXACTO S.A.>,
> del 2026-01-01 al 2026-07-31. Un solo tramo. Confirmas?

For a single short range this is one job and the manifest is near-pointless
overhead, but build it anyway. It costs one command and it is what makes the run
resumable if the request later grows to five years and four countries.

## Step 1: plan the run

With the query resolved and confirmed, build the manifest once, up front. Do not compute date splits by hand as you
go, that is where drift creeps in.

```bash
python scripts/plan_run.py --out RUN_DIR \
  --country ar --country br \
  --report imports_detailed \
  --from 2023-01 --to 2025-12 \
  --label "research-q3"
```

`RUN_DIR` should live with the user's project, not in a temp directory, since it has
to outlive the session. Downloads go to `RUN_DIR/downloads/`.

**Use `--max-months 1` for anything high volume.** Softrade truncates at 30,000
customs records with only an on-screen notice, and one month of a single busy
country pair already reached 25,162. The 12-month default only suits narrow
queries, such as one company's imports.

Tell the user the job count before you start. Forty jobs is a multi-session run and
they should know that going in.

**Check quota before starting, and keep checking.** Softrade accounts carry a
monthly row allowance, commonly 200,000 rows per calendar month, and the
application shows consumption nowhere at all. The manifest is the only place it
gets counted:

```bash
python scripts/run_state.py quota RUN_DIR [--quota 200000]
```

Run it **before planning a run** and again whenever the user asks how things are
going. `run_state.py done` also prints a warning on its own once the month passes
50% of the allowance, and a STOP once it passes 80%.

**A STOP means stop.** Do not start another tramo. Tell the user how much is left
and let them decide. Silently spending a month's allowance in one afternoon is a
worse failure than a run that pauses.

When a period's size is unknown, download one month and extrapolate from its real
row count instead of guessing.

See `references/catalog.md` for all 78 countries and exactly which reports each one
offers, `references/entities-latam.md` for who is named and how current the data is across
Latin America, and `references/columns-latam.md` for the measured column layout,
row and record counts of every Latin American import report,
`references/entities-world.md` for the same coverage question across Asia, Africa,
Oceania and Europe, and `references/cargas.md` for the bill of lading reports,
which are the only place Brasil, Mexico and the United States name companies. Check it before promising anything: only 8 countries have Detalladas data
at all, several have imports but no exports, and report families such as Cargas,
Zona Franca and Transitos exist in only a handful of countries.

## Step 2: the download loop

Repeat until `next` reports the run is complete:

1. `python scripts/run_state.py next RUN_DIR` to get one job. One, not the list.
2. Set the filters in the browser for that job, per `references/site-flow.md`.
   The Periodo fields need the calendar widget, `form_input` on them fails
   silently.
3. Fire the search, then **check the page for "demasiado extensa" before doing
   anything else**. If it fired, the query is over the 30,000 record cap, the Excel
   button will download nothing at all, and you must narrow the query and search
   again. Then **verify against the results sidebar**, which is the only place that
   reports the period and entity actually queried. Do not verify against the form,
   and do not use a screenshot where JS or `read_page` will do.
4. Trigger the export from the Descargas panel, by clicking the `ion-img` itself.
   `find` returns tooltips here, and clicking a tooltip silently does nothing.
5. Confirm the download actually happened by **listing the download directory**
   and checking a new file appeared. Softrade moves its data over a WebSocket, so
   there is no HTTP request to watch, and the screen says "descargando" whether or
   not a file was ever produced. Neither is evidence. The filesystem is.
6. **Rename the file immediately.** Exports are named
   `detalle_{CC}{report}_{timestamp}.xlsx` with no period in the name, so two
   tramos of the same report are indistinguishable. Rename to something like
   `ar_importDetalladas_2026-01_2026-07.xlsx` before doing anything else.
7. `python scripts/inspect_download.py RUN_DIR/downloads/FILE` to confirm the file
   holds rows and the expected columns. **It exits 3 when the file is truncated**,
   which happens silently whenever a query passes 30,000 customs records. Never
   mark a truncated file done: split that job into shorter periods and redo it.
8. Record the outcome and move on:

```bash
python scripts/run_state.py done RUN_DIR --job 7 --file ar_imp_2024.xlsx --rows 15230
python scripts/run_state.py fail RUN_DIR --job 7 --note "el filtro de pais no cargo"
python scripts/run_state.py skip RUN_DIR --job 7 --note "sin datos para el periodo"
```

A period with genuinely no data is `skip`, not `fail`. `fail` means retry later;
`next` hands failed jobs back after the pending ones are exhausted.

## Context discipline

These are the habits that decide whether a long run finishes:

- **Never read the results grid.** The spreadsheet already has the data. Reading
  the on-screen table costs thousands of tokens and adds nothing.
- **Screenshots only to make a decision**, never to confirm something
  `read_page` can confirm.
- **Batch browser actions.** Use `browser_batch` for predictable sequences such as
  set filter, set filter, click search, rather than one call per step.
- **Do not summarize progress in prose** between jobs. A one-line confirmation is
  enough, the manifest carries the detail.

When you notice the conversation getting long, stop cleanly: run
`run_state.py status RUN_DIR`, report the counts, and tell the user to open a fresh
chat and say "seguí la corrida de Softrade en RUN_DIR". Stopping deliberately at a
recorded boundary beats being cut off at a random one.

## Step 3: closing out

When no jobs remain pending, run `status` and report done, skipped and failed
counts, plus where the files are. If any job failed after repeated attempts, say so
explicitly with the note, rather than presenting the run as complete.

## Learning a new report type

If the user asks for a report not yet documented in `references/`, do one guided
pass with them: walk the flow once, capture the filter element names with
`read_page`, capture the export request pattern with `read_network_requests`, then
run `inspect_download.py` on the result and append what you learned to
`references/columns.md` and `references/site-flow.md`. Document it once, so the
next run does not have to rediscover it.
