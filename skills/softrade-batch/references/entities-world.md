# Asia, Africa, Oceania and Europe: who you can see

Companion to `entities-latam.md`, same method: every import and export form opened
live on 2026-09-02 and its filter fields read. The presence of an `Importador` or
`Exportador` filter is the reliable signal that a country's data can answer
questions about companies.

The catalog does not vary by subscription. Verified against two separate Softrade
accounts, which showed identical countries and reports.

## Asia (17)

Export-side coverage is in the last column pair. Where imports and exports differ,
both are shown.

| Country | Nomenclature | Data through | Importador | Proveedor | Exportador | Comprador |
|---|---|---|---|---|---|---|
| **BD** Bangladesh | Codigo SA | **31/07/2026** | yes | **yes** | *no export report* | |
| **CN** China | Codigo SA | 31/12/2025 | **NO** | no | **NO** | no |
| **KR** Corea del Sur | Codigo SA | 31/05/2026 | **NO** | no | **NO** | no |
| **PH** Filipinas | Codigo SA | 31/12/2025 | yes | **yes** | yes | **yes** |
| **IN** India | Codigo SA | **30/06/2018** | **NO** | no | **NO** | no |
| **ID** Indonesia | Codigo SA | 30/09/2021 | yes | **yes** | yes | **yes** |
| **IL** Israel | Codigo SA | 31/05/2026 | **NO** | no | **NO** | no |
| **JP** Japon | **Codigo JTS** | **31/07/2026** | **NO** | no | **NO** | no |
| **KZ** Kazajistan | Codigo SA | **31/07/2026** | yes | **yes** | yes | **yes** |
| **PK** Pakistan | Codigo SA | **31/07/2026** | yes | **yes** | yes | **yes** |
| **RU** Rusia *(Detalladas)* | **Codigo CN FEA** | 31/12/2023 | yes | **yes** | yes | **yes** |
| **LK** Sri Lanka | Codigo SA | 31/12/2019 | yes | **yes** | yes | **yes** |
| **TH** Tailandia | Codigo SA | **31/07/2026** | **NO** | no | **NO** | no |
| **TW** Taiwan | Codigo SA | **31/03/2017** | **NO** | no | **NO** | no |
| **TR** Turquia *(Detalladas)* | Codigo SA | 31/12/2023 | yes | **yes** | yes | **yes** |
| **UZ** Uzbekistan | Codigo SA | 31/12/2025 | yes | **yes** | yes | **yes** |
| **VN** Vietnam | Codigo SA | **30/06/2026** | yes | **yes** | yes | **yes** |

### China does not name importers

This is the finding that surprises people most, and it matters for anyone sourcing
from Asia. China's import report has **six filters total**: Periodo, Identificador,
Codigo SA, Pais de Origen, US$ CIF, Cantidad. No importer, no supplier, no port, no
customs office, no description. It is aggregate statistics.

Softrade cannot tell you who imports what into China, nor who a Chinese supplier
sells to inside China. If a user asks, say so before running anything.

Note this is about **imports into China**. Finding Chinese *suppliers* is a
different question, answered from the other side: the `Proveedor` column of an
importing country such as Peru, Vietnam or Pakistan names the Chinese exporter.
That is usually what the user actually wants.

### The best-covered Asian countries

**Vietnam** is the standout: importer, supplier, both ports and the bonded
warehouse (`Deposito`), current to June 2026.

**Pakistan, Kazakhstan and Bangladesh** are all current to July 2026 and name both
sides. Bangladesh offers **imports only**, no export report at all.

**Philippines** carries an unusual third field, `Pais de Exportador`, separate from
country of origin.

### Frozen or stale

| Country | Data through | Age |
|---|---|---|
| **TW** Taiwan | 31/03/2017 | over 9 years |
| **IN** India | 30/06/2018 | over 8 years |
| **LK** Sri Lanka | 31/12/2019 | almost 7 years |
| **ID** Indonesia | 30/09/2021 | 5 years |
| **RU, TR** | 31/12/2023 | almost 3 years |

India and Taiwan are effectively historical archives. Do not offer them for
anything current.

## Africa (9)

| Country | Nomenclature | Data through | Importador | Proveedor | Exportador | Comprador |
|---|---|---|---|---|---|---|
| **EG** Egipto | Codigo SA | **28/02/2015** | **NO** | no | **NO** | no |
| **ET** Etiopia | Codigo SA | **31/07/2026** | yes | no | yes | **yes** |
| **KE** Kenia | Codigo SA | 30/06/2026 | yes | **yes** | *no export report* | |
| **LS** Lesoto | Codigo SA | **31/07/2026** | yes | **yes** | yes | **yes** |
| **MA** Marruecos | Codigo SA | 28/02/2026 | **NO** | no | **NO** | no |
| **NG** Nigeria | Codigo SA | 31/07/2025 | yes | **yes** | yes | **yes** |
| **ZA** Sudafrica | Codigo SA | **31/07/2026** | **NO** | no | **NO** | no |
| **UG** Uganda | Codigo SA | 30/09/2024 | yes | **yes** | yes | **yes** |
| **ZW** Zimbabue | Codigo SA | 31/07/2023 | yes | **yes** | yes | **yes** |

**Egypt is the oldest data in the entire system, February 2015.** Over eleven
years stale. It should never be offered as current.

**South Africa reports in Rand, not dollars.** Its value column is `ZAR CIF`, the
only non-USD, non-euro currency in the system. Any cross-country comparison needs a
conversion the user must supply, since Softrade does not do it.

Kenya has a `Terminal de Contenedores` filter and, uniquely, carries both an
`Identificador` and a separate `Nro. Declaracion`.

## Oceania (2)

| Country | Nomenclature | Data through | Importador | Proveedor | Exportador | Comprador |
|---|---|---|---|---|---|---|
| **AU** Australia | Codigo SA | 30/06/2026 | **NO** | no | **NO** | no |
| **NZ** Nueva Zelanda | Codigo SA | **31/07/2026** | **NO** | no | **NO** | no |

Neither names companies. Australia is the only country with both an `Aduana de
Ingreso` and an `Aduana de Salida` filter on its import form.

## Europa (29)

**Only one European country names companies: Ukraine.**

| Country | Nomenclature | Imports through | Exports through | Names anyone |
|---|---|---|---|---|
| **UA** Ucrania | **Codigo UKTWED** | 31/12/2024 | 31/12/2022 | **yes, both sides** |
| **GB** Reino Unido | Codigo SA | 30/04/2026 | 30/04/2026 | no |
| **ES** Espana *(Importaciones)* | Codigo NC | 31/12/2025 | | no |
| **ES** Espana *(Totalizadas)* | Codigo NC | 31/05/2026 | | no |
| The EU block | **Codigo NC** | **31/05/2026** | **31/05/2026** | no |

The EU block behaves as one dataset. Germany, Italy and Poland returned an
identical filter set, an identical cutoff of 31/05/2026, and values in **euros**:

`Periodo, Identificador, Codigo NC, Pais de Procedencia, Regimen, Descripcion,
EUR FOB, Cantidad Comercial, Kilos`

Exports are the mirror image, with `Pais de Destino` in place of `Pais de
Procedencia`. Assume the other 25 EU members match, since they are the same source.

**Spain's two reports are the opposite of what their names suggest.** Its
*Totalizadas* report is the ordinary EU dataset, same fields and same 31/05/2026
cutoff as Germany. Its *Importaciones* report is the Spain-specific one: it drops
`Identificador`, adds `Pais de Origen` and the two customs offices, and stops on
31/12/2025. So for Spain, `Importaciones` is the richer and older one, and
`Totalizadas` is the standard and newer one.

The United Kingdom sits outside that block: it uses `Codigo SA` rather than
`Codigo NC` and reports in **dollars**, not euros.

**Ukraine's exports lag its imports by two years**, 31/12/2022 against 31/12/2024.
Its export form also carries both `Exportador` and `Comprador`.

### Two traps in European data

**The values are in euros, not dollars.** `EUR FOB` where every other region gives
`U$S CIF`. Mixing them in one analysis is silently wrong, and it is FOB against CIF
as well, so the numbers are not comparable even after a currency conversion.

**`Pais de Procedencia`, not `Pais de Origen`.** The EU block filters by country of
consignment. Goods made in China and shipped from the Netherlands count as coming
from the Netherlands. For origin analysis this is the wrong field, and Spain is the
only EU member that offers the real one.

## Summary: where company names exist

| Region | Countries that name the importer |
|---|---|
| **Latin America** | 13 of 19, plus Brasil and Mexico through Cargas. See `entities-latam.md` |
| **Asia** | 10 of 17: BD, PH, ID, KZ, PK, RU, LK, TR, UZ, VN |
| **Africa** | 6 of 9: ET, KE, LS, NG, UG, ZW |
| **Oceania** | 0 of 2 |
| **Europe** | **1 of 29**, Ukraine only |

The pattern, roughly: **the smaller or less wealthy the country, the more likely it
publishes company names.** The G7 economies and China publish none. That is the
opposite of what most users assume, and worth saying plainly when the answer is no.

### Ethiopia is asymmetric the useful way

Ethiopia's import form names only the `Importador`, with no supplier. Its **export**
form carries both `Exportador` and `Comprador`. It is the only country in this file
where the export side is richer than the import side.

## Not yet verified

Column layouts for every country outside Latin America. Both the import and export
forms are now documented; what the exported files actually contain is not.
