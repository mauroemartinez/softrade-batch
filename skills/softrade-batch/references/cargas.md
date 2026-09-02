# The Cargas family: bill of lading data

A separate data family from customs declarations, and the one most people miss.
Where a country's Importaciones report is anonymous, its Cargas report often is not.

Captured live 2026-09-02 by opening each form and reading its filters.

## Why this matters

Cargas records are **manifests, not customs declarations**. They carry the two
trading parties by name, plus vessel, container and port detail that customs data
never has. For Brasil, Mexico and the United States, this is the **only** place
company names appear.

Never tell a user a country has no company data without checking its Cargas
reports first.

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

## Not yet measured

Column layouts for every Cargas report except Brasil. The filters above are
verified; what the exported files contain is not.
