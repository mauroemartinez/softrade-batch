# Qué trae cada base: vitalidad y campos clave

La pregunta práctica antes de prometer nada: **¿esta base sigue viva, y trae el
campo que necesito?** Este archivo la contesta de un vistazo.

Derivado de las columnas medidas en `columns-latam.md` y de las fechas de corte de
`entities-latam.md`. Cada ✅ significa que la columna se vio en un archivo real
descargado, no que el formulario la ofrezca. Fecha de derivación: 2026-09-02.

## Cómo leer la vitalidad

| Etiqueta | Criterio | Qué significa en la práctica |
|---|---|---|
| **Viva** | último dato dentro de los 4 meses | Sirve para consultas del año en curso |
| **Rezagada** | entre 4 y 18 meses | Sirve para histórico, no para "este año" |
| **Congelada** | más de 18 meses | Solo histórico. Pedirle datos recientes devuelve vacío y **parece un error de filtro** |

**No hace falta precisión acá.** La pregunta es si sirve para consultas actuales, no cuál es el mes exacto del corte. Dos búsquedas alcanzan para decidirlo; ver `coverage.md`.

Las congeladas son la trampa: el formulario acepta el período, la consulta corre, y
volvés con cero filas. Avisale al usuario **antes** de descargar, no después.

## La matriz

Importaciones salvo donde se aclare. `Prov.` es la contraparte extranjera
(`Proveedor` / `Shipper`): la columna que contesta *a quién le compra*.

| País | Reporte | Vitalidad | Último dato | Cols | FOB | CIF | Importador | Prov. | Incoterm | Marca |
|---|---|---|---|---|:--:|:--:|:--:|:--:|:--:|:--:|
| **EC** | importaciones | Viva | 23/08/2026 | 48 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **CR** | importaciones | Viva | 16/08/2026 | 48 | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| **CL** | importaciones | Viva | 30/06/2026 | 40 | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| **PE** | importaciones | Viva | 22/08/2026 | 31 | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| **BO** | importaciones | Viva | 31/07/2026 | 25 | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| **CO** | importaciones | Viva | 31/05/2026 | 45 | ✅ | ✅ | ✅ | ✅ | — | — |
| **PY** | importaciones | Viva | 31/07/2026 | 42 | ✅ | ✅ | ⚠️ | ⚠️ | — | — |
| **AR** | impo detalladas | Viva | 31/07/2026 | 36 | ✅ | ✅ | ✅ | — | ⚠️ | ✅ |
| **UY** | importaciones | Viva | 01/09/2026 | 35 | ✅ | ⚠️ | ✅ | — | — | — |
| **PA** | importaciones | Viva | 20/08/2026 | 30 | ✅ | ✅ | ✅ | ✅ | — | — |
| **NI** | impo detalladas | Viva | 31/07/2026 | 27 | ✅ | ✅ | ✅ | ✅ | — | — |
| **DO** | impo detalladas | Viva | 31/07/2026 | 27 | ✅ | ✅ | ✅ | ✅ | — | — |
| **BR** | importaciones | Viva | al día | 12 | ✅ | — | — | — | — | — |
| **HN** | importaciones | Rezagada | 31/03/2026 | 8 | — | ✅ | — | — | — | — |
| **PR** | importaciones | Rezagada | 31/07/2025 | 11 | — | ✅ | — | — | — | — |
| **SV** | importaciones | Rezagada | 30/06/2025 | 8 | — | ✅ | — | — | — | — |
| **VE** | importaciones | Congelada | 31/08/2024 | 21 | — | ✅ | ✅ | — | — | — |
| **BR** | cargas marít. ing. | Congelada | 30/11/2023 | 34 | — | — | ⚠️ | ⚠️ | — | — |
| **GT** | impo detalladas | Congelada | 31/12/2021 | 17 | ✅ | ✅ | — | — | — | — |
| **MX** | importaciones | Congelada | 30/11/2021 | 29 | — | ✅ | — | — | ⚠️ | — |

### Lado exportador

| País | Reporte | Vitalidad | Último dato | Cols | FOB | CIF | Exportador | Comprador | Incoterm | Marca |
|---|---|---|---|---|:--:|:--:|:--:|:--:|:--:|:--:|
| **AR** | exportaciones | Viva | 31/07/2026 | 9 | ✅ | — | ❌ | — | — | — |
| **AR** | expo detalladas | Viva | 31/07/2026 | 31 | ✅ | — | ⚠️ | — | ⚠️ | ✅ |

**AR Exportaciones no tiene columna `Exportador`, ni vacía ni nada — no existe.** La variante Detalladas sí la trae, pero con `No disponible` en el 100% de las filas. Las dos son inútiles para atribuir a una empresa; la diferencia es que la Detallada parece que podría haber servido.

### Las ⚠️ , una por una

- **PY Importador / Proveedor** — las columnas se llaman `Probable Importador` y
  `Probable Proveedor`. Son **inferidas, no declaradas**. Esa palabra tiene que
  llegarle al usuario cada vez que se entrega data paraguaya.
- **AR Incoterm** — no existe una columna `Incoterm`, pero `Condición de Venta`
  cumple la misma función (FOB, CIF, CFR...).
- **MX Incoterm** — igual que Argentina, la columna es `Condición de Venta`.
- **UY CIF** — no trae CIF. Trae `U$S VNA` (Valor en Aduana), que es parecido pero
  no idéntico. Sí trae `U$S FOB`, `Flete` y `Seguro`, así que el CIF se puede
  reconstruir sumando.
- **BR Cargas: Importador / Proveedor** — las columnas son `Consignatario` y
  `Shipper`, propias del manifiesto de embarque, no de la declaración aduanera. Es
  la contraparte real, pero el nombre no coincide y además **trae dirección, email
  y teléfono de ambos**, que ningún otro reporte da.

## Lo que se lee de la matriz

**Ecuador es la base más completa del sistema.** Es la única que marca las seis
columnas: 48 campos, viva a agosto de 2026, nombra ambas puntas, y trae Incoterm y
Marca. Cuando alguien necesita el dato más rico posible y el país no está fijado de
antemano, Ecuador es la respuesta.

**Incoterm es rarísimo.** Solo lo dan **Ecuador, Bolivia y Chile** de forma
explícita. Argentina y México lo tienen disfrazado de `Condición de Venta`. Los
otros 15 reportes no lo tienen de ninguna manera. Si el pedido depende del
Incoterm, la lista de países posibles es esa y nada más.

**Marca solo la dan cinco:** Ecuador, Costa Rica, Chile, Perú y Argentina.

**FOB y CIF no vienen juntos siempre.** Los reportes chicos (HN, PR, SV, 8 a 11
columnas) traen CIF y nada más, así que no se puede separar mercadería de flete.
Brasil Importaciones es el caso inverso: FOB sin CIF. Uruguay no trae ninguno de
los dos con ese nombre.

**El tamaño de la economía no predice nada.** Honduras y El Salvador dan 8
columnas; Costa Rica y Ecuador dan 48. México, la segunda economía de la región,
da 29 columnas anónimas y congeladas en 2021.

**Las cuatro bases anónimas** (GT, HN, PR, SV, más BR y MX en su forma
Importaciones) solo contestan preguntas de producto, flujo y precio. Nunca
preguntas de empresa. Para BR y MX hay que ir a Cargas.

## Lo que falta medir

Esta matriz cubre **20 reportes**: las 19 importaciones latinoamericanas más
Cargas Marítimas de Brasil. Falta todo lo demás, y el orden para completarlo está
en `coverage.md`. Los huecos más grandes, por si alguien pregunta:

- **Todas las exportaciones salvo Argentina**, cuyos dos reportes ya están medidos
  y arriba. La columna `Comprador` (a quién le vende) está documentada en
  `entities-latam.md` como existente en 8 países, pero nunca se vio en un archivo.
- **MX Cargas Totales**, que es la única data mexicana viva y con nombres.
- **US Cargas Marítimas**, viva a julio 2026.
- **Los 17 países de Asia y África que nombran empresas.** Cero columnas medidas.
- **Ocho familias enteras** que nunca se abrieron: Histórico, Cargas
  Ingresos/Salidas, Cargas Totales, Cargas Aéreas/Terrestres, Cargas Histórico,
  Zona Franca/Libre, Tránsitos, Totalizadas.

Cuando se mida un reporte nuevo, **agregá su fila acá además de a `columns.md`**.
Esta tabla es la que se consulta antes de prometerle un campo a alguien.
