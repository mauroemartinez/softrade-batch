# Latin America: who you can see, and how current the data is

The single most important question before promising anything: **does this country
name the companies?** It varies enormously, and there is no pattern to guess from.

Captured live 2026-09-02 by opening every form and reading its filter fields. The
cutoff column is the date Softrade shows in the blue header, meaning the last day
of loaded data.

The presence of an `Importador` or `Exportador` **filter** is the reliable signal.
If the form cannot filter by company, the report cannot answer "what did company X
trade", no matter what the results grid appears to show. Argentina is the proof:
its exports grid has an `Exportador` column that is `No disponible` in 100% of rows,
and no filter.

## Sudamerica

| Country | Nomenclature | Data through | Importador | Proveedor | Exportador | Comprador |
|---|---|---|---|---|---|---|
| **AR** Argentina | NCM-SIM | 31/07/2026 | yes | no | **NO** | no |
| **BO** Bolivia | NANDINA | 31/07/2026 | yes | **yes** | yes | **yes** |
| **BR** Brasil *(Importaciones)* | Codigo NCM | al dia | **NO** | no | **NO** | no |
| **BR** Brasil *(Detalladas)* | Codigo NCM | **30/11/2021** | **NO** | no | **NO** | no |
| **BR** Brasil *(Cargas Maritimas)* | Codigo NCM | 30/11/2023 | **Consignatario** | **Shipper** | **Consignatario** | **Shipper** |
| **CL** Chile | **SACH** | 30/06/2026 | yes | no | yes | no |
| **CO** Colombia | NANDINA | 31/05/2026 imp / 30/06/2026 exp | yes | **yes** | yes | **yes** |
| **EC** Ecuador | NANDINA | 23/08/2026 | yes | **yes** | yes | **yes** |
| **PY** Paraguay | Codigo NCM | 31/07/2026 | *Probable* | *Probable* | *Probable* | *Probable* |
| **PE** Peru | NANDINA | 22/08/2026 | yes | **yes** | yes | **yes** |
| **UY** Uruguay | Codigo NCM | **01/09/2026** | yes | no | yes | no |
| **VE** Venezuela | NANDINA | **31/08/2024** | yes | no | yes | no |

## Centroamerica y Caribe

| Country | Nomenclature | Data through | Importador | Proveedor | Exportador | Comprador |
|---|---|---|---|---|---|---|
| **CR** Costa Rica | SAC | 16/08/2026 | yes | **yes** | yes | **yes** |
| **SV** El Salvador | SAC | **30/06/2025** | **NO** | no | **NO** | no |
| **GT** Guatemala *(Detalladas)* | SAC | **31/12/2021** | **NO** | no | **NO** | no |
| **HN** Honduras | SAC | 31/03/2026 | **NO** | no | **NO** | no |
| **NI** Nicaragua *(Detalladas)* | SAC | 31/07/2026 | yes | **yes** | yes | **yes** |
| **PA** Panama | SAC | 20/08/2026 | yes | **yes** | yes | **yes** |
| **PR** Puerto Rico | SAC | **31/07/2025** | **NO** | no | **NO** | no |
| **DO** Rep. Dominicana *(Detalladas)* | SAC | 31/07/2026 | yes | **yes** | yes | **yes** |

## Norteamerica

| Country | Nomenclature | Data through | Importador | Proveedor | Exportador | Comprador |
|---|---|---|---|---|---|---|
| **MX** Mexico *(Importaciones)* | Codigo SA | **30/11/2021** | **NO** | no | **NO** | no |
| **MX** Mexico *(Cargas Totales)* | Codigo SA | 31/05/2026 | **yes** | **yes** | **yes** | **yes** |

## How to read this

### The eight countries that name both sides

Bolivia, Colombia, Ecuador, Peru, Costa Rica, Nicaragua, Panama and Dominican
Republic carry **both** the local company and its foreign counterparty:
`Proveedor` on the import side, `Comprador` on the export side.

That is the richest data in the whole system. It answers "who does this company buy
from" and "who does this exporter sell to", which the larger countries cannot.

### Brasil and Mexico: look in Cargas, not in Importaciones

This is the correction that matters most, and it is easy to get backwards.

For **Brasil** and **Mexico**, the Importaciones and Exportaciones reports name
nobody. Concluding "these countries have no company data" would be wrong. The
company data is in a different report family:

| Report | Names companies | Data through |
|---|---|---|
| BR Importaciones | no | current |
| BR Importaciones Detalladas | no | 30/11/2021 |
| **BR Cargas Maritimas Ingresos** | **yes** | 30/11/2023 |
| MX Importaciones | no | 30/11/2021 |
| **MX Cargas Totales Ingresos** | **yes, Importador and Proveedor** | **31/05/2026** |

**Mexico's Cargas Totales is current to May 2026 and names both sides.** So the
answer to "can I see Mexican importers" is yes, through Cargas, even though the
Importaciones report is anonymous and frozen in 2021.

Brasil's Cargas Maritimas is **bill of lading data, not customs data**, and it is
unusually rich. Its 34 columns include `Consignatario` and `Shipper` each with
**address, email and telephone**, plus `Notify`, vessel name, forwarder, carrier,
container type and TEUs. Treat those contact details with care: they are personal
and commercial data about identifiable people, and the licence they arrive under is
Softrade's, not yours to redistribute.

Brasil Importaciones, by contrast, is monthly aggregated statistics. Its `Fecha`
column carries only month and year, and it has port and destination state but no
declaration-level detail.

### The four that name nobody, anywhere

El Salvador, Guatemala Detalladas, Honduras and Puerto Rico have **no company
filter in any report**. They answer questions about products, flows and prices,
never about firms. They are also the thinnest files in the system: Honduras and El
Salvador return 8 columns. Say this up front rather than running a query and
delivering unattributable rows.

### Argentina is asymmetric

Imports name the importer. **Exports name nobody.** This trips people up constantly
because the same country behaves differently depending on direction. See
`columns.md` for the measurement: `Exportador` is the literal string
`No disponible` in 100% of 53,525 rows.

### Paraguay is inferred, not official

Paraguay's fields are labelled **"Probable Importador"** and **"Probable
Exportador"**. Softrade is guessing, from probabilities and history, not reading an
official record. Always pass that word on to the user. A "probable" match presented
as fact is the worst failure mode here, because it looks exactly like real data.

Argentina's export form carries a similar notice about an independent service using
AI to build market estimates.

### Currency of the data varies by years, not months

| Freshness | Countries |
|---|---|
| Within days | UY 01/09, EC 23/08, PE 22/08, PA 20/08, CR 16/08 |
| Within weeks | AR, BO, PY, NI, DO 31/07, CL 30/06, CO |
| Months behind | HN 31/03/2026 |
| A year or more | PR, SV mid-2025, **VE 08/2024** |
| Frozen years ago | **BR Detalladas, MX Importaciones 11/2021**, **GT Detalladas 12/2021** |

**Check the cutoff before promising "this year".** Asking Mexico or Brazil
Detalladas for 2026 data returns nothing, and the empty result looks like a filter
mistake rather than what it is. Read the date from the blue header, and remember the
month picker greys out months past it.

Brasil Detalladas and Mexico Importaciones being frozen at November 2021 is worth
flagging explicitly: these are the two largest economies in the region, and a user
will assume they are the best covered. Check whether their Cargas reports answer the
question instead, since those are far more current.

### Nomenclature is not the same code everywhere

| System | Countries |
|---|---|
| NCM-SIM | AR |
| Codigo NCM | BR, PY, UY |
| NANDINA | BO, CO, EC, PE, VE |
| SAC | CR, SV, GT, HN, NI, PA, PR, DO |
| SACH | CL |
| Codigo SA | MX |

They share the first 6 digits of the Harmonized System, so a chapter or heading
carries across. The full national codes do not. Never paste a full Argentine
NCM-SIM into Chile's SACH field and expect a match.

### Other filters worth knowing

- **Peru and Panama** have a `Puerto` filter. So does Brasil Importaciones.
- **Uruguay** has `Despachante`, the customs broker.
- **Colombia and Peru** have `Transportista`, the carrier.
- **Dominican Republic** has `Agencia Aduanera`, and its export form has
  `Empresa Naviera`, the shipping line.
- **Ecuador** exports carry `Estado de Declaracion`.
- **Costa Rica and Panama** number declarations as `Ordinal`, Peru and Uruguay as
  `DUA`, Colombia as `Nro. Declaracion`, Paraguay as `Despacho`.

## Column layouts

Measured for all 19 Latin American countries, from real downloads. See
`columns-latam.md`, which carries the row, record and column counts of each, plus
the full column list per country.

## Still not verified

Export-side column layouts, and every country outside Latin America. The
import-side sweep above is complete.
