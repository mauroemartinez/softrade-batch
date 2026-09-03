# Verification coverage tracker

What has actually been confirmed by downloading a real file, versus what is only
known from the catalog. Update this file whenever a new report gets verified — see
"Learning a new report type" in `SKILL.md`. Do not check a box from reading the
form; check it only after `inspect_download.py` has run against a real export.

## The three layers

1. **Catalog** — which reports exist per country. **Complete**, 78 countries
   (`catalog.md`).
2. **Entity filters** — whether each report can filter by company, and how current
   the data is. **Complete**, import and export sides, all 78 countries
   (`entities-latam.md`, `entities-world.md`).
3. **Column layout** — what a real downloaded Excel contains: column count, names,
   the row/record ratio, quirks like duplicated columns or a literal
   `No disponible`. **This is the layer that is mostly open.** Everything below
   tracks layer 3.

Layer 3 needs a live browser session against Softrade (`site-flow.md`) plus quota.
It cannot be done from the catalog alone.

## Breadth before depth

Softrade is not one database with 78 country skins. It is **14 distinct report
families**, and a family's form, filter set and column layout are properties of the
family, not of the country. Argentina's Importaciones tells you nothing about
Uruguay's Tránsitos.

So the ordering below is **one representative country per family first**, then fill
in countries within a family. Measuring a second country of an already-known family
teaches far less than the first country of an unknown one, and today **8 of the 14
families have never been opened at all.**

## The family matrix

| # | Family | Countries offering it | Measured | Status |
|---|---|---|---|---|
| 1 | Importaciones (standard) | all 78 | AR | partial |
| 2 | Importaciones Detalladas | AR BR GT NI DO RU TR | AR | partial |
| 3 | Exportaciones (standard) | 77 (not KE) | — | **never run** |
| 4 | Exportaciones Detalladas | AR BR GT NI DO RU TR | AR | partial |
| 5 | Histórico Imp. / Exp. | BO CO EC HN VE PH ID VN AU CA KE | — | **never opened** |
| 6 | Cargas Marítimas Ing./Sal. | BR PA US | BR Ingresos | partial |
| 7 | Cargas Ingresos / Salidas | EC PE VE GT | — | **never opened** |
| 8 | Cargas Totales Ing./Sal. | MX | — | **never opened** |
| 9 | Cargas Aéreas / Terrestres | UY | — | **never opened** |
| 10 | Cargas Histórico Ing./Sal. | BR | — | **never opened** |
| 11 | Otras Operaciones | AR MX | AR (ratio only) | partial |
| 12 | Zona Franca / Zona Libre | CR (Franca), PA (Libre Ing./Sal.) | — | **never opened** |
| 13 | Tránsitos | UY | — | **never opened** |
| 14 | Totalizadas | ES | — | **never opened** |
| — | Normativa | UY | — | never opened, **not trade data** |
| — | Vista Global | cross-country | — | **never exported** |
| — | Consulta Regional | cross-country | — | **never exported**, aggregated |

`Normativa` is regulations, not customs records. One look to confirm it carries no
exportable dataset, then drop it from this tracker for good.

## Pass A — one country per unknown family

The whole point of this pass is **one file per family**, cheapest representative,
to learn the shape. Do not chase countries here.

Representatives are picked so one login session covers several boxes: **Ecuador**
alone opens families 5 and 7, **Uruguay** opens 9 and 13, and **Brasil** opens 10
next to the Cargas Marítimas layout already measured.

- [ ] **F3 · Exportaciones (standard)** → AR. Cheapest box on the board: same
      country, same session mechanics, already documented in `site-flow.md`.
      Watch whether `Exportador` is `No disponible` here too, as it is in AR
      Exportaciones Detalladas.
- [ ] **F5 · Histórico Importaciones** → EC Ecuador. Names all four parties, data
      through 23/08/2026. **Establish what "Histórico" even means:** which periods
      it covers versus the current dataset, and whether the two overlap or abut.
- [ ] **F5 · Histórico Exportaciones** → EC, same session.
- [ ] **F7 · Cargas Ingresos** → EC or PE. Both current and name Consignatario +
      Shipper. Confirm whether this differs from the Marítimas layout at all, or
      is the same report under a shorter name.
- [ ] **F7 · Cargas Salidas** → same country as above.
- [ ] **F8 · Cargas Totales Ingresos** → MX. **Highest value in this pass:** the
      only place México names companies, both sides, current to 31/05/2026.
- [ ] **F8 · Cargas Totales Salidas** → MX, same session.
- [ ] **F9 · Cargas Aéreas** → UY. Air manifests exist nowhere else.
- [ ] **F9 · Cargas Terrestres** → UY. Land manifests exist nowhere else.
- [ ] **F10 · Cargas Histórico Ingresos** → BR. Pair it with the Marítimas
      Ingresos file already measured to see what "Histórico" changes.
- [ ] **F10 · Cargas Histórico Salidas** → BR.
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
- [ ] **AR Acumulados and Empresas modules** — seen in the site, never opened.
      Establish whether they are reports or navigation.

Completing Pass A means **every family in Softrade has one measured example**, and
any future request can be answered with "here is the shape of that report" instead
of a guess.

## Pass B — countries that name companies

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
- [ ] PE, PA, VE, UY, GT — whichever Cargas variant each offers
- [ ] Salidas counterparts for BR, PA, US

### B3 · Export-side columns, Latin America

Import-side columns are measured for all 19 (`columns-latam.md`). The export side is
unmeasured everywhere except Argentina. The 8 countries naming both sides matter
most, since they answer "who does this exporter sell to":

- [ ] BO, CO, EC, CR, NI, PA, DO — Exportaciones, columns + `Comprador` behavior
- [ ] CL, UY, VE — Exportaciones, columns (no counterparty named)
- [ ] PY — Exportaciones (*Probable Exportador* — confirm the same caveat as the
      import side)

### B4 · Asia, Africa and Ukraine

The 17 countries outside Latin America that name a company on at least one side.
Zero column layouts exist for any of them.

Asia (`entities-world.md`): BD (imports only), PH, ID, KZ, PK, LK, UZ, VN
— RU and TR are covered in B1.

- [ ] BD, PH, ID, KZ, PK, LK, UZ, VN — Importaciones + Exportaciones

Africa: ET, KE (imports only), LS, NG, UG, ZW

- [ ] ET, LS, NG, UG, ZW — Importaciones + Exportaciones
- [ ] KE — Importaciones (no export report exists)

Europe: only Ukraine names anyone.

- [ ] UA — Importaciones + Exportaciones

**Order within B4:** Vietnam and Pakistan first — both current, both sides, no
known quirks — to get a clean baseline before the messier ones. Vietnam also
carries Histórico, so pair it with family 5 if EC surfaced anything odd.

## Pass C — anonymous countries

These can only answer product, flow and price questions, never company questions.
One column pass each so the catalog is complete, done last.

- [ ] CL, PY — export side (import already measured)
- [ ] SV, HN, PR — both sides anonymous, thin files (8-11 columns, quick)
- [ ] MX, BR — Importaciones / Exportaciones proper (Cargas is the real data)
- [ ] CN, KR, IN, IL, JP, TH, TW — Asia, both directions
- [ ] EG, MA, ZA — Africa, both directions
- [ ] AU, NZ — Oceania, both directions
- [ ] Europe: sample **one** EU-block country (e.g. DE), since all 28 non-Spain,
      non-Ukraine members reportedly share one filter set and cutoff. Confirm that
      assumption on one country rather than running all 28. Then GB separately
      (Código SA and USD, not the EU block). Spain needs both Importaciones and
      Totalizadas, since they behave oppositely (`entities-world.md`).

## How to work through this

1. Take the next unchecked box in **Pass A**. Only start Pass B once Pass A has no
   boxes left — a new family teaches more than a new country.
2. Follow `site-flow.md` for the mechanics: flag menu, calendar widget for Periodo,
   the 12-month ceiling, JS `.click()` on `ion-img.imgBotonDescarga`, filesystem
   check, never the results grid.
3. Keep each verification query **deliberately tiny** — one month, one NCM code if
   the form allows it. This pass is measuring column layouts, not gathering data,
   and every row still burns the monthly quota.
4. Run `inspect_download.py` on the file.
5. Append the measured column list to `columns.md` (Argentina today, growing) or a
   new `columns-<region>.md` following the format of `columns-latam.md`, and check
   the box here.
6. If a report behaves differently from what `site-flow.md` documents — a filter in
   a different place, a Periodo field that is free text instead of a calendar,
   Puerto appearing where it did not in Argentina — add a note to `site-flow.md`
   rather than assuming it matches.
7. When a family turns out to be structurally different from the customs-declaration
   reports (Cargas already is; Zona Franca, Tránsitos and Totalizadas may be),
   give it its own reference file rather than forcing it into `columns.md`.
