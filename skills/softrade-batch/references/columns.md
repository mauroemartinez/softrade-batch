# Softrade: column layouts

Confirm columns with `scripts/inspect_download.py` on a real export. **Never copy
them from the on-screen grid**: the grid is a preview, and the export carries far
more fields. For Argentina / Importaciones Detalladas the grid shows 12 columns and
the Excel has 36.

## Argentina / Importaciones Detalladas

Verified 2026-09-02 against a real export: 143 rows, 36 columns, every column 100%
filled in the sample.

| # | Column | Example |
|---|---|---|
| 1 | Identificador | `26001IC04013595S` |
| 2 | Item | `1` |
| 3 | Fecha | `2026-01-20` |
| 4 | Tipo de Dato | `DEFINITIVO` |
| 5 | NCM-SIM | `8544.42.00.110Y` |
| 6 | Importador | `NOMBRE DE LA EMPRESA S.A.` |
| 7 | Localidad | `CAP FED` |
| 8 | Destinación | `CONSUMO` |
| 9 | Aduana | `BS.AS. (CAPITAL)` |
| 10 | Via Transporte | `ACUATICA` |
| 11 | País de Origen | `Alemania` |
| 12 | País de Procedencia | `Alemania` |
| 13 | U$S Unitario | `97.01` |
| 14 | U$S FOB | `97.01` |
| 15 | Flete U$S | `0.42` |
| 16 | Seguro U$S | `0.49` |
| 17 | U$S CIF | `97.92` |
| 18 | Cant. Estad. | `1` |
| 19 | Un. Medida Estad. | `UNIDAD` |
| 20 | Cantidad | `1` |
| 21 | Unidad de Medida | `UNIDAD` |
| 22 | Kgs. Netos | `0.38` |
| 23 | Kgs. Brutos | `0.41` |
| 24 | Derecho | `0` |
| 25 | % Dere. | `0` |
| 26 | Acuerdo ALADI | `No disponible` |
| 27 | Item *(second one)* | `0` |
| 28 | Marca - Sufijos | `MARCA: <marca>` |
| 29 | Cantidad *(second one)* | `1` |
| 30 | Unitario Divisa | `83.19` |
| 31 | FOB Divisa | `83.19` |
| 32 | Moneda Divisa | `EURO` |
| 33 | Condición de Venta | `FCA` |
| 34 | Marca o Descripcion | `AA(<marca>)-AB(<modelo>)-...` |
| 35 | Descripcion Arancelaria | `CONDUCTORES ELECTRICOS PARA UNA TENSION ...` |
| 36 | Modelo | `<codigo de modelo>` |

### Reading this correctly

- **`Item` and `Cantidad` each appear twice.** Pandas renames the duplicates to
  `Item.1` and `Cantidad.1`; other tools may silently keep only one. The second
  pair belongs to the Marca / sufijos sub-record, not to the line item, and the two
  `Cantidad` values do not always agree. Always address these by position, never by
  name.
- **One row is one line item, not one shipment.** `Identificador` repeats across a
  despacho and `Item` numbers the lines within it. Counting rows overstates the
  number of operations, so aggregate on `Identificador` when the user asks how many
  imports there were.
- **Two prices and two currencies.** `U$S *` columns are the customs USD values;
  `Unitario Divisa` / `FOB Divisa` / `Moneda Divisa` are the original invoice
  currency. Do not mix them.
- `Fecha` comes through as a real datetime, not a string.
- `Acuerdo ALADI` uses the literal `No disponible` rather than an empty cell, so a
  null check will not catch it.

### Grid columns, for reference

The results table shows only: Fecha, Identificador, Item, País de Origen, NCM-SIM,
U$S CIF, U$S Unitario, Cantidad, Importador, Aduana, Via Transporte, Marca o
Descripcion.

Readable without downloading, useful only for a sanity check:

```js
[...document.querySelectorAll('th')].map(e => e.innerText.trim()).filter(Boolean)
```

## Argentina / Importaciones

Verified 2026-09-02: same query as above returned the **same 143 rows** but only 13
columns. This report is a subset of Importaciones Detalladas, not a different
dataset. Always prefer the Detalladas variant unless the user wants a smaller file.

`Identificador | Item | Fecha | Código NCM-SIM | Importador | País de Origen |
País de Procedencia | Aduana | Transporte | U$S FOB | Cantidad | Unidad |
Descripción`

Note it carries `U$S FOB` where the detailed report carries the full CIF breakdown.

## Argentina / Exportaciones Detalladas

Verified 2026-09-02, one month (07/2026) with País de Destino = Brasil:
**53,525 rows, 31 columns, 7 MB**. One country pair for one month is already a
large file, so plan export runs a month at a time.

`Identificador | Item | Fecha | Estado | NCM-SIM | Exportador | Localidad | Tipo de
Dato | Fecha Cumplido | Fecha Cargado | Destinación | Aduana | Via Transporte |
País de Destino | Aduana de Destino | U$S Unitario | U$S FOB | Flete U$S | Seguro |
Cantidad | Unidad | Kgs. Netos | Item.1 | Marca - Sufijos | Cantidad.1 | Unitario
Divisa | FOB Divisa | Moneda Divisa | Condición de Venta | Marca o Descripcion |
Descripcion Arancelaria`

### Argentine exports cannot be attributed to a company

This is the single most important fact about this report. Measured across all
53,525 rows:

| Column | `No disponible` |
|---|---|
| Exportador | **100%** |
| Identificador | **100%** |
| Localidad | **100%** |
| Estado | **100%** |
| Fecha Cargado | **100%** |

Every one of those columns is the literal string `No disponible` in every row. The
form has **no Exportador filter at all**, and the results grid shows an
`Exportador` column that is always empty, which reads as if the data merely happens
to be missing for this query. It is not: Argentina does not publish exporter
identities in this dataset.

**So "las expo de mi empresa" is impossible for Argentina.** Say so before running
anything, rather than delivering 53,000 unattributable rows. What Argentine exports
*can* answer: what left the country, under which NCM, to which destination, at what
price, with which brand (`Marca - Sufijos` is populated, and often names the firm,
for example `MARCA: <nombre de la firma>`).

The form also carries a notice that the data comes from an independent service
using AI and probabilities to build market estimates. Treat any inferred attribution
as an estimate, and tell the user it is one.

### Filters differ from the imports form

Exportaciones Detalladas filters: Periodo, Identificador, NCM-SIM, País de Destino,
Ramo Actividad, Tipo de Documento, Transporte, Aduana de Salida, **Estado**
(defaults to `Cumplidos`), Acuerdo ALADI, U$S FOB, U$S Unitario, Kgs Brutos.

Note `Estado` has a non-empty default, so an "unfiltered" export query is already
filtered. Mention it when reporting results.

**An export search with no filters at all does not run.** The form simply stays
put with no error. Give it at least one real filter, such as País de Destino.

## Entity catalogs are per report, not global

The same search term in the Importador field returned **two** entities in
Importaciones Detalladas (a foreign parent and the local company) but only **one**
in Importaciones. Never carry a resolved entity from one report to another
without re-checking it.

## Other reports

Not yet documented: Exportaciones (non detailed), Otras Operaciones, the Acumulados
and Empresas modules, and every country other than Argentina.
