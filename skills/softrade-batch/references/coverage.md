# Verification coverage tracker

What has actually been confirmed by downloading a real file, versus what is only
known from the catalog. Update this file whenever a new report gets verified, see
"Learning a new report type" in `SKILL.md`. Do not check a box from reading the
form; check it only after `inspect_download.py` has run against a real export.

**The run is tracked in two sub-manifests**, `corrida-catalogo/split-claude/` and
`corrida-catalogo/split-chatgpt/`, carved by `tools/split_run.py` so two accounts
can work in parallel. `run_state.py next corrida-catalogo/split-claude` (or
`split-chatgpt`) hands you the next box of that half; `run_state.py check` on the
same directory validates it. `split_run.py` refuses to overwrite a sub-manifest
that already has progress unless you pass `--force`. The master
`corrida-catalogo/manifest.json` (112 jobs, one per country/report, in the Pass
A→B→C order below) is the reference, not the live checklist: sub-run results are
merged back into it by hand at the end. This file is the *why* behind that order
and the field notes per box; the sub-manifests are the *state*. Keep them in step:
when you measure a report, record it against its sub-manifest job and tick it here.

**Exception: the second survey pass of 2026-09-18** ran outside those manifests
(`runs/cobertura-2026-09-18/`, not versioned, no manifest of its own). It read the
pre-filled period of each form and downloaded a small sample (heading 8544 where
the form takes it, one month) where it could. Its results live in `catalog.json` (entries carrying
`"surveyed": "2026-09-18"`), in `fields-matrix.md` and in the boxes ticked below,
but the matching jobs in `corrida-catalogo/manifest.json` are still `pending`. It
kept the column **count**, cutoff and notes, not the column names.

The boxes for Vista Global, Consulta Regional and the AR Acumulados / Empresas
modules have no job in any manifest: they are cross-country views or modules, not
country/report pairs, so they are tracked only here, by hand.

## The three layers

1. **Catalog**: which reports exist per country. **Complete**, 78 countries
   (`catalog.md`).
2. **Entity filters**: whether each report can filter by company, and how current
   the data is. **Complete**, import and export sides, all 78 countries
   (`entities-latam.md`, `entities-world.md`).
3. **Column layout**: what a real downloaded Excel contains: column count, names,
   the row/record ratio, quirks like duplicated columns or a literal
   `No disponible`. **This is the layer that is mostly open.** Everything below
   tracks layer 3.

Layer 3 has two outputs, and a new measurement must land in both:
`columns-latam.md` (or a new `columns-<region>.md`) for the full column list, and
**`fields-matrix.md`** for the one-line answer on vitality and the key fields:
FOB, CIF, Importador, Proveedor, Incoterm, Marca. The matrix is what gets consulted
before promising a field to a user; the column list is what gets consulted while
building the query. `catalog.json` has 32 reports with a measured column count;
the matrix shows 30 of them (AR Importaciones and AR Otras Operaciones are the two
left out; they have no matrix row, and their columns are in `columns.md` and
`catalog.md`).

Layer 3 needs a live browser session against Softrade (`site-flow.md`).
It cannot be done from the catalog alone.

## How much precision the vitality check needs

**Very little. Do not hunt for the exact cutoff month.**

The only question a user ever asks is whether the data is usable *now*: is there
something from last month, or is this one of the bases frozen five years ago? That
is a yes/no, and one or two searches answer it.

The cheap procedure, per report:

0. **Read the pre-filled period.** Both Periodo fields arrive holding the newest
   period the report offers, so the vitality answer is often visible before any
   search at all: `05/2026` means current, `12/2021` means frozen. Verified on MX
   Cargas Totales, which read `05/2026` matching its header exactly.
1. Only if you need to confirm rows exist, search that period. Data? **Current, done.**
2. Empty? Step back one month and search again. Data? **Current, done.**
3. Still empty? Record it as **"sin datos recientes"** and move on. Do not binary
   search backwards through the year to find where the data starts.

Two searches, then a verdict. A report that has nothing in the last two months is
not current, and *how* stale it is beyond that almost never changes what anyone
does with it. Chasing the exact boundary costs many round trips and buys nothing.

The one exception is when the user specifically asks for a historical period. Then
you are testing that period, not the cutoff.

## Breadth before depth

Softrade is not one database with 78 country skins. It is **14 distinct report
families**, and a family's form, filter set and column layout are properties of the
family, not of the country. Argentina's Importaciones tells you nothing about
Uruguay's Tránsitos.

So the ordering below is **one representative country per family first**, then fill
in countries within a family. Measuring a second country of an already-known family
teaches far less than the first country of an unknown one, and today **5 of the 14
families have never been opened at all.**

## The family matrix

| # | Family | Countries offering it | Measured | Status |
|---|---|---|---|---|
| 1 | Importaciones (standard) | all 78 | 15 LatAm countries + AR | partial |
| 2 | Importaciones Detalladas | AR BR GT NI DO RU TR | AR GT NI DO | partial |
| 3 | Exportaciones (standard) | 77 (not KE) | AR; BO CL CO EC (2026-09-18) | partial |
| 4 | Exportaciones Detalladas | AR BR GT NI DO RU TR | AR | partial |
| 5 | Histórico Imp. / Exp. | BO CO EC HN VE PH ID VN AU CA KE | EC Imp. (2026-09-18); BO CO Imp./Exp. and EC Exp. form only | partial |
| 6 | Cargas Marítimas Ing./Sal. | BR PA US | BR Ingresos; BR Salidas (2026-09-18) | partial |
| 7 | Cargas Ingresos / Salidas | EC PE VE GT | EC Ingresos (2026-09-18) | partial |
| 8 | Cargas Totales Ing./Sal. | MX | no | **never opened** |
| 9 | Cargas Aéreas / Terrestres | UY | no | **never opened** |
| 10 | Cargas Histórico Ing./Sal. | BR | BR Ingresos (2026-09-18); Salidas form only | partial |
| 11 | Otras Operaciones | AR MX | AR (ratio only) | partial |
| 12 | Zona Franca / Zona Libre | CR (Franca), PA (Libre Ing./Sal.) | no | **never opened** |
| 13 | Tránsitos | UY | no | **never opened** |
| 14 | Totalizadas | ES | no | **never opened** |
| no | Normativa | UY | no | never opened, **not trade data** |
| no | Vista Global | cross-country | no | **never exported** |
| no | Consulta Regional | cross-country | no | **never exported**, aggregated |

`Normativa` is regulations, not customs records. One look to confirm it carries no
exportable dataset, then drop it from this tracker for good.

## Pass A: one country per unknown family

The whole point of this pass is **one file per family**, cheapest representative,
to learn the shape. Do not chase countries here.

Representatives are picked so one login session covers several boxes: **Ecuador**
alone opens families 5 and 7, **Uruguay** opens 9 and 13, and **Brasil** opens 10
next to the Cargas Marítimas layout already measured.

- [x] **F3 · Exportaciones (standard)** → AR. **DONE 2026-09-03**, 9 columns, no
      `Exportador` column at all. See `columns.md`.
- [x] **F3 second country** → EC. **DONE 2026-09-18**, 45 columns, `Exportador`
      and `Comprador` both present (not `No disponible` as in AR Exportaciones
      Detalladas), plus Incoterm, Marca, Modelo, Bill of Lading and Estado de
      Declaración. Data through 06/09/2026. The 2026-09-03 attempt had come back
      empty because Softrade refused every search without a typed filter; see
      "Softrade refuses a search without a filter" in `site-flow.md`. The same pass
      also measured BO (23), CL (29) and CO (28) Exportaciones; see B3.
- [x] **F5 · Histórico Importaciones** → EC Ecuador. **DONE 2026-09-18**, 48
      columns, the same count as the current Importaciones but **not the same
      layout**: it adds `Refrendo`, `Nro. DAU`, `Base Imponible U$S`, `Advalorem`,
      `Aforador` and `Actividad Principal Importador`, and has no `Incoterm`,
      `Modelo`, `Año producido` or `Bill of Lading`. **Frozen at 12/2017**: it
      is the older data, not a copy of the current base. The Excel carries
      `Importador` and `Proveedor`, but the form cannot filter by `Proveedor`.
      Same pass, form only: BO Histórico frozen 09/2023 and anonymous; CO Histórico
      frozen 12/2021 with *Probable* names on both sides.
- [ ] **F5 · Histórico Exportaciones** → EC. Form read 2026-09-18 (frozen 12/2017,
      `Exportador`, no counterparty filter); no file downloaded yet.
- [x] **F7 · Cargas Ingresos** → EC. **DONE 2026-09-18**, 33 columns, data through
      31/07/2026. A manifest, like Marítimas, but **not the same layout** (33 vs 34
      columns): no tariff-code field, so it filters by Descripción or Marcas; carries
      BL Master, Consolidador and the consignee's RUC. In the sample, 1 in 3
      consignees was a logistics firm.
- [ ] **F7 · Cargas Salidas** → EC. Not surveyed.
- [ ] **F8 · Cargas Totales Ingresos** → MX. **Highest value in this pass:** the
      only place México names companies, both sides, current to 31/05/2026.
- [ ] **F8 · Cargas Totales Salidas** → MX, same session.
- [ ] **F9 · Cargas Aéreas** → UY. Air manifests exist nowhere else.
- [ ] **F9 · Cargas Terrestres** → UY. Land manifests exist nowhere else.
- [x] **F10 · Cargas Histórico Ingresos** → BR. **DONE 2026-09-18**, 10 columns,
      frozen 01/2020. What "Histórico" changes: it is built like a declaration
      (Aduana, Estado, 8-digit NCM, every transport mode), not a bill of lading.
      `Consignatario` only, no counterparty, and 99% of consignees in the sample
      were companies, so it works as a real importer field.
- [ ] **F10 · Cargas Histórico Salidas** → BR. Form read 2026-09-18 (frozen
      07/2018, same format as Ingresos, names the `Shipper`); no file yet.
- [ ] **F12 · Zona Franca** → CR Costa Rica. Filters unknown, columns unknown.
- [ ] **F12 · Zona Libre Ingresos** → PA Panamá. Filters unknown.
- [ ] **F12 · Zona Libre Salidas** → PA.
- [ ] **F13 · Tránsitos** → UY. Goods in transit, a different record type from a
      customs declaration. Uruguay only.
- [ ] **F14 · Totalizadas** → ES. Aggregated, so **check whether it even offers an
      Excel export** before planning around it.
- [ ] **F11 · Otras Operaciones, full column list** → AR. Row/record ratio is known
      (25 rows / 12 records, one code, one month, `site-flow.md`) but the column
      listing never made it into `columns.md`.
- [ ] **Normativa** → UY. One look, confirm it is not a dataset, then delete its
      row from the matrix above.
- [ ] **Vista Global** → `/home/formulario/01/global`. Cross-country, never
      exported.
- [ ] **Consulta Regional** → `/home/formulario/01/regional`. Aggregated by entity
      and year; may offer no Excel at all. Confirm which.
- [ ] **AR Acumulados and Empresas modules**, seen in the site, never opened.
      Establish whether they are reports or navigation.

Completing Pass A means **every family in Softrade has one measured example**, and
any future request can be answered with "here is the shape of that report" instead
of a guess.

## Pass B: countries that name companies

Only now go wide, and only where the data can answer a company question. Everything
here is a known family, so each file is cheap.

### B1 · Detalladas, the remaining 6 countries

Transaction-level data exists in only 8 places total.

| Country | Names companies | Data cutoff | Priority |
|---|---|---|---|
| NI Nicaragua | yes, both sides | 31/07/2026 | **high** |
| DO Rep. Dominicana | yes, both sides | 31/07/2026 | **high** |
| RU Rusia | yes, both sides | 31/12/2023 | medium |
| TR Turquía | yes, both sides | 31/12/2023 | medium |
| BR Brasil | no | 30/11/2021 | low |
| GT Guatemala | no | 31/12/2021 | low |

- [ ] NI Importaciones + Exportaciones Detalladas
- [ ] DO Importaciones + Exportaciones Detalladas
- [ ] RU Importaciones + Exportaciones Detalladas
- [ ] TR Importaciones + Exportaciones Detalladas
- [ ] BR Importaciones + Exportaciones Detalladas (cheap to confirm while in BR
      for family 10)
- [ ] GT Importaciones + Exportaciones Detalladas

### B2 · Cargas, the remaining countries

Filters are documented for every row (`cargas.md`); **column layouts are not.**

| Country | Report | Names | Cutoff | Priority |
|---|---|---|---|---|
| US Estados Unidos | Cargas Marítimas Ing. | Consignatario, Shipper | 31/07/2026 | **high** |
| PE Perú | Cargas Ingresos | Consignatario, Shipper | 22/08/2026 | medium |
| PA Panamá | Cargas Marítimas Ing. | Consignatario only | 31/07/2026 | medium |
| VE Venezuela | Cargas Ingresos | Consignatario, Shipper | 31/08/2025 | low |
| UY Uruguay | Cargas Marítimas | Consignatario, Remitente | 11/07/2024 | low |
| GT Guatemala | Cargas Ingresos | Consignatario, Shipper | 30/09/2019 | low (stale) |

- [ ] US Cargas Marítimas Ingresos (watch `Incluir Masters`, see `cargas.md`)
- [ ] PE, PA, VE, UY, GT: whichever Cargas variant each offers
- [x] BR Cargas Marítimas Salidas, **DONE 2026-09-18**: 32 columns, frozen
      11/2023, `Shipper` as exporter and `Consignatario` as counterparty, plus
      Notify and Forwarder. In the sample, 2 in 3 consignees were logistics firms,
      not the buyer.
- [ ] Salidas counterparts for PA, US

### B3 · Export-side columns, Latin America

Import-side columns are measured for all 19 (`columns-latam.md`). On the export
side, Argentina was measured 2026-09-03 and BO, CL, CO, EC on 2026-09-18 (column
count only; see `fields-matrix.md`). The 8 countries naming both sides matter
most, since they answer "who does this exporter sell to":

- [x] BO, CO, EC: Exportaciones, **DONE 2026-09-18** (23, 28, 45 columns).
      `Comprador` present in all three.
- [ ] CR, NI, PA, DO: Exportaciones, columns + `Comprador` behavior
- [x] CL: Exportaciones, **DONE 2026-09-18**, 29 columns, no counterparty.
- [ ] UY, VE: Exportaciones, columns (no counterparty named)
- [ ] PY, Exportaciones (*Probable Exportador*, confirm the same caveat as the
      import side)

### B4 · Asia, Africa and Ukraine

The 17 countries outside Latin America that name a company on at least one side.
Zero column layouts exist for any of them.

Asia (`entities-world.md`): BD (imports only), PH, ID, KZ, PK, LK, UZ, VN
RU and TR are covered in B1.

- [ ] BD, PH, ID, KZ, PK, LK, UZ, VN: Importaciones + Exportaciones

Africa: ET, KE (imports only), LS, NG, UG, ZW

- [ ] ET, LS, NG, UG, ZW: Importaciones + Exportaciones
- [ ] KE: Importaciones (no export report exists)

Europe: only Ukraine names anyone.

- [ ] UA: Importaciones + Exportaciones

**Order within B4:** Vietnam and Pakistan first, both current, both sides, no
known quirks, to get a clean baseline before the messier ones. Vietnam also
carries Histórico, so pair it with family 5 if EC surfaced anything odd.

## Pass C: anonymous countries

These can only answer product, flow and price questions, never company questions.
One column pass each so the catalog is complete, done last.

- [x] CL: export side, **DONE 2026-09-18** (see B3)
- [ ] PY: export side (import already measured)
- [ ] SV, HN, PR: both sides anonymous, thin files (8-11 columns, quick)
- [ ] MX, BR: Importaciones / Exportaciones proper (Cargas is the real data). BR
      Exportaciones form read 2026-09-18: anonymous statistics, filters by Puerto
      and Estado, data through 31/08/2026.
- [ ] CN, KR, IN, IL, JP, TH, TW: Asia, both directions
- [ ] EG, MA, ZA: Africa, both directions
- [ ] AU, NZ: Oceania, both directions
- [ ] Europe: sample **one** EU-block country (e.g. DE), since all 28 non-Spain,
      non-Ukraine members reportedly share one filter set and cutoff. Confirm that
      assumption on one country rather than running all 28. Then GB separately
      (Código SA and USD, not the EU block). Spain needs both Importaciones and
      Totalizadas, since they behave oppositely (`entities-world.md`).

## How to work through this

1. Take the next unchecked box in **Pass A**. Only start Pass B once Pass A has no
   boxes left, since a new family teaches more than a new country.
2. Follow `site-flow.md` for the mechanics: flag menu, calendar widget for Periodo,
   the 12-month ceiling, JS `.click()` on `ion-img.imgBotonDescarga`, filesystem
   check, never the results grid.
3. Keep each verification query **deliberately tiny**: one month, one NCM code if
   the form allows it. This pass is measuring column layouts, not gathering data,
   so there is no reason to pull a big file.
4. Run `inspect_download.py` on the file.
5. Append the measured column list to `columns.md` (Argentina today, growing) or a
   new `columns-<region>.md` following the format of `columns-latam.md`, **add the
   row to `fields-matrix.md`**, and check the box here. A measurement that is not
   in the matrix is a measurement nobody will find.
6. If a report behaves differently from what `site-flow.md` documents, such as a filter in
   a different place, a Periodo field that is free text instead of a calendar,
   Puerto appearing where it did not in Argentina, add a note to `site-flow.md`
   rather than assuming it matches.
7. When a family turns out to be structurally different from the customs-declaration
   reports (Cargas already is; Zona Franca, Tránsitos and Totalizadas may be),
   give it its own reference file rather than forcing it into `columns.md`.
