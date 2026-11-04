# The Cargas family: bill of lading data

A separate data family from customs declarations, and the one most people miss.
Where a country's Importaciones report is anonymous, its Cargas report often is not.

Captured live 2026-09-02 by opening each form and reading its filters.

## Why this matters

Cargas records are **manifests, not customs declarations**. They carry names,
plus vessel, container and port detail that customs data never has. For Brasil,
Mexico and the United States, this is the **only** place company names appear.

Never tell a user a country has no company data without checking its Cargas
reports first. And never present those names as "the importer" without the caveat
in the next section.

## The consignee is not always the buyer

A customs declaration names the **importer of record**: whoever cleared the goods
and pays the duties. In the Spanish-speaking customs reports (Importaciones /
Exportaciones) that is the real trading company.

A bill of lading names whoever **the carrier delivers to**, and that is often not
the buyer:

- **Master bills** go from the shipping line to a forwarder or NVOCC. Their
  consignee is the logistics company (Kuehne+Nagel, DHL, DSV, Expeditors and the
  like), and the shipper is often its partner agent at origin.
- **"TO ORDER" / "A LA ORDEN"** bills name no one, or a bank, because the goods are
  released against a letter of credit. The real buyer may appear only as the
  **Notify** party.
- A carrier's own house or the customs broker can also appear as consignee.

So a ranking of "top importers" built on Cargas mixes buyers with forwarders, and
the forwarders tend to float to the top because they consolidate many clients.

What to do per country:

- **US**: `Incluir Masters` off keeps house bills, whose consignee is much more
  often the real importer. Leave masters out for anything you rank or aggregate
  by company. (It also avoids counting one shipment twice.)
- **BR**: the file has separate `Forwarder` and `Notify` columns. When the
  Consignatario is a logistics company, Notify is the best hint of the real buyer.
- **MX Cargas Totales**: its form filters by `Importador` and `Proveedor` and
  carries `Código SA` and `U$S CIF`, which are customs-declaration fields, not
  bill-of-lading ones. It may be declaration-based despite the family name. Treat
  that as unconfirmed until the file is inspected.
- **Everywhere in this family**: before attributing volume to a company, look at
  the top consignees. If logistics firms or "TO ORDER" lead the list, say so to
  the user and report the buyer-level ranking only after excluding them.

`scripts/preflight.py` raises this caveat automatically when an import-side
(Ingresos) Cargas report is used for a by-company question, unless the catalog
note for that report says the consignee works as the real importer (BR Cargas
Historico Ingresos). Salidas reports filter by the Shipper, so the caveat does not
apply to the side the user asks about; the catalog note still reports how often
their consignees are logistics firms.

To measure it on a real download instead of guessing:

```bash
python scripts/party_check.py RUN_DIR/downloads/FILE.xlsx
```

It reports, for every party column, the share of rows that are "TO ORDER", a known
forwarder or shipping-line brand, or a name built on logistics words, plus the top
ten names with a flag. Add `--no-names` before sharing the output: the names are
real companies from licensed data.

## What each country offers

| Country | Report | Data through | Names on it |
|---|---|---|---|
| **US** | Cargas Maritimas Ingresos | **31/07/2026** | Consignatario, Shipper |
| **BR** | Cargas Maritimas Ingresos | 30/11/2023 | Consignatario, Shipper, Notify |
| **MX** | Cargas Totales Ingresos | **31/05/2026** | Importador, Proveedor |
| **MX** | Cargas Totales Salidas | **31/05/2026** | Exportador, Comprador |
| **PE** | Cargas Ingresos | **22/08/2026** | Consignatario, Shipper |
| **EC** | Cargas Ingresos | **31/07/2026** | Consignatario, Shipper |
| **PA** | Cargas Maritimas Ingresos | **31/07/2026** | Consignatario |
| **VE** | Cargas Ingresos | 31/08/2025 | Consignatario, Shipper |
| **UY** | Cargas Maritimas | 11/07/2024 | Consignatario (B/L), Remitente |
| **GT** | Cargas Ingresos | **30/09/2019** | Consignatario, Shipper |

Uruguay also has Cargas Aereas and Cargas Terrestres. Brasil, Panama, Mexico and
the United States each have a Salidas counterpart to their Ingresos report.

### Cargas is often fresher than the customs report

| Country | Customs report through | Cargas through |
|---|---|---|
| MX | 30/11/2021 | **31/05/2026** |
| VE | 31/08/2024 | **31/08/2025** |
| BR | 30/11/2021 *(Detalladas)* | **30/11/2023** |

Guatemala is the exception and runs the other way: its Cargas stops in 2019 while
its Detalladas reaches 2021.

## Filters, country by country

**US Cargas Maritimas Ingresos** is the richest entry point for US import data:
Periodo, **Numero B/L**, Codigo SA, Descripcion, Consignatario, Shipper, Pais de
Shipper, Pais de Consignatario, Puerto de Carga, Puerto Arribo USA, Empresa
Naviera, Nombre Buque, Nro. Contenedor, **Incluir Masters**, Kgs. Brutos.

`Incluir Masters` decides whether master bills are included alongside house bills.
Leaving it on double counts a shipment that appears as both. Ask the user which
they want before running anything they will aggregate.

**BR Cargas Maritimas Ingresos**: Periodo, Ordinal, Codigo NCM, Descripcion,
Consignatario, Shipper, Pais de Origen, Pais de Destino, Puerto de Origen, Puerto
de Destino, Ruta de Origen, **Notify**, Kgs. Brutos, Teus.

**PE Cargas Ingresos**: Periodo, Identificador, **Bill of Lading**, Descripcion,
Pais de Origen, Consignatario, Shipper, Empresa Transportista, Pais de Destino,
Puerto de Carga, Puerto de Destino, Transporte, Kgs. Brutos, Cantidad.

**EC Cargas Ingresos**: Periodo, Identificador, **Bill of Lading**, Consignatario,
Shipper, Pais de Embarque, Pais de Destino, Puerto de Arribo, Puerto de Embarque,
Puerto de Destino, Transporte, Transportista, Marcas, Descripcion, Nro.
Manifiesto, Kilos.

**PA Cargas Maritimas Ingresos**: Periodo, Identificador, **Bill of Lading**,
Consignatario, Pais de Origen, Pais de Destino, Puerto de Descarga, Puerto de
Origen, Puerto de Destino, Transportista, Descripcion, Manifiesto, Nro.
Contenedor, Kilos. Note there is **no Shipper filter**, only the consignee side.

**UY Cargas Maritimas** uses its own vocabulary: Periodo, Operacion, Nro.
Manifiesto, **Conocimiento B/L**, Garante (Conocimiento), Agencia, **Consignatario
(B/L)**, **Remitente**, Puerto de Embarque, Pais de Origen, Continente, Ruta
Comercial, Puerto de Descarga, Buque, Tipo de Carga, Tipo de Contenedor, Numero
Contenedor. `Remitente` is the shipper.

**VE Cargas Ingresos**: Periodo, Identificador, Descripcion, Consignatario,
Shipper, Pais de Embarque, Lugar de Embarque, Aduana, Transporte, Kilos.

**GT Cargas Ingresos**: Periodo, Ordinal, Codigo SAC, Pais de Origen,
Consignatario, Shipper, Descripcion, U$S CIF, Kgs. Brutos, Cantidad.

**MX Cargas Totales** uses customs vocabulary rather than manifest vocabulary:
Periodo, Ordinal, Codigo SA, Importador / Exportador, Proveedor / Comprador, Pais,
Aduana, Transporte, Descripcion, U$S CIF or FOB, U$S Unitario, Kgs. Brutos.

## Measured columns: BR Cargas Maritimas Ingresos

One sample, heading 8544, 291 rows, **34 columns**:

`Ordinal | Fecha | Codigo NCM | Pais de Origen | Pais de Destino | Consignatario |
Direccion | Email | Telefono | Shipper | Direccion | Email | Telefono | Notify |
Puerto de Trasbordo | Puerto de Origen | Puerto de Destino | Puerto de Descarga |
Pais de Shipper | Pais de Trasbordo | Ruta de Origen | Transporte | Kgs. Brutos |
Teus | Valor Estimado | Tipo de Contenedor | Descripcion | Nombre Transportista |
Forwarder | Nombre Buque | Toneladas | Tipo de Carga | Tipo de Servicio | Lugar de
Recepcion`

### Handle the contact columns carefully

Both `Consignatario` and `Shipper` come with **address, email and telephone**.
That is personal and commercial data about identifiable people, arriving under
Softrade's licence rather than the user's. Do not paste it into a chat, commit it
to a repository, or send it anywhere the user has not asked for. Report counts and
column names, not contact rows.

## Zona Franca and Zona Libre

Related but distinct: free-zone movements, which never appear in ordinary import
statistics.

| Country | Report | Data through | Names |
|---|---|---|---|
| **CR** | Zona Franca | 16/08/2026 | **Operador** |
| **PA** | Zona Libre Ingresos | 31/07/2026 | **Operador**, **Proveedor** |

Panama's Zona Libre is the more useful of the two: it names both the free-zone
operator and its foreign supplier. Costa Rica names only the operator.

For anyone tracking goods that transit Colon or a Costa Rican free zone before
their final market, these reports are the only visibility there is.

## Counted on 2026-09-18, names not kept

A second survey pass downloaded a small sample (heading 8544 where the form takes
it, one month) of three
more Cargas reports. It kept the column count and a few notes (in `catalog.json`
and `columns-cargas.md`), not the column names:

| Country | Report | Data through | Columns | Names |
|---|---|---|---|---|
| **BR** | Cargas Maritimas Salidas | 30/11/2023 | 32 | `Shipper` (exporter), `Consignatario`; 2 in 3 consignees in the sample were logistics firms |
| **BR** | Cargas Historico Ingresos | 31/01/2020 | 10 | `Consignatario` only; built like a declaration, 99% companies in the sample |
| **EC** | Cargas Ingresos | 31/07/2026 | 33 | `Consignatario`, `Shipper`; no tariff-code field, filter by Descripcion or Marcas |

BR Cargas Historico Salidas was read off the form only: frozen 07/2018, names the
`Shipper`.

## Not yet measured

Column layouts for every other Cargas report, and the column names of the three
above. The filters above are verified; what the exported files contain is not.
