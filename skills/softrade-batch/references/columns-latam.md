# Columnas por pais, medidas sobre archivos reales

Cada fila sale de una muestra descargada el 2026-09-02 filtrando la **partida 8544
de 4 digitos** sobre el ultimo mes cargado de cada pais. Las muestras viven en
`ejemplos_queries/` y no se publican, porque traen nombres de empresas y datos
licenciados de Softrade. Esto es lo que se deriva de ellas.

## Resumen

| Pais | Reporte | Filas | Registros | Filas/reg | Columnas | Clave de registro |
|---|---|---|---|---|---|---|
| **AR** | importaciones detalladas | 25.061 | 3.180 | 7.88 | **36** | `Identificador` |
| **BO** | importaciones | 2.542 | 2.542 | 1.00 | **25** | `Identificador` |
| **BR** | cargas maritimas ingresos | 291 | 291 | 1.00 | **34** | `Ordinal` |
| **BR** | importaciones | 2.666 | 2.666 | 1.00 | **12** | `Operación` |
| **CL** | importaciones | 5.013 | 2.622 | 1.91 | **40** | `Ordinal` |
| **CO** | importaciones | 4.214 | 4.214 | 1.00 | **45** | `Nro. Declaración` |
| **CR** | importaciones | 3.499 | 756 | 4.63 | **48** | `Ordinal` |
| **DO** | importaciones detalladas | 3.637 | 3.637 | 1.00 | **27** | `Identificador` |
| **EC** | importaciones | 3.391 | 881 | 3.85 | **48** | `Identificador` |
| **GT** | importaciones detalladas | 4.310 | 1.013 | 4.25 | **17** | `Identificador` |
| **HN** | importaciones | 161 | 161 | 1.00 | **8** | `Identificador` |
| **MX** | importaciones | 84.596 | 84.596 | 1.00 | **29** | `Ordinal` |
| **NI** | importaciones detalladas | 863 | 863 | 1.00 | **27** | `Identificador` |
| **PA** | importaciones | 771 | 771 | 1.00 | **30** | `Ordinal` |
| **PE** | importaciones | 7.400 | 2.072 | 3.57 | **31** | `DUA` |
| **PR** | importaciones | 35 | 35 | 1.00 | **11** | `Identificador` |
| **PY** | importaciones | 3.505 | 496 | 7.07 | **42** | `Despacho` |
| **SV** | importaciones | 153 | 153 | 1.00 | **8** | `Identificador` |
| **UY** | importaciones | 49 | 40 | 1.23 | **35** | `DUA` |
| **VE** | importaciones | 513 | 513 | 1.00 | **21** | `Identificador` |

## Que mirar de esta tabla

**Las columnas van de 8 a 48.** Honduras y El Salvador dan 8. Costa Rica y Ecuador
dan 48, Colombia 45, Paraguay 42, Chile 40. No hay relacion entre el tamano de la
economia y la riqueza del dato.

**La relacion filas por registro va de 1,00 a 7,88.** Algunos paises entregan una
fila por declaracion y otros una fila por item. Nunca estimes registros desde filas
ni al reves.

**Cada pais llama distinto a la clave de la declaracion.** `Identificador`,
`Nro. Declaracion`, `DUA`, `Despacho`, `Ordinal`, `Operacion`. `inspect_download.py`
los reconoce a todos.

### Advertencia sobre Mexico

El `Ordinal` mexicano trae el numero de item pegado al del pedimento, con la forma
`06255386-0001`. Contar `Ordinal` distintos devuelve la cantidad de filas, no de
declaraciones, asi que el conteo de registros de Mexico esta inflado y la deteccion
de truncamiento no es confiable ahi. Para contar operaciones mexicanas hay que
cortar el sufijo despues del guion.

## Columnas completas por pais

### AR / importaciones detalladas

36 columnas.

`Identificador | Item | Fecha | Tipo de Dato | NCM-SIM | Importador | Localidad | Destinación | Aduana | Via Transporte | País de Origen | País de Procedencia | U$S Unitario | U$S FOB | Flete U$S | Seguro U$S | U$S CIF | Cant. Estad. | Un. Medida Estad. | Cantidad | Unidad de Medida | Kgs. Netos | Kgs. Brutos | Derecho | % Dere. | Acuerdo ALADI | Item.1 | Marca - Sufijos | Cantidad.1 | Unitario Divisa | FOB Divisa | Moneda Divisa | Condición de Venta | Marca o Descripcion | Descripcion Arancelaria | Modelo`

### BO / importaciones

25 columnas.

`Identificador | Item | Fecha | NANDINA | Aduana | Importador | Importador Ruc | País de Origen | Proveedor | País de Proveedor | País de Procedencia | U$S CIF | U$S Unitario | U$S FOB | Kgs. Brutos | Kgs. Netos | Cantidad | Unidad | Flete | Seguro | Transporte | Incoterm | Tipo de Operación | Descripción Arancelaria | Descripción Comercial`

### BR / cargas maritimas ingresos

34 columnas.

`Ordinal | Fecha | Código NCM | País de Origen | País de Destino | Consignatario | Dirección | Email | Teléfono | Shipper | Dirección.1 | Email.1 | Teléfono.1 | Notify | Puerto de Trasbordo | Puerto de Origen | Puerto de Destino | Puerto de Descarga | País de Shipper | País de Trasbordo | Ruta de Origen | Transporte | Kgs. Brutos | Teus | Valor Estimado | Tipo de Contenedor | Descripción | Nombre Transportista | Forwarder | Nombre Buque | Toneladas | Tipo de Carga | Tipo de Servicio | Lugar de Recepción`

### BR / importaciones

12 columnas.

`Operación | Fecha | Código NCM | País de Origen | Puerto | Estado | Unitario FOB | U$S FOB | Cantidad Comercial | Unidad de Medida | Kgs. Brutos | Descripción de Mercadería`

### CL / importaciones

40 columnas.

`Ordinal | item | Fecha | Código SACH | Importador | RUT | Aduana | Vía Transporte | País de Origen | País de Adquisición | FOB Unitario U$S | FOB U$S | Flete U$S | Seguro U$S | U$S CIF | U$S Unitario | Cantidad Comercial | Unidad de Medida | Kgs. Brutos | Valor ADV. | % ADV. | Acuerdo ALADI | Mercadería | Variedad | Marca | Descripción de Mercadería | Observaciones | Transportista | Bandera - Nave | Puerto de Embarque | Puerto de Desembarque | Bultos | Tipo de Bulto | Manifiesto | Fecha Manifiesto | Documento de Transporte | Fec.D.T. | Agente | Incoterm | Documento`

### CO / importaciones

45 columnas.

`Nro. Declaración | Fecha | NANDINA | País de Origen | País de Procedencia | Importador | RUC | Dirección | Ciudad | Email | Proveedor | Dirección.1 | Ciudad.1 | Email.1 | Aduana | Transporte | Transportista | NIT Agente Aduanero | Agente Aduanero | Representante Legal | Factura | Fecha Factura | Manifiesto | Fecha Manifiesto | Nro. Documento Transporte | País de Compra | U$S CIF | CIF Unitario | U$S FOB | FOB Unitario | Flete | Seguro | Kgs. Netos | Kgs. Brutos | Cantidad | Unidad | Bultos | IVA | Arancel | Modalidad | Tipo de Importación | Nro. Aceptación | Fecha Aceptación | Descripción Arancelaria | Descripción Comercial`

### CR / importaciones

48 columnas.

`Ordinal | Item | Fecha | Aduana | Regimen | Modalidad | Importador | Proveedor | Marca | Modelo | Factura | Código SAC | Transporte | País de Origen | País de Procedencia | País de Adquisición | Cantidad Comercial | Unidad de Medida | Volúmen Físico | UVF | Bultos | U$S FOB | U$S FOB Unit. | U$S Flete | U$S Seguro | U$S CIF | U$S Unitario | V. Aduana U$S | Kgs. Netos | Kgs. Brutos | Descripción de Mercadería | Nro. Declaración | Declarante | Nro. Agencia | Agente | Cod. Loc. | Localización | IVA - U$S | % | Ley 6946 U$S | %.1 | DAI U$S | %.2 | PROCOMER U$S | %.3 | S.C. U$S | %.4 | Otros Imp. U$S`

### DO / importaciones detalladas

27 columnas.

`Identificador | Fecha | Item | Fecha de Liquidación | Código SAC | País de Origen | País de Proveedor | Importador | Importador Ruc | Proveedor | Agencia Aduanera | Aduana | Régimen | U$S CIF | U$S FOB | Cantidad | Unidad | Kgs. Netos | RD$ CIF | Total RD$ | Seguro | Flete | Modelo | Color | Descripción Comercial | Descripción Arancelaria | Descripción Capítulo`

### EC / importaciones

48 columnas.

`Identificador | Item | Fecha | NANDINA | Importador | RUC | Dirección | Proveedor | Dirección.1 | País de Origen | País de Embarque | Aduana | Provincia | Régimen | Tipo de Régimen | Transporte | Transportista | Depósito | Agente Afianzado | Agencia Transporte | Nave | Manifiesto | Manifiesto Original | Bill of Lading | Tipo de Aforo | Factura | Fecha Embarque | Fecha Llegada | Fecha Pago | Fecha Salida | U$S CIF | CIF Unitario | U$S FOB | FOB Unitario | Flete | Seguro | Kgs. Netos | Incoterm | Producto | Estado Mercadería | Marca | Modelo de Mercadería | Año producido | Característica | Descripción Arancelaria | Cant. comercial | Unidad comercial | Descripción Comercial`

### GT / importaciones detalladas

17 columnas.

`Período | Identificador | Item | Código SAC | País de Origen | U$S CIF | Tipo de Cambio | Cantidad | Unidad | Unitario CIF | Valor FOB Total | Peso Total | Régimen | Aduana | Descripción | Valor Dai | Porcentaje Dai`

### HN / importaciones

8 columnas.

`Identificador | Fecha | Código SAC | País de Origen | U$S CIF | Kgs. Brutos | Descripción | Descripción Arancelaria`

### MX / importaciones

29 columnas.

`Ordinal | Fecha | Código SA | Régimen | País de Origen | Pais de Adquisición | Aduana | Transporte | País de Destino | Condición de Venta | Val. Com. Mex | Flete Mex | Seguro Mex | Embalaje Mex | Otros Inc. Mex | Val. Adu. Mex | U$S CIF | U$S Unitario | Cantidad | Unidad de Medida | Volúmen Físico | U.V.F. | Kgs. Brutos | Descripción de Mercadería | IVA - Tasa | IVA - U$S | IGI - Tasa | IGI - U$S | Otros - U$S`

### NI / importaciones detalladas

27 columnas.

`Identificador | Número de Operación | Fecha | Código SAC | País de Origen | País de Procedencia | Importador | Importador Ruc | Proveedor | Consignatario | Agencia | RUC Agencia | U$S CIF | U$S FOB | U$S Unitario | Kgs. Brutos | Kgs. Netos | Flete | Seguro | Otros Gastos | Impuestos | Exonerado | Pagado | Cantidad | Unidad | Descripción | Descripción Arancelaria`

### PA / importaciones

30 columnas.

`Ordinal | Dígito Ctrl. | Fecha | Importador | Tipo de Dato | Código SAC | Aduana | Transporte | País de Origen | Puerto | Documento | Cantidad | Unidad | Bultos | U$S FOB | U$S Unitario FOB | Flete | Seguro | U$S CIF | U$S Unitario | ITBMS | ISC | ICDDP | Impuesto de Importación | Impuesto Calculado | Impuesto a Pagar | Kgs. Netos | Kgs. Brutos | Proveedor | Descripción de Mercadería`

### PE / importaciones

31 columnas.

`DUA | Item | Fecha | Importador | Importador Ruc | Régimen | NANDINA | Aduana | Transporte | Transportista | Manifiesto | Conocimiento | Puerto | País de Origen | País de Procedencia | Cantidad | Unidad | Cantidad UVF | Unidad.1 | Bultos | Unidad.2 | U$S FOB | Unitario FOB | U$S CIF | Unitario CIF | Flete | Kgs. Netos | Kgs. Brutos | Proveedor | Marca | Descripción`

### PR / importaciones

11 columnas.

`Identificador | Fecha | Código SAC | País de Origen | U$S CIF | Cantidad | Unidad | Cantidad 2 | Unidad 2 | Descripción | Descripción Arancelaria`

### PY / importaciones

42 columnas.

`Despacho | Item | Fecha Canc. | Fecha Oficialización | Código NCM | País de Origen | País de Procedencia | Probable Importador | RUC | Email | Probable Proveedor | Aduana | Régimen Código | Régimen | Transporte | U$S CIF | U$S FOB | Cantidad | Unidad | Kgs. Brutos | Kgs. Netos | Flete | Seguro | Factura | Estado Operación | Acuerdo | Conocimiento | Canal | Derecho | ISC | Servicio | Renta | IVA | Total | Producto | Estado Mercadería | Descripción Arancelaria | Descripción | Despachante | RUC.1 | Dirección | Email.1`

### SV / importaciones

8 columnas.

`Identificador | Fecha | Código SAC | País de Origen | U$S CIF | Kgs. Netos | Descripción | Descripción Arancelaria`

### UY / importaciones

35 columnas.

`DUA | Fecha | Código NCM | NADISA | País de Origen | País de Procedencia | País de Adquisición | Aduana | U$S FOB | U$S VNA | Cantidad Comercial | Unidad de Medida | Unitario VNA | Kgs. Netos | Kgs. Brutos | Importador | RUC | Cantidad UVF | Unidad UVF | Descripción de Mercadería | Flete | Seguro | % Recargo | % Imaduni | % Brou | Aladi | Exoneración | % Iva | Anticipo IVA | Vía Transporte | Nombre Transportista | Despachante | Estado Mercadería | Depósito | Tipo de Operación`

### VE / importaciones

21 columnas.

`Identificador | Fecha | NANDINA | País de Origen | Importador | País de Procedencia | País de Adquisición | Aduana de Ingreso | Puerto de Entrada | Puerto de Procedencia | Puerto de Desembarque | Bandera | Transporte | Manifiesto | Registro | U$S CIF | Valor CIF (Bol) | Kgs. Brutos | Kgs. Netos | Descripción del Capítulo | Descripción`

