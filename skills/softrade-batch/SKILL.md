---
name: softrade-batch
description: Pull foreign-trade data out of Softrade (app.softrade.info) from a plain-language request such as "necesito las impo de mi empresa de este ano", resolving the company, country, report type and date range before touching the browser. Drives the user's own logged-in Chrome tab. Built for batches that are too long for one conversation: keeps a manifest.json on disk as the single source of truth so a run that dies halfway resumes from a fresh chat instead of restarting. Knows all 78 countries and which reports each one offers. Detects the silent truncation that hits any query over 30,000 customs records. Use whenever the user asks for imports or exports of a named company, asks to pull, export, resume or bulk-download Softrade data, mentions "importaciones detalladas", "exportaciones detalladas", a Softrade "consulta por parametros", says a previous Softrade run never finished, or wants trade data spanning more than one year or country.
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

**`scripts/...` and `references/...` in this file are relative to this skill's own
directory**, the one that holds this `SKILL.md` (Claude Code announces it as the
skill's base directory when the skill loads; installed as a plugin it sits under
the plugin cache, not in the user's project). Do not `cd` into it. Stay in the
user's project or working folder and prefix every script with the absolute base
directory, so each `python scripts/X.py ...` below really runs as:

```bash
python "<skill base dir>/scripts/run_state.py" next "C:/ruta/absoluta/al/RUN_DIR"
```

`RUN_DIR` and downloaded files are the opposite: they belong to the user's project,
not to the skill, so always pass them as **absolute paths** inside the user's
project or working folder. Never a relative path that could resolve inside the
skill directory: anything written under the plugin cache (manifest included) is
lost on the next plugin update or reinstall.

The scripts that read spreadsheets (`inspect_download.py`, `party_check.py`,
`merge_run.py`) need
`pandas`, `openpyxl` and, for old `.xls` files, `xlrd`. A missing one is an
environment problem, not a bad download (`inspect_download.py` says "missing
dependency" and leaves the manifest alone): ask the user to run
`pip install pandas openpyxl xlrd` (or `pip install -r requirements.txt` from a
checkout of the repo). The other scripts are standard library only.

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

**Accumulate what the user already told you. Never ask twice.** These four fields
arrive across several messages, not in one sentence. "Necesito las impo" pins the
direction; a later "detalladas" pins the variant. Treat the answers as a form you
are filling in, and ask only about fields that are still blank:

```
direccion = importaciones     <- from "las impo"
variante  = detalladas        <- from "detalladas"
empresa   = ?                 <- still missing, ask about THIS
pais      = ?                 <- still missing, ask about THIS
periodo   = ?                 <- still missing, ask about THIS
```

Re-asking something the user already said reads as not listening, and it costs a
round trip on every field. If a later message contradicts an earlier one, the
later one wins, but say out loud that you are changing it.

Rules:

- **Resolve relative dates against today and state them back.** "Este ano" means
  January 1 of the current year through today, not through December. Say the
  literal range you are going to use before starting.
- **Never assume the company name matches.** Softrade stores names as they appear
  in customs records, with suffixes, abbreviations and spelling that rarely match
  how the user says it. Search the entity filter first and show the user the
  candidates. Picking the wrong one silently returns a plausible, wrong dataset,
  which is worse than returning nothing.
- **Check the request is even answerable before planning.** Run
  `scripts/preflight.py` first: it reads `references/catalog.json` and returns a
  verdict without opening anything.

  ```bash
  python scripts/preflight.py --country ar --report "impo detalladas" \
      --by-company --from 2026-01 --to 2026-07
  ```

  It exits `0` OK, `1` WARN (usable with caveats), `2` IMPOSSIBLE (the report does
  not exist, cannot answer a by-company question, the dates are malformed or
  reversed, or the whole period is past the cutoff of a base that is frozen). Its
  `messages_es` lines are written to be relayed to the user verbatim. This is the
  fast path; the reference files below are the narrative behind each verdict, for
  when you need the detail.

  The catalog cutoffs are a snapshot from `meta.captured`, so a period past the
  cutoff of a live base is only a WARN: open the form and read the period it
  pre-fills, which is the real maximum. The report name resolves on an exact alias,
  or on the same words forgiving singular/plural, filler words and word order.
  Anything looser is not guessed: preflight answers "no reconozco el reporte X.
  ¿Quisiste decir A / B?", and you ask the user or pass the canonical id.

  What it catches, all of which otherwise look like a filter mistake after
  downloading: six Latin American countries name nobody on either side; Argentina
  names importers but not exporters; Paraguay's names (and Colombia Histórico's)
  are labelled *Probable* by Softrade (it does not say why; Paraguay's carry the
  RUC), and that word must reach the user; Brasil Detalladas, Mexico and
  Guatemala Detalladas are frozen in 2021. `plan_run.py` runs the same check and
  refuses to build a manifest for an impossible run, so a plan that survives is a
  plan that can be executed.
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
- **But a Cargas name is not automatically the buyer.** Customs reports name the
  importer of record. Cargas reports come from bills of lading, whose consignee
  can be a forwarder, a shipping line or a bank under a "TO ORDER" bill. Say so
  before ranking companies from Cargas, run `scripts/party_check.py` on the file to
  measure how much of it is logistics, and for the US keep `Incluir Masters` off.
  Detail in `references/cargas.md`.
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
  --importador "NOMBRE EXACTO S.A." \
  --label "research-q3"
```

`RUN_DIR` should be an absolute path in the user's project, not in a temp directory
nor in the skill's directory, since it has to outlive the session and plugin
updates. Downloads go to `RUN_DIR/downloads/`.

**Pass every filter to `plan_run.py`.** `--importador`, `--exportador`,
`--proveedor`, `--comprador`, `--ncm`, `--aduana`, `--pais-origen`, `--marca`. This is not
bookkeeping, it is the difference between a resumable run and a broken one.

Company filters must match the report's direction. Import reports take
`--importador` (the local company) and `--proveedor` (the foreign supplier);
export reports take `--exportador` and `--comprador` (the foreign buyer). A
mismatch exits `2` and names the right flag ("usá --X"). Reports that go both ways
(Otras Operaciones, Zona Franca, Transitos) are not checked.

Country, report and dates alone do not define a dataset. "Importaciones de
Argentina en 2024" is a different file for every importer. If the company you spent
Step 0 confirming lives only in the conversation, then the moment the chat is
summarized the run has lost it, and the next `next` hands you a job you cannot
reproduce. You would have to either ask the user again, which breaks the promise
that a run resumes on its own, or guess, which silently mixes two different
datasets across tramos of the same run.

`next` prints the filters back on every job, and `split` copies them into the
sub-jobs. If `next` says `filters (none: whole country/period)` on a job that was
meant to be about one company, the manifest is wrong: fix it before downloading.

**Softrade refuses any query longer than 12 months**, so a multi-year request is
always several jobs. `plan_run.py` splits on `--max-months` (default 12) to keep
every job legal. This is a hard limit of the form, not a heuristic.

### Plan wide, narrow only when Softrade complains

**Do not pre-split into months.** Start with the widest job the form allows and
escalate only on evidence. Splitting up front is the mistake that turns one
download into twelve, of which eleven come back empty:

1. **Ask for the whole period, up to 12 months, as one job.** This is the default
   and it needs no flag.
2. **If "consulta demasiado extensa" fires, or `inspect_download.py` exits 3,**
   split that job by month:
   `python scripts/run_state.py split RUN_DIR --job N`
   The original job is marked `split`, the monthly jobs are appended, and every
   index you already handed out still points at the same job.
3. **If a single month still truncates,** period splitting is exhausted. Narrow
   the query itself (an NCM-SIM code, an aduana, a country of origin) and plan
   those as separate jobs.

The only case for splitting up front is a query you already know is enormous: a
whole country's imports with no company filter, where one month of a single busy
country pair already reached 25,162 records against the 30,000 cap. A named
company's imports is not that case. One real run of a company's January-July came
back as **2 operations**, and pre-splitting it would have produced seven downloads
to find them.

**One period, one file.** When the whole request fits in one job, the user gets a
single consolidated Excel. Monthly files are an internal mechanism for when
Softrade forces segmentation, never the default deliverable. If a run did get
segmented, say so when handing over and merge the files with
`scripts/merge_run.py` (Step 3) rather than leaving the user several files to
combine by hand.

Tell the user the job count before you start. Forty jobs is a multi-session run and
they should know that going in.

When a period's size is unknown, download one month and extrapolate from its real
row count instead of guessing.

### Which reference answers which question

| Question | File |
|---|---|
| Is this country/report/period even answerable? (machine-readable, one call) | **`scripts/preflight.py`** over `references/catalog.json` |
| Does this report have FOB / CIF / Incoterm / Marca? Is the data still alive? | **`references/fields-matrix.md`** |
| Which reports does this country offer at all? | `references/catalog.md` |
| Does it name the importer, the exporter, the counterparty? | `references/entities-latam.md`, `references/entities-world.md` |
| What are the exact column names and the rows-per-record ratio? | `references/columns-latam.md`, `references/columns.md` |
| Bill of lading reports (the only company data for BR, MX, US) | `references/cargas.md` |
| What has been verified versus only cataloged? | `references/coverage.md` |

`catalog.json` ships ready to use; never regenerate it during a run. It is built
by `tools/build_catalog.py`, which lives in the repo checkout, outside this skill
directory, so an installed skill cannot run it. When a `references/*.md` fact
changes, the maintainer transcribes it into that builder and rebuilds the catalog
from the repo root. The markdown stays the human-readable narrative.

**`fields-matrix.md` is the one to open first when the request names a field.**
"Necesito el incoterm" narrows the possible countries to a handful, and knowing that
before planning saves a download that was never going to carry the column.

Check these before promising anything: only 8 countries have Detalladas data at
all, several have imports but no exports, and report families such as Cargas, Zona
Franca and Transitos exist in only a handful of countries.

**Say it when a base is frozen.** Several are stuck in 2021 or 2024. Asking one of
them for recent data returns zero rows and looks exactly like a filter mistake, so
warn the user before downloading, not after.

## Step 2: the download loop

Repeat until `next` reports the run is complete:

1. `python scripts/run_state.py next RUN_DIR` to get one job. One, not the list.
   Add `--json` if you want the job as a structured object instead of prose;
   `status --json` works the same way.
2. **List the download directory now**, before touching anything. You need a
   "before" listing to prove later that a new file appeared.
3. Set the filters in the browser for that job, per `references/site-flow.md`.
   The Periodo fields need the calendar widget, `form_input` on them fails
   silently, and **calendar clicks have applied even when the tool reported a
   timeout**, so read the field back and retry only if its value did not change.
   If the job carries an NCM-SIM code, **count the chips**: the field spawns a
   phantom empty chip that breaks the search.
   **Type every filter with real key events** (click the field, type, Enter).
   A value set from JavaScript paints a chip but does not count, and Softrade
   refuses a search with no counting filter: a yellow toast, "Debe ingresar al
   menos un parámetro de búsqueda", shows for a few seconds and the page stays on
   the form. Read it wrong and every job in the batch looks like "sin datos".
   Chips also survive leaving the report and pressing Reset, so clear the previous
   job's chips before typing the new ones.
4. Fire the search, then **check the page for "demasiado extensa" before doing
   anything else**. If it fired, the query is over the 30,000 record cap and the
   Excel button will download nothing at all. Do not narrow it by hand: mark the
   job with `run_state.py split` and take the monthly jobs from `next`.
   Then **verify against the results sidebar**, which is the only place that
   reports the period and entity actually queried. Do not verify against the form,
   and do not use a screenshot where JS or `read_page` will do.
5. Trigger the export from the Descargas panel, by clicking the `ion-img` itself.
   `find` returns tooltips here, and clicking a tooltip silently does nothing.
   The plain `.click()` is not reliable on its own and the icons render clipped;
   if no file lands, fall back to a coordinate click inside the icon's **visible**
   area, per `site-flow.md`.
6. Confirm the download actually happened by **listing the download directory
   again** and diffing against the listing from step 2. Softrade moves its data
   over a WebSocket, so there is no HTTP request to watch, and the screen says
   "descargando" whether or not a file was ever produced. Neither is evidence.
   The filesystem is.
7. **Rename the file immediately.** Exports are named
   `detalle_{CC}{report}_{timestamp}.xlsx` with no period in the name, so two
   tramos of the same report are indistinguishable. The timestamp is not a usable
   date either (0-indexed month, and the day slot appears to be the weekday). Rename to something like
   `ar_importDetalladas_2026-01_2026-07.xlsx` before doing anything else.
8. **Inspect and record in one command.** Do not transcribe counts by hand:

```bash
python scripts/inspect_download.py RUN_DIR/downloads/FILE --record RUN_DIR --job 7
```

This reads the file, counts rows and records, and writes both into the manifest
with the right status: `done` for real data, `skipped` for a genuinely empty
period, `failed` for a truncated file or an HTML login page. **It exits 3 when
the file is truncated**, which happens silently whenever a query passes 30,000
customs records.

Typing `run_state.py done --rows` yourself is the fallback for when the file is
not machine-readable, and it is where wrong numbers come from: a real run recorded
`1` where the file held `16`. If you must use it, pass `--records` too.

9. If the job came back truncated, split it and carry on:

```bash
python scripts/run_state.py split RUN_DIR --job 7
```

The other manual transitions, for cases `inspect_download.py` cannot judge:

```bash
python scripts/run_state.py fail RUN_DIR --job 7 --note "el filtro de pais no cargo"
python scripts/run_state.py skip RUN_DIR --job 7 --note "sin datos para el periodo"
```

A period with genuinely no data is `skip`, not `fail`. `fail` means retry later;
`next` hands failed jobs back after the pending ones are exhausted.

Before resuming a run, and after any hand edit of a manifest, run
`python scripts/run_state.py check RUN_DIR` (`--json` gives `{ok, jobs, problems,
warnings}`). It validates every job against `catalog.json` without touching
anything: non-canonical reports, reversed or invalid dates, spans over 12 months,
duplicate jobs, `split` jobs with no children, bad attempts. It exits `1` on any
problem; fix those before the next `next`.

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

**Always report rows and operations as two numbers.** They are not the same thing
and users read whichever one you give them as "how much data I got". One real run
was **17 rows but only 2 customs operations**. Quoting 17 alone overstates it by
eight times. `status` prints both plus the ratio; pass both on.

**Verify a segmented run that came back mostly empty.** If the run was split into
months and most of them were skipped for no data, the empties are indistinguishable
from a filter that silently failed. When the surviving volume is small enough to
fit one query, run the whole period once as a single job and compare:

- same operation count → the empty months were genuinely empty, say so and close.
- more operations than the segments added up to → **the segmented run was wrong.**
  A filter was not applying on some tramos. Investigate before handing anything
  over.

This costs one query and it is the only thing that distinguishes "no data" from
"the query was broken and nobody noticed".

**Merge before handing over.** When the run produced more than one file (a split
job, or several years or countries), run
`python scripts/merge_run.py RUN_DIR` (prefixed with the skill base dir, `RUN_DIR`
absolute, as in "Before starting"). It writes `RUN_DIR/consolidado.xlsx`: one sheet
per country/report, plus `origen_job` / `origen_periodo` columns on every row.
Split parents are left out, since their months belong to their children. It
refuses (exit `1`, nothing written) while jobs are pending or failed;
`--allow-partial` merges the `done` ones anyway and the summary says `PARCIAL`, and
so must your hand-over. It also refuses when files of the same country/report have
different columns, when a file is missing from the manifest's download directory,
unreadable or an HTML page, or when there is nothing to merge. It drops repeated
rows only between jobs whose periods overlap, and prints rows and operations
recounted from the merged data: quote both. Exit `3` means the file was written but
some segments were flagged with `!` (empty or far smaller than their siblings, a
mostly-empty split, or a file whose row count no longer matches the manifest): do
the single-job comparison above before handing anything over. `--out X.xlsx` or
`--out X.csv` (absolute path) writes elsewhere; a `.csv` only takes a single
country/report. `--json` gives the summary as `{ok, output, partial, groups, jobs,
warnings, flagged, ...}`.

## Learning a new report type

If the user asks for a report not yet documented in `references/`, do one guided
pass with them: walk the flow once, capture the filter element names with
`read_page`, capture the export request pattern with `read_network_requests`, then
run `inspect_download.py` on the result and append what you learned to
`references/columns.md` and `references/site-flow.md`. Document it once, so the
next run does not have to rediscover it.

`references/coverage.md` tracks which reports have been verified that way and which
are still only catalog entries, ordered so the next unmeasured **report family**
comes before the next unmeasured country. Read it before promising a column layout,
and check its box after appending what you measured.
