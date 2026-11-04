# Qué trae cada base: vitalidad y campos clave

La pregunta práctica antes de prometer nada: **¿esta base sigue viva, y trae el
campo que necesito?** Este archivo la contesta de un vistazo.

Derivado de las columnas medidas en `columns-latam.md` y de las fechas de corte de
`entities-latam.md`. Cada ✅ significa que la columna se vio en un archivo real
descargado, no que el formulario la ofrezca. Fecha de derivación: 2026-09-02, con
las filas de la segunda pasada del **2026-09-18** agregadas (marcadas *2ª pasada*).

La segunda pasada leyó el período precargado de cada formulario y bajó una muestra
chica (partida 8544 donde el formulario la admite, un mes) donde se pudo. Guardó el conteo de columnas, el corte y
las notas en `catalog.json`, pero **no la lista de columnas por nombre**, así que en
sus filas hay campos que quedan en **?** (no consta) hasta que alguien vuelva a
correr `inspect_download.py` sobre el Excel.

## Cómo leer la vitalidad

| Etiqueta | Criterio | Qué significa en la práctica |
|---|---|---|
| **Viva** | último dato dentro de los 4 meses | Sirve para consultas del año en curso |
| **Rezagada** | entre 4 y 18 meses | Sirve para histórico, no para "este año" |
| **Congelada** | más de 18 meses | Solo histórico. Pedirle datos recientes devuelve vacío y **parece un error de filtro** |

**No hace falta precisión acá.** La pregunta es si sirve para consultas actuales, no cuál es el mes exacto del corte. Dos búsquedas alcanzan para decidirlo; ver `coverage.md`.

Las congeladas son las que más confunden: el formulario acepta el período, la consulta corre, y
volvés con cero filas. Avisale al usuario **antes** de descargar, no después.

## La matriz

Importaciones salvo donde se aclare. `Prov.` es la contraparte extranjera
(`Proveedor` / `Shipper`): la columna que contesta *a quién le compra*.

En las celdas: **✅** la columna se vio en un archivo real, **⚠️** está pero con
alguna salvedad, **no** no existe en ese reporte, **?** no consta en lo que se
registró de la medición.

| País | Reporte | Vitalidad | Último dato | Cols | FOB | CIF | Importador | Prov. | Incoterm | Marca |
|---|---|---|---|---|:--:|:--:|:--:|:--:|:--:|:--:|
| **EC** | importaciones | Viva | 23/08/2026 | 48 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **CR** | importaciones | Viva | 16/08/2026 | 48 | ✅ | ✅ | ✅ | ✅ | no | ✅ |
| **CL** | importaciones | Viva | 30/06/2026 | 40 | ✅ | ✅ | ✅ | no | ✅ | ✅ |
| **PE** | importaciones | Viva | 22/08/2026 | 31 | ✅ | ✅ | ✅ | ✅ | no | ✅ |
| **BO** | importaciones | Viva | 31/07/2026 | 25 | ✅ | ✅ | ✅ | ✅ | ✅ | no |
| **CO** | importaciones | Viva | 31/05/2026 | 45 | ✅ | ✅ | ✅ | ✅ | no | no |
| **PY** | importaciones | Viva | 31/07/2026 | 42 | ✅ | ✅ | ⚠️ | ⚠️ | no | no |
| **AR** | impo detalladas | Viva | 31/07/2026 | 36 | ✅ | ✅ | ✅ | no | ⚠️ | ✅ |
| **UY** | importaciones | Viva | 01/09/2026 | 35 | ✅ | ⚠️ | ✅ | no | no | no |
| **PA** | importaciones | Viva | 20/08/2026 | 30 | ✅ | ✅ | ✅ | ✅ | no | no |
| **NI** | impo detalladas | Viva | 31/07/2026 | 27 | ✅ | ✅ | ✅ | ✅ | no | no |
| **DO** | impo detalladas | Viva | 31/07/2026 | 27 | ✅ | ✅ | ✅ | ✅ | no | no |
| **BR** | importaciones | Viva | al día | 12 | ✅ | no | no | no | no | no |
| **HN** | importaciones | Rezagada | 31/03/2026 | 8 | no | ✅ | no | no | no | no |
| **PR** | importaciones | Rezagada | 31/07/2025 | 11 | no | ✅ | no | no | no | no |
| **SV** | importaciones | Rezagada | 30/06/2025 | 8 | no | ✅ | no | no | no | no |
| **VE** | importaciones | Congelada | 31/08/2024 | 21 | no | ✅ | ✅ | no | no | no |
| **BR** | cargas marít. ing. | Congelada | 30/11/2023 | 34 | no | no | ⚠️ | ⚠️ | no | no |
| **GT** | impo detalladas | Congelada | 31/12/2021 | 17 | ✅ | ✅ | no | no | no | no |
| **MX** | importaciones | Congelada | 30/11/2021 | 29 | no | ✅ | no | no | ⚠️ | no |
| **EC** | cargas ingresos *(2ª pasada)* | Viva | 31/07/2026 | 33 | ? | ? | ⚠️ | ⚠️ | ? | ? |
| **EC** | histórico impo *(2ª pasada)* | Congelada | 31/12/2017 | 48 | ✅ | ✅ | ✅ | ⚠️ | no | ✅ |
| **BR** | cargas hist. ing. *(2ª pasada)* | Congelada | 31/01/2020 | 10 | ? | ? | ⚠️ | no | ? | ? |

### Lado exportador

| País | Reporte | Vitalidad | Último dato | Cols | FOB | CIF | Exportador | Comprador | Incoterm | Marca |
|---|---|---|---|---|:--:|:--:|:--:|:--:|:--:|:--:|
| **AR** | exportaciones | Viva | 31/07/2026 | 9 | ✅ | no | ❌ | no | no | no |
| **AR** | expo detalladas | Viva | 31/07/2026 | 31 | ✅ | no | ⚠️ | no | ⚠️ | ✅ |
| **EC** | exportaciones *(2ª pasada)* | Viva | 06/09/2026 | 45 | ? | ? | ✅ | ✅ | ✅ | ✅ |
| **CL** | exportaciones *(2ª pasada)* | Viva | 30/06/2026 | 29 | ✅ | ✅ | ✅ | no | ⚠️ | ✅ |
| **CO** | exportaciones *(2ª pasada)* | Viva | 31/07/2026 | 28 | ✅ | no | ✅ | ✅ | ? | ? |
| **BO** | exportaciones *(2ª pasada)* | Viva | 31/08/2026 | 23 | ? | ? | ✅ | ✅ | ✅ | ? |
| **BR** | cargas marít. sal. *(2ª pasada)* | Congelada | 30/11/2023 | 32 | ? | ? | ⚠️ | ⚠️ | ? | ? |

**AR Exportaciones no tiene columna `Exportador`, ni vacía ni nada, no existe.** La variante Detalladas sí la trae, pero con `No disponible` en el 100% de las filas. Las dos son inútiles para atribuir a una empresa; la diferencia es que la Detallada parece que podría haber servido.

#### Exportaciones con datos confirmados, columnas sin documentar

Una corrida de cobertura del 2026-09-04 bajó estas muestras con la partida 8544 y
registró filas y registros en `corrida-catalogo/manifest.json`, pero los Excel no se
conservaron y nunca se inspeccionaron las columnas. Así que de estas bases sabemos
**que están vivas y cuánto trae una partida chica**, pero no qué campos tienen. No
llevan ✅ en ninguna columna hasta que alguien vuelva a bajar el archivo. Ecuador
estaba en esta tabla y salió: la segunda pasada le contó 45 columnas (fila de
arriba; la corrida del 2026-09-04 había dado 100 filas y 60 registros).

| País | Reporte | Filas | Registros | Filas/reg | Qué se sabe |
|---|---|---:|---:|---:|---|
| **CR** | exportaciones | 1.893 | 359 | 5,27 | viva |
| **NI** | expo detalladas | 454 | 454 | 1,00 | viva |
| **PE** | exportaciones | 26 | 11 | 2,36 | viva |
| **PY** | exportaciones | 23.613 | 384 | **61,49** | viva; nombres *Probable*; **ratio a verificar** |
| **UY** | exportaciones | 12 | 12 | 1,00 | viva |
| **VE** | exportaciones | 4 | 4 | 1,00 | **congelada** en 08/2024 |

El 61,49 de Paraguay es sospechoso: el lado importador del mismo país da 7,07.
Puede ser real (despachos de exportación con decenas de ítems) o puede ser que la
clave `Despacho` no identifique la operación en el reporte de exportación. Hasta
no ver el archivo, no usar ese número para detectar truncamiento en PY.

#### Leídas del formulario el 2026-09-18, sin archivo

La segunda pasada leyó el corte y los filtros de estas, sin bajar muestra. Sirven
para contestar la vitalidad y si nombran empresas; de columnas no se sabe nada.

| País | Reporte | Vitalidad | Último dato | Empresa local | Contraparte | Qué se sabe |
|---|---|---|---|---|---|---|
| **BR** | exportaciones | Viva | 31/08/2026 | no | no | estadística anónima: filtra por Puerto y Estado |
| **BR** | cargas hist. sal. | Congelada | 31/07/2018 | ⚠️ `Shipper` | no | mismo formato que Histórico Ingresos, lado exportador |
| **EC** | histórico expo | Congelada | 31/12/2017 | ✅ | no | |
| **CO** | histórico impo / expo | Congelada | 31/12/2021 | ⚠️ *Probable* | ⚠️ *Probable* | Softrade los rotula `Probable` sin explicar por qué |
| **BO** | histórico impo | Congelada | 30/09/2023 | no | no | anónimo, solo CIF y Kgs |
| **BO** | histórico expo | Congelada | 30/09/2023 | no | no | anónimo, filtra por Departamento |

### Las ⚠️ , una por una

- **PY Importador / Proveedor**: las columnas se llaman `Probable Importador` y
  `Probable Proveedor`. Softrade no explica el "Probable", y el archivo trae el
  **RUC** al lado del nombre, lo que apunta a una empresa registrada. Esa palabra tiene que
  llegarle al usuario cada vez que se entrega data paraguaya.
- **AR Incoterm**: no existe una columna `Incoterm`, pero `Condición de Venta`
  cumple la misma función (FOB, CIF, CFR...).
- **MX Incoterm**: igual que Argentina, la columna es `Condición de Venta`.
- **UY CIF**: no trae CIF. Trae `U$S VNA` (Valor en Aduana), que es parecido pero
  no idéntico. Sí trae `U$S FOB`, `Flete` y `Seguro`, así que el CIF se puede
  reconstruir sumando.
- **BR Cargas: Importador / Proveedor**: las columnas son `Consignatario` y
  `Shipper`, propias del manifiesto de embarque, no de la declaración aduanera. Es
  la contraparte real, pero el nombre no coincide y además **trae dirección, email
  y teléfono de ambos**, que ningún otro reporte da.
- **BR Cargas Marítimas Salidas: Exportador / Comprador**: del lado exportador las
  columnas se invierten (`Shipper` es el exportador, `Consignatario` la
  contraparte), y trae `Notify` y `Forwarder`. En la muestra medida, **2 de cada 3
  consignatarios eran logísticas**, no el comprador. Mismos datos de contacto que
  Ingresos: no redistribuir.
- **EC Cargas Ingresos: Importador / Proveedor**: `Consignatario` y `Shipper`,
  más `BL Master`, `Consolidador` y el RUC del consignatario. En la muestra, 1 de
  cada 3 consignatarios era una logística. No tiene campo de partida (ni en el
  formulario ni en el Excel): se filtra por Descripción o Marcas, así que la
  muestra no está acotada a la partida 8544 aunque el archivo lo diga en el nombre.
- **BR Cargas Histórico Ingresos: Importador**: se llama `Consignatario`, pero el
  reporte se arma como una declaración (Aduana, Estado, NCM de 8 dígitos, todos los
  transportes) y en la muestra el 99% eran empresas: funciona como importador real.
  No nombra contraparte.
- **EC Histórico impo: Proveedor**: el Excel trae `Proveedor`, pero el formulario
  no permite filtrar por él. Tiene 48 columnas como la base actual, pero **no es
  el mismo layout**: trae `Refrendo`, `Nro. DAU`, `Base Imponible U$S`,
  `Advalorem`, `Aforador` y `Actividad Principal Importador`, y no trae
  `Incoterm`, `Modelo de Mercadería`, `Año producido` ni `Bill of Lading`. Los ✅
  de esa fila salen de leer los encabezados del Excel de la muestra
  (`FOB U$S`, `U$S CIF`, `Importador`, `Proveedor`, `Marca`).
- **CL exportaciones: Incoterm**: no hay `Incoterm`, pero `Cláusula VTA` (la
  condición de venta) cumple la misma función, como en Argentina y México.

## Lo que se lee de la matriz

**Ecuador es la base más completa del sistema.** Es la única que marca las seis
columnas: 48 campos, viva a agosto de 2026, nombra ambas puntas, y trae Incoterm y
Marca. Cuando alguien necesita el dato más rico posible y el país no está fijado de
antemano, Ecuador es la respuesta.

**Incoterm es rarísimo.** Del lado importador solo lo dan **Ecuador, Bolivia y
Chile** de forma explícita. Argentina y México lo tienen disfrazado de `Condición
de Venta`. Los otros 15 reportes de importación medidos el 2026-09-02 no lo tienen
de ninguna manera. Del lado exportador lo traen Ecuador y Bolivia, Chile como
`Cláusula VTA` y Argentina (Exportaciones Detalladas) como `Condición de Venta`.
Si el pedido depende del Incoterm, la lista de países posibles es esa entre lo
medido; Colombia Exportaciones queda en **?** y el resto de las exportaciones no
se midió.

**Marca solo la dan cinco:** Ecuador, Costa Rica, Chile, Perú y Argentina.

**FOB y CIF no vienen juntos siempre.** Los reportes chicos (HN, PR, SV, 8 a 11
columnas) traen CIF y nada más, así que no se puede separar mercadería de flete.
Brasil Importaciones es el caso inverso: FOB sin CIF. Uruguay no trae ninguno de
los dos con ese nombre.

**El tamaño de la economía no predice nada.** Honduras y El Salvador dan 8
columnas; Costa Rica y Ecuador dan 48. México, la segunda economía de la región,
da 29 columnas anónimas y congeladas en 2021.

**Las seis bases de importación anónimas** (GT, HN, PR, SV, y BR y MX en su
forma Importaciones) solo contestan preguntas de producto, flujo y precio. Nunca
preguntas de empresa. Para BR y MX hay que ir a Cargas.

## Lo que falta medir

`catalog.json` tiene **32 reportes con columnas medidas** (`columns_measured` no
nulo). Esta matriz muestra 30: las 19 importaciones latinoamericanas, Cargas
Marítimas de Brasil, las dos exportaciones de Argentina y las 8 de la segunda
pasada. Los otros dos son AR Importaciones (13 columnas, `columns.md`) y AR Otras
Operaciones (30, `catalog.md`), que no tienen fila en esta matriz; sus columnas
están en esos dos archivos. Otras 6 exportaciones (la tabla *Exportaciones con datos
confirmados*) tienen filas y registros pero no columnas, así que no cuentan como
medidas. Falta todo lo demás, y el orden para completarlo está en `coverage.md`.
Los huecos más grandes, por si alguien pregunta:

- **Las exportaciones salvo Argentina, Bolivia, Chile, Colombia y Ecuador.** La
  columna `Comprador` (a quién le vende) ya se vio en un archivo en Ecuador,
  Colombia y Bolivia; en el resto de los 8 países que la documentan en
  `entities-latam.md` sigue sin verse.
- **La lista de columnas por nombre de las 8 mediciones de la segunda pasada**
  (los **?** de arriba): los Excel quedaron en `runs/cobertura-2026-09-18/downloads/`,
  que no se versiona.
- **MX Cargas Totales**, que es la única data mexicana viva y con nombres.
- **US Cargas Marítimas**, viva a julio 2026.
- **Los 16 países de Asia y África que nombran empresas** (10 de Asia, 6 de
  África), y Ucrania, la única de Europa. Cero columnas medidas.
- **Cinco familias enteras** que nunca se abrieron: Cargas Totales, Cargas
  Aéreas/Terrestres, Zona Franca/Libre, Tránsitos, Totalizadas. Histórico, Cargas
  Ingresos/Salidas y Cargas Histórico ya tienen al menos un reporte medido (segunda
  pasada); les faltan los demás países y lados.

El objetivo completo, reporte por reporte y en orden, está en
`corrida-catalogo/manifest.json` (112 jobs), pero ese manifiesto maestro es la
referencia, no donde se avanza. La corrida se partió en dos sub-corridas,
`corrida-catalogo/split-claude/` y `corrida-catalogo/split-chatgpt/`, y el trabajo
se registra en sus manifiestos (`run_state.py next corrida-catalogo/split-claude`
da el próximo de esa mitad). Los resultados se copian al maestro a mano al final.
Esta tabla queda para lo **medido**, no para el pendiente: cuando se mide un
reporte nuevo, **se agrega su fila acá además de a `columns-*.md`**, y se tilda el
job en el sub-manifiesto que lo tenía. Esta tabla es la que se consulta antes de
prometerle un campo a alguien.
