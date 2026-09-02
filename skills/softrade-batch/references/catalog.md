# Softrade: full catalog of countries and operations

Captured live 2026-09-02 by reading the flag bar and each country's menu.
**78 countries.** What a given account can actually open depends on its
subscription, so treat this as the catalog, not as an entitlement list.

Country codes are the two-letter codes Softrade uses in its own flag images
(`AR.png`) and in report URLs (`/home/formulario/AR/importDetalladas`).

## How to re-capture this list

The flag bar is `img.imgTituloPaisBar`, and each country's menu is `ion-item`:

```js
// countries in the current continent tab
[...document.querySelectorAll('img.imgTituloPaisBar')]
  .map(e => e.src.split('/').pop().replace('.png',''))

// that country's operations, after clicking its flag
[...document.querySelectorAll('ion-item')]
  .map(e => e.innerText.replace(/\s+/g,' ').trim()).filter(Boolean)
// first entry is the country name, the rest are its reports
```

Continent tabs need a **real click**, a JS `.click()` does not switch them. Flags
respond fine to JS `.click()`. Close each menu before opening the next or the
lists stack and contaminate each other.

## Sudamerica (10)

| Code | Country | Operations |
|---|---|---|
| AR | Argentina | Importaciones, Importaciones Detalladas, Exportaciones, Exportaciones Detalladas, Otras Operaciones |
| BO | Bolivia | Importaciones, Exportaciones, Histórico Importaciones, Histórico Exportaciones |
| BR | Brasil | Importaciones, Importaciones Detalladas, Exportaciones, Exportaciones Detalladas, Cargas Marítimas Ingresos, Cargas Marítimas Salidas, Cargas Histórico Ingresos, Cargas Histórico Salidas |
| CL | Chile | Importaciones, Exportaciones |
| CO | Colombia | Importaciones, Exportaciones, Histórico Importaciones, Histórico Exportaciones |
| EC | Ecuador | Importaciones, Exportaciones, Histórico Importaciones, Histórico Exportaciones, Cargas Ingresos, Cargas Salidas |
| PY | Paraguay | Importaciones, Exportaciones |
| PE | Perú | Importaciones, Exportaciones, Cargas Ingresos, Cargas Salidas |
| UY | Uruguay | Importaciones, Exportaciones, Tránsitos, Cargas Aéreas, Cargas Marítimas, Cargas Terrestres, Normativa |
| VE | Venezuela | Importaciones, Exportaciones, Histórico Importaciones, Histórico Exportaciones, Cargas Ingresos, Cargas Salidas |

## Centroamerica y Caribe (8)

| Code | Country | Operations |
|---|---|---|
| CR | Costa Rica | Importaciones, Exportaciones, **Zona Franca** |
| SV | El Salvador | Importaciones, Exportaciones |
| GT | Guatemala | Importaciones, Exportaciones, Importaciones Detalladas, Exportaciones Detalladas, Cargas Ingresos, Cargas Salidas |
| HN | Honduras | Importaciones, Exportaciones, Histórico Importaciones, Histórico Exportaciones |
| NI | Nicaragua | Importaciones, Importaciones Detalladas, Exportaciones, Exportaciones Detalladas |
| PA | Panamá | Importaciones, Exportaciones, **Zona Libre Ingresos**, **Zona Libre Salidas**, Cargas Marítimas Ingresos, Cargas Marítimas Salidas |
| PR | Puerto Rico | Importaciones, Exportaciones |
| DO | Rep. Dominicana | Importaciones, Importaciones Detalladas, Exportaciones, Exportaciones Detalladas |

## Norteamerica (3)

| Code | Country | Operations |
|---|---|---|
| CA | Canadá | Importaciones, Histórico Importaciones, Exportaciones, Histórico Exportaciones |
| US | Estados Unidos | Importaciones, Exportaciones, Cargas Marítimas Ingresos, Cargas Marítimas Salidas |
| MX | México | Importaciones, Exportaciones, Otras Operaciones, Cargas Totales Ingresos, Cargas Totales Salidas |

## Asia (17)

| Code | Country | Operations |
|---|---|---|
| BD | Bangladesh | **Importaciones only** |
| CN | China | Importaciones, Exportaciones |
| KR | Corea del Sur | Importaciones, Exportaciones |
| PH | Filipinas | Importaciones, Exportaciones, Histórico Importaciones, Histórico Exportaciones |
| IN | India | Importaciones, Exportaciones |
| ID | Indonesia | Importaciones, Exportaciones, Histórico Importaciones, Histórico Exportaciones |
| IL | Israel | Importaciones, Exportaciones |
| JP | Japón | Importaciones, Exportaciones |
| KZ | Kazajistán | Importaciones, Exportaciones |
| PK | Pakistán | Importaciones, Exportaciones |
| RU | Rusia | Importaciones, **Importaciones Detalladas**, Exportaciones, **Exportaciones Detalladas** |
| LK | Sri Lanka | Importaciones, Exportaciones |
| TH | Tailandia | Importaciones, Exportaciones |
| TW | Taiwán | Importaciones, Exportaciones |
| TR | Turquía | Importaciones, **Importaciones Detalladas**, Exportaciones, **Exportaciones Detalladas** |
| UZ | Uzbekistán | Importaciones, Exportaciones |
| VN | Vietnam | Importaciones, Exportaciones, Histórico Importaciones, Histórico Exportaciones |

## Africa (9)

| Code | Country | Operations |
|---|---|---|
| EG | Egipto | Importaciones, Exportaciones |
| ET | Etiopía | Importaciones, Exportaciones |
| KE | Kenia | Importaciones, **Histórico Importaciones** (no exports) |
| LS | Lesoto | Importaciones, Exportaciones |
| MA | Marruecos | Importaciones, Exportaciones |
| NG | Nigeria | Importaciones, Exportaciones |
| ZA | Sudáfrica | Importaciones, Exportaciones |
| UG | Uganda | Importaciones, Exportaciones |
| ZW | Zimbabue | Importaciones, Exportaciones |

## Oceania (2)

| Code | Country | Operations |
|---|---|---|
| AU | Australia | Importaciones, Histórico Importaciones, Exportaciones, Histórico Exportaciones |
| NZ | Nueva Zelanda | Importaciones, Exportaciones |

## Europa (29)

Every European country offers **Importaciones and Exportaciones**, with one
exception:

| Code | Country | Operations |
|---|---|---|
| ES | España | Importaciones, **Importaciones Totalizadas**, Exportaciones, **Exportaciones Totalizadas** |

The other 28, all Importaciones + Exportaciones: DE Alemania, AT Austria,
BE Bélgica, BG Bulgaria, CY Chipre, HR Croacia, DK Dinamarca, SK Eslovaquia,
SI Eslovenia, EE Estonia, FI Finlandia, FR Francia, GR Grecia, HU Hungría,
IE Irlanda, IT Italia, LV Letonia, LT Lituania, LU Luxemburgo, MT Malta,
NL Países Bajos, PL Polonia, PT Portugal, GB Reino Unido, CZ República Checa,
RO Rumania, SE Suecia, UA Ucrania.


## What has actually been run

The table above is the catalog: which reports exist. This section is the far
shorter list of what has been **verified by downloading real data**. Keep the two
apart, and never present a catalog row as if its behaviour were known.

### Argentina, verified 2026-09-02

Data loaded through **31/7/2026**. The month picker greys out later months, so read
the cutoff from the widget rather than assuming the current month exists.

| Report | Columns in Excel | Company identity |
|---|---|---|
| Importaciones | 13 | `Importador`, populated and filterable |
| Importaciones Detalladas | 36 | `Importador`, populated and filterable |
| Exportaciones Detalladas | 31 | **none**, `Exportador` is `No disponible` in 100% of rows, and there is no filter |
| Otras Operaciones | 30 | `Importador`, populated and filterable |
| Exportaciones | not run | unknown |

Importaciones returned exactly the same records as Importaciones Detalladas for the
same query, with fewer columns. It is a projection, not a different dataset.

Scale reference: one month of exports to a single destination country was 25,162
records and 53,525 rows, 7 MB, which is 84% of the 30,000 record cap. One company's
imports over seven months was 22 records and 143 rows.

### Everything else

Not verified. Report availability comes from the catalog above, but column layouts,
which filters each form offers, and whether importer or exporter names exist all
vary by country. None of the Argentina findings should be assumed to carry over.

## Cross-country views

Two entries sit outside the flag bar, next to the continent tabs:

| View | URL when open | What it offers |
|---|---|---|
| Vista Global | `/home/formulario/01/global` | Importaciones / Exportaciones toggle, filters for Periodo, Identificador, Codigo NCM, Pais de Origen, Puerto, Estado, U$S FOB, U$S Unitario, Kgs. Brutos |
| Consulta Regional | `/home/formulario/01/regional` | Importaciones / Exportaciones plus an Importadores / Exportadores toggle, a year selector, an accumulation selector (`Acum. Anual`), and NCM chips |

Consulta Regional is built around comparing entities across countries by year, and
is aggregated rather than transaction level. Neither view has been run to the point
of downloading a file, so their exports are undocumented.

Note that Brasil Importaciones carries a **Puerto** filter, which Argentina's forms
do not. Filter sets are per country and per report, so read the form rather than
assuming it matches one you already know.

## What the operation names mean

- **Importaciones / Exportaciones**: the standard report. Fewer columns.
- **Detalladas**: the same records with far more fields. For Argentina imports,
  36 columns against 13. Prefer these when available.
- **Histórico**: older periods, held separately from the current dataset.
- **Cargas**: shipping manifests (marítimas, aéreas, terrestres), a different kind
  of record from customs declarations. Ingresos and Salidas are separate reports.
- **Otras Operaciones**: customs entries outside ordinary consumption imports,
  such as temporary admission. Argentina and México only.
- **Zona Franca / Zona Libre**: free-trade-zone movements. Costa Rica and Panamá.
- **Tránsitos**: goods passing through. Uruguay only.
- **Totalizadas**: aggregated rather than transaction level. Spain only.
- **Normativa**: regulations, not trade data. Uruguay only.

## Only 8 countries offer Detalladas

AR, BR, GT, NI, DO, RU, TR, and ES in its Totalizadas form. If a user asks for
detailed, transaction-level data anywhere else, it does not exist, and the standard
report is the most they can get. Say so rather than downloading the wrong thing.
