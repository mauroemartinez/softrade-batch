# Columnas: familia Cargas

Mismo formato que `columns-latam.md`: solo se completa una seccion cuando existe un Excel real inspeccionado.

## BR / cargasMaritimasIngresos

Medido sobre archivo real: 291 filas, 291 registros, 34 columnas.

- Pais: **BR Brasil**
- Reporte: `cargasMaritimasIngresos` (Cargas Marítimas - Ingresos)
- Nomenclatura: Codigo NCM
- Ultimo dato conocido: 30/11/2023
- Nombres esperados: Consignatario / Shipper

| # | Column | Example |
|---|---|---|
| 1 | Ordinal | pendiente |
| 2 | Fecha | pendiente |
| 3 | Codigo NCM | pendiente |
| 4 | Pais de Origen | pendiente |
| 5 | Pais de Destino | pendiente |
| 6 | Consignatario | pendiente |
| 7 | Direccion | pendiente |
| 8 | Email | pendiente |
| 9 | Telefono | pendiente |
| 10 | Shipper | pendiente |
| 11 | Direccion.1 | pendiente |
| 12 | Email.1 | pendiente |
| 13 | Telefono.1 | pendiente |
| 14 | Notify | pendiente |
| 15 | Puerto de Trasbordo | pendiente |
| 16 | Puerto de Origen | pendiente |
| 17 | Puerto de Destino | pendiente |
| 18 | Puerto de Descarga | pendiente |
| 19 | Pais de Shipper | pendiente |
| 20 | Pais de Trasbordo | pendiente |
| 21 | Ruta de Origen | pendiente |
| 22 | Transporte | pendiente |
| 23 | Kgs. Brutos | pendiente |
| 24 | Teus | pendiente |
| 25 | Valor Estimado | pendiente |
| 26 | Tipo de Contenedor | pendiente |
| 27 | Descripcion | pendiente |
| 28 | Nombre Transportista | pendiente |
| 29 | Forwarder | pendiente |
| 30 | Nombre Buque | pendiente |
| 31 | Toneladas | pendiente |
| 32 | Tipo de Carga | pendiente |
| 33 | Tipo de Servicio | pendiente |
| 34 | Lugar de Recepcion | pendiente |

### Reading this correctly

- `Consignatario` y `Shipper` vienen con direccion, email y telefono; no pegar filas ni contactos en chats o repos.
- Es manifiesto de embarque, no declaracion aduanera.

### US / cargasMaritimasIngresos

<!-- PENDIENTE: medicion en vivo -->

- Pais: **US Estados Unidos**
- Reporte: `cargasMaritimasIngresos` (Cargas Marítimas - Ingresos)
- Nomenclatura: Codigo SA
- Ultimo dato conocido: 31/07/2026
- Nombres esperados: Consignatario / Shipper

Filas: pendiente. Registros: pendiente. Columnas: pendiente.

| # | Column | Example |
|---|---|---|
| 1 | pendiente | pendiente |

#### Reading this correctly

- Pendiente: completar despues de correr `inspect_download.py` sobre un Excel real.

### PE / cargasIngresos

<!-- PENDIENTE: medicion en vivo -->

- Pais: **PE Perú**
- Reporte: `cargasIngresos` (Cargas - Ingresos)
- Nomenclatura: NANDINA
- Ultimo dato conocido: 22/08/2026
- Nombres esperados: Consignatario / Shipper

Filas: pendiente. Registros: pendiente. Columnas: pendiente.

| # | Column | Example |
|---|---|---|
| 1 | pendiente | pendiente |

#### Reading this correctly

- Pendiente: completar despues de correr `inspect_download.py` sobre un Excel real.

### EC / cargasIngresos

<!-- PENDIENTE: transcribir las columnas del Excel del 2026-09-18 -->

- Pais: **EC Ecuador**
- Reporte: `cargasIngresos` (Cargas - Ingresos)
- Nomenclatura: NANDINA
- Ultimo dato conocido: 31/07/2026
- Nombres esperados: Consignatario / Shipper

Filas: pendiente. Registros: pendiente. Columnas: **33** (muestra del 2026-09-18, 07/2026, sin filtro de partida porque el reporte no lo admite; el `8544` del nombre del archivo es solo el rotulo del job; se guardo el conteo, no los nombres).

| # | Column | Example |
|---|---|---|
| 1 | pendiente | pendiente |

#### Reading this correctly

- Manifiesto sin campo de partida: se filtra por Descripcion o Marcas.
- Trae BL Master, Consolidador y RUC del consignatario.
- En la muestra, 1 de cada 3 consignatarios era logistica.
- Pendiente: completar despues de correr `inspect_download.py` sobre un Excel real.

### PA / cargasMaritimasIngresos

<!-- PENDIENTE: medicion en vivo -->

- Pais: **PA Panamá**
- Reporte: `cargasMaritimasIngresos` (Cargas Marítimas - Ingresos)
- Nomenclatura: SAC
- Ultimo dato conocido: 31/07/2026
- Nombres esperados: Consignatario / ninguno

Filas: pendiente. Registros: pendiente. Columnas: pendiente.

| # | Column | Example |
|---|---|---|
| 1 | pendiente | pendiente |

#### Reading this correctly

- Pendiente: completar despues de correr `inspect_download.py` sobre un Excel real.

### VE / cargasIngresos

<!-- PENDIENTE: medicion en vivo -->

- Pais: **VE Venezuela**
- Reporte: `cargasIngresos` (Cargas - Ingresos)
- Nomenclatura: NANDINA
- Ultimo dato conocido: 31/08/2025
- Nombres esperados: Consignatario / Shipper

Filas: pendiente. Registros: pendiente. Columnas: pendiente.

| # | Column | Example |
|---|---|---|
| 1 | pendiente | pendiente |

#### Reading this correctly

- Pendiente: completar despues de correr `inspect_download.py` sobre un Excel real.

### UY / cargasMaritimas

<!-- PENDIENTE: medicion en vivo -->

- Pais: **UY Uruguay**
- Reporte: `cargasMaritimas` (Cargas Marítimas)
- Nomenclatura: Codigo NCM
- Ultimo dato conocido: 11/07/2024
- Nombres esperados: Consignatario (B/L) / Remitente

Filas: pendiente. Registros: pendiente. Columnas: pendiente.

| # | Column | Example |
|---|---|---|
| 1 | pendiente | pendiente |

#### Reading this correctly

- Pendiente: completar despues de correr `inspect_download.py` sobre un Excel real.

### UY / cargasAereas

<!-- PENDIENTE: medicion en vivo -->

- Pais: **UY Uruguay**
- Reporte: `cargasAereas` (Cargas Aéreas)
- Nomenclatura: Codigo NCM
- Ultimo dato conocido: no relevado
- Nombres esperados: unknown / unknown

Filas: pendiente. Registros: pendiente. Columnas: pendiente.

| # | Column | Example |
|---|---|---|
| 1 | pendiente | pendiente |

#### Reading this correctly

- Pendiente: completar despues de correr `inspect_download.py` sobre un Excel real.

### UY / cargasTerrestres

<!-- PENDIENTE: medicion en vivo -->

- Pais: **UY Uruguay**
- Reporte: `cargasTerrestres` (Cargas Terrestres)
- Nomenclatura: Codigo NCM
- Ultimo dato conocido: no relevado
- Nombres esperados: unknown / unknown

Filas: pendiente. Registros: pendiente. Columnas: pendiente.

| # | Column | Example |
|---|---|---|
| 1 | pendiente | pendiente |

#### Reading this correctly

- Pendiente: completar despues de correr `inspect_download.py` sobre un Excel real.

### GT / cargasIngresos

<!-- PENDIENTE: medicion en vivo -->

- Pais: **GT Guatemala**
- Reporte: `cargasIngresos` (Cargas - Ingresos)
- Nomenclatura: SAC
- Ultimo dato conocido: 30/09/2019
- Nombres esperados: Consignatario / Shipper

Filas: pendiente. Registros: pendiente. Columnas: pendiente.

| # | Column | Example |
|---|---|---|
| 1 | pendiente | pendiente |

#### Reading this correctly

- Pendiente: completar despues de correr `inspect_download.py` sobre un Excel real.

### MX / cargasTotalesIngresos

<!-- PENDIENTE: medicion en vivo -->

- Pais: **MX México**
- Reporte: `cargasTotalesIngresos` (Cargas Totales - Ingresos)
- Nomenclatura: Codigo SA
- Ultimo dato conocido: 31/05/2026
- Nombres esperados: Importador / Proveedor

Filas: pendiente. Registros: pendiente. Columnas: pendiente.

| # | Column | Example |
|---|---|---|
| 1 | pendiente | pendiente |

#### Reading this correctly

- Pendiente: completar despues de correr `inspect_download.py` sobre un Excel real.

### MX / cargasTotalesSalidas

<!-- PENDIENTE: medicion en vivo -->

- Pais: **MX México**
- Reporte: `cargasTotalesSalidas` (Cargas Totales - Salidas)
- Nomenclatura: Codigo SA
- Ultimo dato conocido: 31/05/2026
- Nombres esperados: Exportador / Comprador

Filas: pendiente. Registros: pendiente. Columnas: pendiente.

| # | Column | Example |
|---|---|---|
| 1 | pendiente | pendiente |

#### Reading this correctly

- Pendiente: completar despues de correr `inspect_download.py` sobre un Excel real.

### BR / cargasMaritimasSalidas

<!-- PENDIENTE: transcribir las columnas del Excel del 2026-09-18 -->

- Pais: **BR Brasil**
- Reporte: `cargasMaritimasSalidas` (Cargas Marítimas - Salidas)
- Nomenclatura: Codigo NCM
- Ultimo dato conocido: 30/11/2023 (congelada)
- Nombres esperados: Shipper / Consignatario

Filas: pendiente. Registros: pendiente. Columnas: **32** (muestra del 2026-09-18, partida 8544, 11/2023; se guardo el conteo, no los nombres).

| # | Column | Example |
|---|---|---|
| 1 | pendiente | pendiente |

#### Reading this correctly

- Lado exportador del manifiesto: `Shipper` es el exportador y `Consignatario` la contraparte. Trae `Notify` y `Forwarder`.
- En la muestra medida, 2 de cada 3 consignatarios eran logisticas: no son el comprador.
- Datos de contacto de ambas partes, como en Ingresos: no redistribuir.
- Pendiente: completar despues de correr `inspect_download.py` sobre un Excel real.

### PA / cargasMaritimasSalidas

<!-- PENDIENTE: medicion en vivo -->

- Pais: **PA Panamá**
- Reporte: `cargasMaritimasSalidas` (Cargas Marítimas - Salidas)
- Nomenclatura: SAC
- Ultimo dato conocido: no relevado
- Nombres esperados: unknown / unknown

Filas: pendiente. Registros: pendiente. Columnas: pendiente.

| # | Column | Example |
|---|---|---|
| 1 | pendiente | pendiente |

#### Reading this correctly

- Pendiente: completar despues de correr `inspect_download.py` sobre un Excel real.

### US / cargasMaritimasSalidas

<!-- PENDIENTE: medicion en vivo -->

- Pais: **US Estados Unidos**
- Reporte: `cargasMaritimasSalidas` (Cargas Marítimas - Salidas)
- Nomenclatura: Codigo SA
- Ultimo dato conocido: no relevado
- Nombres esperados: unknown / unknown

Filas: pendiente. Registros: pendiente. Columnas: pendiente.

| # | Column | Example |
|---|---|---|
| 1 | pendiente | pendiente |

#### Reading this correctly

- Pendiente: completar despues de correr `inspect_download.py` sobre un Excel real.

### BR / cargasHistoricoIngresos

<!-- PENDIENTE: transcribir las columnas del Excel del 2026-09-18 -->

- Pais: **BR Brasil**
- Reporte: `cargasHistoricoIngresos` (Cargas Histórico - Ingresos)
- Nomenclatura: Codigo NCM
- Ultimo dato conocido: 31/01/2020 (congelada)
- Nombres esperados: Consignatario / ninguno

Filas: pendiente. Registros: pendiente. Columnas: **10** (muestra del 2026-09-18, partida 8544, 01/2020; se guardo el conteo, no los nombres).

| # | Column | Example |
|---|---|---|
| 1 | pendiente | pendiente |

#### Reading this correctly

- Se arma como declaracion, no como manifiesto: Aduana, Estado, NCM de 8 digitos, todos los transportes.
- En la muestra el 99% de los consignatarios eran empresas: funciona como importador real. No nombra contraparte.
- Pendiente: completar despues de correr `inspect_download.py` sobre un Excel real.

### BR / cargasHistoricoSalidas

<!-- PENDIENTE: medicion en vivo -->

- Pais: **BR Brasil**
- Reporte: `cargasHistoricoSalidas` (Cargas Histórico - Salidas)
- Nomenclatura: Codigo NCM
- Ultimo dato conocido: 31/07/2018 (congelada)
- Nombres esperados: Shipper / ninguno

Filas: pendiente. Registros: pendiente. Columnas: pendiente.

| # | Column | Example |
|---|---|---|
| 1 | pendiente | pendiente |

#### Reading this correctly

- Formulario leido el 2026-09-18, sin Excel: mismo formato que Historico Ingresos, del lado exportador.
- Pendiente: completar despues de correr `inspect_download.py` sobre un Excel real.

### EC / cargasSalidas

<!-- PENDIENTE: medicion en vivo -->

- Pais: **EC Ecuador**
- Reporte: `cargasSalidas` (Cargas - Salidas)
- Nomenclatura: NANDINA
- Ultimo dato conocido: no relevado
- Nombres esperados: unknown / unknown

Filas: pendiente. Registros: pendiente. Columnas: pendiente.

| # | Column | Example |
|---|---|---|
| 1 | pendiente | pendiente |

#### Reading this correctly

- Pendiente: completar despues de correr `inspect_download.py` sobre un Excel real.
