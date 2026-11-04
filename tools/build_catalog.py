#!/usr/bin/env python3
"""Build references/catalog.json from the reference markdown.

catalog.json is the machine-readable single source of truth the query engine
(`preflight.py`, `plan_run.py`) reads instead of parsing ~600 lines of markdown.
This builder keeps its provenance explicit: every fact below is transcribed from a
named section of a `references/*.md` file, and re-running the builder regenerates
the JSON deterministically.

Sources:
  catalog.md          -> which report_types each country offers
  entities-latam.md   -> cutoff, nomenclature, importer/exporter/counterparty names (LatAm)
  entities-world.md   -> same, Asia / Africa / Oceania / Europe
  fields-matrix.md    -> columns_measured, vitality caveats
  columns-latam.md    -> columns_measured (import side, 19 countries + BR cargas)
  columns.md          -> AR import/export column counts
  cargas.md           -> Cargas family names (Consignatario / Shipper / Operador)

Usage:
  python tools/build_catalog.py               writes skills/softrade-batch/references/catalog.json
  python tools/build_catalog.py --check       builds in memory; exit 1 + diff summary if catalog.json is stale
  python tools/build_catalog.py --out PATH    writes somewhere else (with --check: compares against PATH)

meta.catalog_version is "<latest survey date>+<8-hex content hash>": it moves
whenever any entry changes, not only when meta.captured does (a second survey
pass only sets `surveyed` on the entries it touched). meta.captured stays the
base survey date that preflight falls back to for entries without `surveyed`.
"""
import argparse
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "skills", "softrade-batch", "references", "catalog.json")

CAPTURED = "2026-09-02"

# --- report_types: the canonical list, frozen. See docs/handoff-motor-consultas.md
REPORT_TYPES = {
    "import":                  ("Importaciones",                "customs",  "import", False),
    "importDetalladas":        ("Importaciones Detalladas",     "customs",  "import", True),
    "export":                  ("Exportaciones",                "customs",  "export", False),
    "exportDetalladas":        ("Exportaciones Detalladas",     "customs",  "export", True),
    "otrasOperaciones":        ("Otras Operaciones",            "customs",  "both",   False),
    "historicoImport":         ("Histórico Importaciones",      "customs",  "import", False),
    "historicoExport":         ("Histórico Exportaciones",      "customs",  "export", False),
    "cargasIngresos":          ("Cargas - Ingresos",            "cargas",   "import", False),
    "cargasSalidas":           ("Cargas - Salidas",             "cargas",   "export", False),
    "cargasMaritimasIngresos": ("Cargas Marítimas - Ingresos",  "cargas",   "import", False),
    "cargasMaritimasSalidas":  ("Cargas Marítimas - Salidas",   "cargas",   "export", False),
    "cargasHistoricoIngresos": ("Cargas Histórico - Ingresos",  "cargas",   "import", False),
    "cargasHistoricoSalidas":  ("Cargas Histórico - Salidas",   "cargas",   "export", False),
    "cargasTotalesIngresos":   ("Cargas Totales - Ingresos",    "cargas",   "import", False),
    "cargasTotalesSalidas":    ("Cargas Totales - Salidas",     "cargas",   "export", False),
    "cargasMaritimas":         ("Cargas Marítimas",             "cargas",   "import", False),
    "cargasAereas":            ("Cargas Aéreas",                "cargas",   "import", False),
    "cargasTerrestres":        ("Cargas Terrestres",            "cargas",   "import", False),
    "zonaFranca":              ("Zona Franca",                  "zona",     "both",   False),
    "zonaLibreIngresos":       ("Zona Libre - Ingresos",        "zona",     "import", False),
    "zonaLibreSalidas":        ("Zona Libre - Salidas",         "zona",     "export", False),
    "transitos":               ("Tránsitos",                    "transito", "both",   False),
    "importTotalizadas":       ("Importaciones Totalizadas",    "customs",  "import", False),
    "exportTotalizadas":       ("Exportaciones Totalizadas",    "customs",  "export", False),
    "normativa":               ("Normativa",                    "otro",     "n/a",    False),
}

# Aliases: how a user or an AI might name a report -> canonical id. Consumed by
# scripts/_catalog.py; kept here so the mapping ships inside the JSON too.
ALIASES = {
    "importaciones": "import", "impo": "import", "las impo": "import",
    "imports": "import", "importacion": "import",
    "importaciones detalladas": "importDetalladas", "impo detalladas": "importDetalladas",
    "impo det": "importDetalladas", "importaciones detallada": "importDetalladas",
    "detalladas import": "importDetalladas",
    "imports detailed": "importDetalladas", "import detailed": "importDetalladas",
    "exports detailed": "exportDetalladas", "export detailed": "exportDetalladas",
    "exportaciones": "export", "expo": "export", "las expo": "export", "exports": "export",
    "exportaciones detalladas": "exportDetalladas", "expo detalladas": "exportDetalladas",
    "expo det": "exportDetalladas",
    "otras operaciones": "otrasOperaciones",
    "historico importaciones": "historicoImport", "historico impo": "historicoImport",
    "historico exportaciones": "historicoExport", "historico expo": "historicoExport",
    "cargas ingresos": "cargasIngresos", "cargas salidas": "cargasSalidas",
    "cargas maritimas ingresos": "cargasMaritimasIngresos",
    "cargas maritimas salidas": "cargasMaritimasSalidas",
    "cargas maritimas - ingresos": "cargasMaritimasIngresos",
    "cargas maritimas - salidas": "cargasMaritimasSalidas",
    "cargas historico ingresos": "cargasHistoricoIngresos",
    "cargas historico salidas": "cargasHistoricoSalidas",
    "cargas totales ingresos": "cargasTotalesIngresos", "cargas totales - ingresos": "cargasTotalesIngresos",
    "cargas totales salidas": "cargasTotalesSalidas", "cargas totales - salidas": "cargasTotalesSalidas",
    "cargas totales": "cargasTotalesIngresos",
    "cargas maritimas": "cargasMaritimas", "cargas aereas": "cargasAereas",
    "cargas terrestres": "cargasTerrestres",
    "zona franca": "zonaFranca",
    "zona libre ingresos": "zonaLibreIngresos", "zona libre salidas": "zonaLibreSalidas",
    "zona libre": "zonaLibreIngresos",
    "transitos": "transitos", "transito": "transitos",
    "importaciones totalizadas": "importTotalizadas", "totalizadas": "importTotalizadas",
    "exportaciones totalizadas": "exportTotalizadas",
    "normativa": "normativa",
}

# --- helper builders -------------------------------------------------------
def R(cutoff=None, cols=None, local=None, counter=None, vitality=None,
      inferred=False, note=None, surveyed=None):
    """One (country, report) entry.

    local / counter values:
      a string  -> the column/filter name exists and is usable ("Importador", "Shipper")
      None      -> the report is anonymous on that side (no column, no filter)
      "no_disponible" -> column exists but is 'No disponible' in 100% of rows, no filter
      "unknown" -> the form was not surveyed; may or may not filter by company
      "Probable Importador" / "Probable Exportador" -> inferred, pass the word on
    cutoff: ISO date of the newest data, or None if never surveyed.
    vitality: only set when it cannot be computed from cutoff (e.g. "al día" with no date).
    surveyed: the day this entry was read off the form, when it is not meta.captured.
    """
    d = {"cutoff": cutoff, "columns_measured": cols,
         "names": {"local": local, "counterparty": counter}}
    if vitality:
        d["vitality"] = vitality
    if inferred:
        d["inferred"] = True
    if note:
        d["note"] = note
    if surveyed:
        d["surveyed"] = surveyed
    return d


S2 = "2026-09-18"  # second survey pass: prefilled period + small sample download


EU_NC = ["DE", "AT", "BE", "BG", "CY", "HR", "DK", "SK", "SI", "EE", "FI", "FR",
         "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "CZ",
         "RO", "SE"]
EU_NAME = {"DE": "Alemania", "AT": "Austria", "BE": "Bélgica", "BG": "Bulgaria",
           "CY": "Chipre", "HR": "Croacia", "DK": "Dinamarca", "SK": "Eslovaquia",
           "SI": "Eslovenia", "EE": "Estonia", "FI": "Finlandia", "FR": "Francia",
           "GR": "Grecia", "HU": "Hungría", "IE": "Irlanda", "IT": "Italia",
           "LV": "Letonia", "LT": "Lituania", "LU": "Luxemburgo", "MT": "Malta",
           "NL": "Países Bajos", "PL": "Polonia", "PT": "Portugal",
           "CZ": "República Checa", "RO": "Rumania", "SE": "Suecia"}
EU_NOTE = ("valores en EUROS y FOB, no USD CIF; filtra por País de Procedencia, "
           "no por país de origen")

UNK = "unknown"

COUNTRIES = {}


def C(code, name, region, nom, reports):
    COUNTRIES[code] = {"name_es": name, "region": region,
                       "nomenclature": nom, "reports": reports}


# ===================== Sudamérica (10) =====================
C("AR", "Argentina", "sudamerica", "NCM-SIM", {
    "import":            R("2026-07-31", 13, "Importador", None),
    "importDetalladas":  R("2026-07-31", 36, "Importador", None),
    "export":            R("2026-07-31", 9,  None, None,
                           note="no existe columna Exportador ni filtro; la columna Marca a veces nombra la firma"),
    "exportDetalladas":  R("2026-07-31", 31, "no_disponible", None, inferred=True,
                           note="Exportador = 'No disponible' en 100% de filas, sin filtro; aviso de estimación por IA"),
    "otrasOperaciones":  R("2026-07-31", 30, "Importador", None),
})
C("BO", "Bolivia", "sudamerica", "NANDINA", {
    "import":          R("2026-07-31", 25, "Importador", "Proveedor"),
    "export":          R("2026-08-31", 23, "Exportador", "Comprador", surveyed=S2,
                         note="trae Incoterm, Flete y Seguro"),
    "historicoImport": R("2023-09-30", None, None, None, surveyed=S2,
                         note="congelada 09/2023; anónimo, solo CIF y Kgs"),
    "historicoExport": R("2023-09-30", None, None, None, surveyed=S2,
                         note="congelada 09/2023; anónimo, filtra por Departamento"),
})
C("BR", "Brasil", "sudamerica", "Codigo NCM", {
    "import":                  R(None, 12, None, None, vitality="viva",
                                 note="estadística mensual agregada; Fecha trae solo mes y año"),
    "importDetalladas":        R("2021-11-30", None, None, None, note="congelada 11/2021"),
    "export":                  R("2026-08-31", None, None, None, surveyed=S2,
                                 note="estadística anónima: filtra por Puerto y Estado, sin empresas"),
    "exportDetalladas":        R("2021-11-30", None, None, None, note="congelada 11/2021"),
    "cargasMaritimasIngresos": R("2023-11-30", 34, "Consignatario", "Shipper",
                                 note="manifiesto de embarque; trae dirección, email y teléfono de ambas partes: datos personales, no redistribuir"),
    "cargasMaritimasSalidas":  R("2023-11-30", 32, "Shipper", "Consignatario", surveyed=S2,
                                 note="manifiesto de embarque; trae Notify y Forwarder. En la muestra medida, 2 de cada 3 consignatarios eran logísticas: no son el comprador. Datos de contacto de ambas partes: no redistribuir"),
    "cargasHistoricoIngresos": R("2020-01-31", 10, "Consignatario", None, surveyed=S2,
                                 note="congelada 01/2020. Se arma como declaración (Aduana, Estado, NCM de 8 dígitos, todos los transportes) y en la muestra el 99% de los consignatarios eran empresas: funciona como importador real"),
    "cargasHistoricoSalidas":  R("2018-07-31", None, "Shipper", None, surveyed=S2,
                                 note="congelada 07/2018; mismo formato que Histórico Ingresos, del lado exportador"),
})
C("CL", "Chile", "sudamerica", "SACH", {
    "import": R("2026-06-30", 40, "Importador", None, note="trae Incoterm y Marca"),
    "export": R("2026-06-30", 29, "Exportador", None, surveyed=S2,
                note="trae FOB y CIF, Marca y Cláusula VTA (la condición de venta, equivalente al Incoterm)"),
})
C("CO", "Colombia", "sudamerica", "NANDINA", {
    "import":          R("2026-05-31", 45, "Importador", "Proveedor", note="tiene Transportista"),
    "export":          R("2026-07-31", 28, "Exportador", "Comprador", surveyed=S2,
                         note="trae Agente Aduanero y Transportista; solo FOB"),
    "historicoImport": R("2021-12-31", None, "Probable Importador", "Probable Proveedor",
                         inferred=True, surveyed=S2,
                         note="congelada 12/2021. Softrade los rotula 'Probable' sin explicar por qué: pasá la palabra al usuario tal cual"),
    "historicoExport": R("2021-12-31", None, "Probable Exportador", "Probable Comprador",
                         inferred=True, surveyed=S2,
                         note="congelada 12/2021. Softrade los rotula 'Probable' sin explicar por qué: pasá la palabra al usuario tal cual"),
})
C("EC", "Ecuador", "sudamerica", "NANDINA", {
    "import":          R("2026-08-23", 48, "Importador", "Proveedor",
                         note="base más completa del sistema: 48 columnas, Incoterm y Marca presentes"),
    "export":          R("2026-09-06", 45, "Exportador", "Comprador", surveyed=S2,
                         note="45 columnas: Incoterm, Marca, Modelo, Bill of Lading y Estado de Declaración"),
    "historicoImport": R("2017-12-31", 48, "Importador", None, surveyed=S2,
                         note="congelada 12/2017; 48 columnas pero layout distinto de la actual: sin Incoterm, Modelo ni Bill of Lading, con Refrendo, Nro. DAU, Advalorem y Aforador. Trae Proveedor y Marca en el Excel, sin filtro por Proveedor"),
    "historicoExport": R("2017-12-31", None, "Exportador", None, surveyed=S2,
                         note="congelada 12/2017"),
    "cargasIngresos":  R("2026-07-31", 33, "Consignatario", "Shipper", surveyed=S2,
                         note="manifiesto: no tiene campo de partida, se filtra por Descripción o Marcas. Trae BL Master, Consolidador y RUC del consignatario. En la muestra, 1 de cada 3 consignatarios era logística"),
    "cargasSalidas":   R(None, None, UNK, UNK, note="no relevado"),
})
C("PY", "Paraguay", "sudamerica", "Codigo NCM", {
    "import": R("2026-07-31", 42, "Probable Importador", "Probable Proveedor", inferred=True,
                note="Softrade los rotula 'Probable' sin explicar por qué; traen RUC. Pasá la palabra al usuario tal cual"),
    "export": R("2026-07-31", None, "Probable Exportador", "Probable Comprador", inferred=True,
                note="Softrade los rotula 'Probable' sin explicar por qué; traen RUC. Pasá la palabra al usuario tal cual"),
})
C("PE", "Perú", "sudamerica", "NANDINA", {
    "import":         R("2026-08-22", 31, "Importador", "Proveedor", note="tiene Puerto y Transportista"),
    "export":         R("2026-08-22", None, "Exportador", "Comprador"),
    "cargasIngresos": R("2026-08-22", None, "Consignatario", "Shipper"),
    "cargasSalidas":  R(None, None, UNK, UNK, note="no relevado"),
})
C("UY", "Uruguay", "sudamerica", "Codigo NCM", {
    "import":          R("2026-09-01", 35, "Importador", None,
                         note="actualiza a diario: el mes en curso puede volver incompleto con filtros angostos. No trae CIF con ese nombre, trae U$S VNA; FOB, flete y seguro vienen sueltos"),
    "export":          R("2026-09-01", None, "Exportador", None),
    "transitos":       R(None, None, UNK, UNK, note="mercadería en tránsito, tipo de registro distinto; solo UY"),
    "cargasMaritimas": R("2024-07-11", None, "Consignatario (B/L)", "Remitente"),
    "cargasAereas":    R(None, None, UNK, UNK, note="no relevado; manifiestos aéreos, solo UY"),
    "cargasTerrestres": R(None, None, UNK, UNK, note="no relevado; manifiestos terrestres, solo UY"),
    "normativa":       R(None, None, None, None, note="regulaciones, no data de comercio exterior"),
})
C("VE", "Venezuela", "sudamerica", "NANDINA", {
    "import":          R("2024-08-31", 21, "Importador", None, note="congelada 08/2024"),
    "export":          R("2024-08-31", None, "Exportador", None, note="congelada 08/2024"),
    "historicoImport": R(None, None, UNK, UNK, note="form Histórico no relevado"),
    "historicoExport": R(None, None, UNK, UNK, note="form Histórico no relevado"),
    "cargasIngresos":  R("2025-08-31", None, "Consignatario", "Shipper"),
    "cargasSalidas":   R(None, None, UNK, UNK, note="no relevado"),
})

# ===================== Centroamérica y Caribe (8) =====================
C("CR", "Costa Rica", "centroamerica", "SAC", {
    "import":     R("2026-08-16", 48, "Importador", "Proveedor", note="48 columnas, trae Marca (no Incoterm)"),
    "export":     R("2026-08-16", None, "Exportador", "Comprador"),
    "zonaFranca": R("2026-08-16", None, "Operador", None, note="movimientos de zona franca; nombra solo al operador"),
})
C("SV", "El Salvador", "centroamerica", "SAC", {
    "import": R("2025-06-30", 8, None, None, note="rezagada; reporte fino de 8 columnas, solo CIF"),
    "export": R("2025-06-30", None, None, None, note="rezagada; anónimo"),
})
C("GT", "Guatemala", "centroamerica", "SAC", {
    "import":           R(None, None, None, None, note="reporte estándar no relevado"),
    "importDetalladas": R("2021-12-31", 17, None, None, note="congelada 12/2021; anónimo"),
    "export":           R(None, None, None, None, note="reporte estándar no relevado"),
    "exportDetalladas": R("2021-12-31", None, None, None, note="congelada 12/2021; anónimo"),
    "cargasIngresos":   R("2019-09-30", None, "Consignatario", "Shipper", note="muy vieja, 09/2019"),
    "cargasSalidas":    R(None, None, UNK, UNK, note="no relevado"),
})
C("HN", "Honduras", "centroamerica", "SAC", {
    "import":          R("2026-03-31", 8, None, None, note="rezagada; reporte fino de 8 columnas, solo CIF"),
    "export":          R("2026-03-31", None, None, None, note="rezagada; anónimo"),
    "historicoImport": R(None, None, UNK, UNK, note="form Histórico no relevado"),
    "historicoExport": R(None, None, UNK, UNK, note="form Histórico no relevado"),
})
C("NI", "Nicaragua", "centroamerica", "SAC", {
    "import":           R(None, None, UNK, UNK, note="reporte estándar no relevado; la variante Detalladas llega al 31/07/2026"),
    "importDetalladas": R("2026-07-31", 27, "Importador", "Proveedor"),
    "export":           R(None, None, UNK, UNK, note="reporte estándar no relevado"),
    "exportDetalladas": R("2026-07-31", None, "Exportador", "Comprador",
                          note="muestra bajada 2026-09-03 (454 filas/454 registros); columnas aún sin documentar"),
})
C("PA", "Panamá", "centroamerica", "SAC", {
    "import":                  R("2026-08-20", 30, "Importador", "Proveedor", note="tiene filtro Puerto"),
    "export":                  R("2026-08-20", None, "Exportador", "Comprador"),
    "zonaLibreIngresos":       R("2026-07-31", None, "Operador", "Proveedor",
                                 note="nombra al operador de zona libre y a su proveedor extranjero"),
    "zonaLibreSalidas":        R(None, None, UNK, UNK, note="no relevado"),
    "cargasMaritimasIngresos": R("2026-07-31", None, "Consignatario", None, note="sin filtro Shipper, solo lado consignatario"),
    "cargasMaritimasSalidas":  R(None, None, UNK, UNK, note="no relevado"),
})
C("PR", "Puerto Rico", "centroamerica", "SAC", {
    "import": R("2025-07-31", 11, None, None, note="rezagada; solo CIF"),
    "export": R("2025-07-31", None, None, None, note="rezagada; anónimo"),
})
C("DO", "Rep. Dominicana", "centroamerica", "SAC", {
    "import":           R(None, None, UNK, UNK, note="reporte estándar no relevado; la variante Detalladas llega al 31/07/2026"),
    "importDetalladas": R("2026-07-31", 27, "Importador", "Proveedor", note="tiene Agencia Aduanera"),
    "export":           R(None, None, UNK, UNK, note="reporte estándar no relevado"),
    "exportDetalladas": R("2026-07-31", None, "Exportador", "Comprador", note="el form de export trae Empresa Naviera"),
})

# ===================== Norteamérica (3) =====================
C("CA", "Canadá", "norteamerica", "Codigo SA", {
    "import":          R(None, None, UNK, UNK, note="no relevado (Norteamérica solo tiene MX relevado)"),
    "export":          R(None, None, UNK, UNK, note="no relevado"),
    "historicoImport": R(None, None, UNK, UNK, note="no relevado"),
    "historicoExport": R(None, None, UNK, UNK, note="no relevado"),
})
C("US", "Estados Unidos", "norteamerica", "Codigo SA", {
    "import":                  R(None, None, UNK, UNK, note="reporte estándar no relevado; la data de empresas está en Cargas Marítimas"),
    "export":                  R(None, None, UNK, UNK, note="no relevado"),
    "cargasMaritimasIngresos": R("2026-07-31", None, "Consignatario", "Shipper",
                                 note="punto de entrada más rico para impo de EEUU; ojo con 'Incluir Masters' (doble conteo de un mismo embarque)"),
    "cargasMaritimasSalidas":  R(None, None, UNK, UNK, note="no relevado"),
})
C("MX", "México", "norteamerica", "Codigo SA", {
    "import":                R("2021-11-30", 29, None, None,
                               note="congelada 11/2021; anónima. 'Condición de Venta' cumple la función de Incoterm. Ojo: el Ordinal trae item pegado, el conteo de registros se infla"),
    "export":                R(None, None, None, None, note="reporte estándar no relevado; anónimo"),
    "otrasOperaciones":      R(None, None, UNK, UNK, note="no relevado"),
    "cargasTotalesIngresos": R("2026-05-31", None, "Importador", "Proveedor",
                               note="única data mexicana viva y con nombres; ambas puntas"),
    "cargasTotalesSalidas":  R("2026-05-31", None, "Exportador", "Comprador"),
})

# ===================== Asia (17) =====================
C("BD", "Bangladesh", "asia", "Codigo SA", {
    "import": R("2026-07-31", None, "Importador", "Proveedor", note="solo importaciones, no hay reporte de exportaciones"),
})
C("CN", "China", "asia", "Codigo SA", {
    "import": R("2025-12-31", None, None, None,
                note="6 filtros en total; no nombra importadores. Para proveedores chinos, mirá la columna Proveedor de un país importador (PE, VN, PK)"),
    "export": R("2025-12-31", None, None, None, note="anónimo; estadística agregada"),
})
C("KR", "Corea del Sur", "asia", "Codigo SA", {
    "import": R("2026-05-31", None, None, None), "export": R("2026-05-31", None, None, None),
})
C("PH", "Filipinas", "asia", "Codigo SA", {
    "import":          R("2025-12-31", None, "Importador", "Proveedor", note="campo extra 'Pais de Exportador' aparte de país de origen"),
    "export":          R("2025-12-31", None, "Exportador", "Comprador"),
    "historicoImport": R(None, None, UNK, UNK, note="no relevado"),
    "historicoExport": R(None, None, UNK, UNK, note="no relevado"),
})
C("IN", "India", "asia", "Codigo SA", {
    "import": R("2018-06-30", None, None, None, note="archivo histórico, 8+ años; no ofrecer para nada actual"),
    "export": R("2018-06-30", None, None, None, note="archivo histórico, 8+ años"),
})
C("ID", "Indonesia", "asia", "Codigo SA", {
    "import":          R("2021-09-30", None, "Importador", "Proveedor", note="congelada 09/2021"),
    "export":          R("2021-09-30", None, "Exportador", "Comprador", note="congelada 09/2021"),
    "historicoImport": R(None, None, UNK, UNK, note="no relevado"),
    "historicoExport": R(None, None, UNK, UNK, note="no relevado"),
})
C("IL", "Israel", "asia", "Codigo SA", {
    "import": R("2026-05-31", None, None, None), "export": R("2026-05-31", None, None, None),
})
C("JP", "Japón", "asia", "Codigo JTS", {
    "import": R("2026-07-31", None, None, None), "export": R("2026-07-31", None, None, None),
})
C("KZ", "Kazajistán", "asia", "Codigo SA", {
    "import": R("2026-07-31", None, "Importador", "Proveedor"),
    "export": R("2026-07-31", None, "Exportador", "Comprador"),
})
C("PK", "Pakistán", "asia", "Codigo SA", {
    "import": R("2026-07-31", None, "Importador", "Proveedor"),
    "export": R("2026-07-31", None, "Exportador", "Comprador"),
})
C("RU", "Rusia", "asia", "Codigo CN FEA", {
    "import":           R(None, None, UNK, UNK, note="reporte estándar no relevado"),
    "importDetalladas": R("2023-12-31", None, "Importador", "Proveedor", note="congelada 12/2023; ambas puntas"),
    "export":           R(None, None, UNK, UNK, note="reporte estándar no relevado"),
    "exportDetalladas": R("2023-12-31", None, "Exportador", "Comprador", note="congelada 12/2023; ambas puntas"),
})
C("LK", "Sri Lanka", "asia", "Codigo SA", {
    "import": R("2019-12-31", None, "Importador", "Proveedor", note="congelada 12/2019"),
    "export": R("2019-12-31", None, "Exportador", "Comprador", note="congelada 12/2019"),
})
C("TH", "Tailandia", "asia", "Codigo SA", {
    "import": R("2026-07-31", None, None, None), "export": R("2026-07-31", None, None, None),
})
C("TW", "Taiwán", "asia", "Codigo SA", {
    "import": R("2017-03-31", None, None, None, note="archivo histórico, 9+ años"),
    "export": R("2017-03-31", None, None, None, note="archivo histórico, 9+ años"),
})
C("TR", "Turquía", "asia", "Codigo SA", {
    "import":           R(None, None, UNK, UNK, note="reporte estándar no relevado"),
    "importDetalladas": R("2023-12-31", None, "Importador", "Proveedor", note="congelada 12/2023; ambas puntas"),
    "export":           R(None, None, UNK, UNK, note="reporte estándar no relevado"),
    "exportDetalladas": R("2023-12-31", None, "Exportador", "Comprador", note="congelada 12/2023; ambas puntas"),
})
C("UZ", "Uzbekistán", "asia", "Codigo SA", {
    "import": R("2025-12-31", None, "Importador", "Proveedor"),
    "export": R("2025-12-31", None, "Exportador", "Comprador"),
})
C("VN", "Vietnam", "asia", "Codigo SA", {
    "import":          R("2026-06-30", None, "Importador", "Proveedor",
                         note="mejor cubierto de Asia: importador, proveedor, ambos puertos y depósito (bonded warehouse)"),
    "export":          R("2026-06-30", None, "Exportador", "Comprador"),
    "historicoImport": R(None, None, UNK, UNK, note="no relevado"),
    "historicoExport": R(None, None, UNK, UNK, note="no relevado"),
})

# ===================== África (9) =====================
C("EG", "Egipto", "africa", "Codigo SA", {
    "import": R("2015-02-28", None, None, None, note="la data más vieja del sistema, 02/2015; nunca ofrecer como actual"),
    "export": R("2015-02-28", None, None, None, note="la data más vieja del sistema, 02/2015"),
})
C("ET", "Etiopía", "africa", "Codigo SA", {
    "import": R("2026-07-31", None, "Importador", None, note="import nombra solo al importador, sin proveedor"),
    "export": R("2026-07-31", None, "Exportador", "Comprador", note="único país donde el lado exportador es más rico que el importador"),
})
C("KE", "Kenia", "africa", "Codigo SA", {
    "import":          R("2026-06-30", None, "Importador", "Proveedor",
                         note="filtro Terminal de Contenedores; trae Identificador y Nro. Declaración por separado. No hay reporte de exportaciones"),
    "historicoImport": R(None, None, UNK, UNK, note="no relevado"),
})
C("LS", "Lesoto", "africa", "Codigo SA", {
    "import": R("2026-07-31", None, "Importador", "Proveedor"),
    "export": R("2026-07-31", None, "Exportador", "Comprador"),
})
C("MA", "Marruecos", "africa", "Codigo SA", {
    "import": R("2026-02-28", None, None, None), "export": R("2026-02-28", None, None, None),
})
C("NG", "Nigeria", "africa", "Codigo SA", {
    "import": R("2025-07-31", None, "Importador", "Proveedor"),
    "export": R("2025-07-31", None, "Exportador", "Comprador"),
})
C("ZA", "Sudáfrica", "africa", "Codigo SA", {
    "import": R("2026-07-31", None, None, None, note="reporta en Rand (ZAR CIF), no dólares: única moneda así en el sistema"),
    "export": R("2026-07-31", None, None, None, note="reporta en Rand (ZAR)"),
})
C("UG", "Uganda", "africa", "Codigo SA", {
    "import": R("2024-09-30", None, "Importador", "Proveedor"),
    "export": R("2024-09-30", None, "Exportador", "Comprador"),
})
C("ZW", "Zimbabue", "africa", "Codigo SA", {
    "import": R("2023-07-31", None, "Importador", "Proveedor"),
    "export": R("2023-07-31", None, "Exportador", "Comprador"),
})

# ===================== Oceanía (2) =====================
C("AU", "Australia", "oceania", "Codigo SA", {
    "import":          R("2026-06-30", None, None, None, note="único país con Aduana de Ingreso y de Salida en el form de impo; anónimo"),
    "export":          R("2026-06-30", None, None, None, note="anónimo"),
    "historicoImport": R(None, None, UNK, UNK, note="no relevado"),
    "historicoExport": R(None, None, UNK, UNK, note="no relevado"),
})
C("NZ", "Nueva Zelanda", "oceania", "Codigo SA", {
    "import": R("2026-07-31", None, None, None), "export": R("2026-07-31", None, None, None),
})

# ===================== Europa (29) =====================
C("UA", "Ucrania", "europa", "UKTWED", {
    "import": R("2024-12-31", None, "Importador", "Proveedor"),
    "export": R("2022-12-31", None, "Exportador", "Comprador", note="exportaciones atrasadas ~2 años respecto de importaciones"),
})
C("GB", "Reino Unido", "europa", "Codigo SA", {
    "import": R("2026-04-30", None, None, None, note="fuera del bloque UE: Codigo SA y dólares, no euros"),
    "export": R("2026-04-30", None, None, None, note="fuera del bloque UE: Codigo SA y dólares"),
})
C("ES", "España", "europa", "Codigo NC", {
    "import":           R("2025-12-31", None, None, None,
                          note="el 'Importaciones' de España es el específico del país: sin Identificador, con País de Origen real y dos aduanas. Más viejo que Totalizadas"),
    "importTotalizadas": R("2026-05-31", None, None, None,
                           note="pese al nombre, es el dataset UE estándar (euros, FOB, País de Procedencia); más nuevo que 'Importaciones'"),
    # entities-world.md leaves both Spanish export cutoffs blank; do not copy the
    # import dates across. Unknown cutoff -> preflight tells the user to read it
    # off the form.
    "export":           R(None, None, None, None, note="específico de España; vigencia no relevada"),
    "exportTotalizadas": R(None, None, None, None, note="dataset UE estándar; vigencia no relevada"),
})
for _code in EU_NC:
    C(_code, EU_NAME[_code], "europa", "Codigo NC", {
        "import": R("2026-05-31", None, None, None, note=EU_NOTE),
        "export": R("2026-05-31", None, None, None, note=EU_NOTE),
    })


# --- assemble & write ----------------------------------------------------
def catalog_version(catalog):
    """"<latest survey date>+<hash>" for a built catalog.

    The date is the newest of meta.captured and every entry's `surveyed`, so a
    reader sees which survey pass it reflects. The hash covers the whole catalog
    except this field, so a fixed note or a corrected cutoff with no new survey
    date still changes the version.
    """
    meta = {k: v for k, v in catalog["meta"].items() if k != "catalog_version"}
    body = dict(catalog, meta=meta)
    dates = [meta.get("captured") or ""] + [
        e["surveyed"] for c in catalog["countries"].values()
        for e in c["reports"].values() if e.get("surveyed")]
    blob = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "%s+%s" % (max(dates), hashlib.sha256(blob.encode("utf-8")).hexdigest()[:8])


def build():
    """The catalog as a dict, ready to dump. Writes nothing."""
    catalog = {
        "meta": {
            "captured": CAPTURED,
            "source": "derived from skills/softrade-batch/references/*.md by tools/build_catalog.py",
            "record_cap": 30000,
            "max_months_per_query": 12,
            "vitality_thresholds_months": {"viva": 4, "rezagada": 18},
            "name_states": {
                "string": "columna y filtro por empresa usables (p. ej. 'Importador')",
                "null": "reporte anónimo de ese lado: no hay columna ni filtro",
                "no_disponible": "la columna existe pero es 'No disponible' en el 100% y no hay filtro",
                "unknown": "el form no se relevó; puede o no filtrar por empresa",
                "Probable ...": "Softrade lo rotula 'Probable' sin explicar por qué; el archivo trae el RUC",
            },
        },
        "report_types": {
            rid: {"label_es": v[0], "family": v[1], "direction": v[2], "detailed": v[3]}
            for rid, v in REPORT_TYPES.items()
        },
        "report_aliases": ALIASES,
        "countries": dict(sorted(COUNTRIES.items())),
    }

    # sanity: every report a country lists must be a known report_type
    bad = []
    for cc, c in catalog["countries"].items():
        for rid in c["reports"]:
            if rid not in REPORT_TYPES:
                bad.append("%s/%s" % (cc, rid))
    if bad:
        raise SystemExit("unknown report_type(s): %s" % ", ".join(bad))

    # Deep copy through JSON: callers (tests, --check) may mutate the result
    # without touching COUNTRIES / ALIASES.
    catalog = json.loads(json.dumps(catalog, ensure_ascii=False))
    catalog["meta"]["catalog_version"] = catalog_version(catalog)
    return catalog


def diff_summary(old, new, limit=20):
    """Short list of what differs between two parsed catalogs (file vs build)."""
    out = []
    for key in sorted(set(old) | set(new)):
        if key == "countries" or old.get(key) == new.get(key):
            continue
        if key == "meta" and isinstance(old.get(key), dict) and isinstance(new.get(key), dict):
            for mk in sorted(set(old[key]) | set(new[key])):
                if old[key].get(mk) != new[key].get(mk):
                    out.append("meta.%s: %r -> %r" % (mk, old[key].get(mk), new[key].get(mk)))
        else:
            out.append("%s difiere" % key)
    asdict = lambda x: x if isinstance(x, dict) else {}  # noqa: E731  (file may be malformed)
    oc, nc = asdict(old.get("countries")), asdict(new.get("countries"))
    for cc in sorted(set(oc) | set(nc)):
        if cc not in nc:
            out.append("%s: sobra en el archivo" % cc)
        elif cc not in oc:
            out.append("%s: falta en el archivo" % cc)
        elif not isinstance(oc[cc], dict):
            out.append("%s: no es un objeto en el archivo" % cc)
        elif oc[cc] != nc[cc]:
            orp, nrp = asdict(oc[cc].get("reports")), asdict(nc[cc].get("reports"))
            if not isinstance(oc[cc].get("reports"), dict):
                out.append("%s: reports no es un objeto en el archivo" % cc)
            for rid in sorted(set(orp) | set(nrp)):
                if rid not in nrp:
                    out.append("%s/%s: sobra en el archivo" % (cc, rid))
                elif rid not in orp:
                    out.append("%s/%s: falta en el archivo" % (cc, rid))
                elif orp[rid] != nrp[rid]:
                    out.append("%s/%s: difiere" % (cc, rid))
            rest = lambda c: {k: v for k, v in c.items() if k != "reports"}  # noqa: E731
            if rest(oc[cc]) != rest(nc[cc]):
                out.append("%s: datos del país difieren" % cc)
    if len(out) > limit:
        out = out[:limit] + ["... y %d diferencias más" % (len(out) - limit)]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="no escribe nada: compara el archivo con lo que generaría el builder; "
                         "exit 1 si está desactualizado")
    ap.add_argument("--out", metavar="PATH",
                    help="archivo a escribir (o a comparar, con --check); default: references/catalog.json")
    args = ap.parse_args(argv)
    out_path = args.out or OUT
    catalog = build()

    if args.check:
        try:
            with open(out_path, encoding="utf-8") as fh:
                current = json.load(fh)
            if not isinstance(current, dict):  # null / [] / "x": JSON válido pero no un catálogo
                raise ValueError("no es un objeto JSON (%s)" % type(current).__name__)
        except (OSError, ValueError) as ex:
            print("check: no puedo leer %s (%s) -- corré tools/build_catalog.py" % (out_path, ex),
                  file=sys.stderr)
            return 1
        if current == catalog:
            print("check: %s al día (%s)" % (out_path, catalog["meta"]["catalog_version"]))
            return 0
        print("check: %s desactualizado -- corré tools/build_catalog.py" % out_path)
        for line in diff_summary(current, catalog):
            print("  - %s" % line)
        return 1

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    n_countries = len(catalog["countries"])
    n_reports = sum(len(c["reports"]) for c in catalog["countries"].values())
    n_measured = sum(1 for c in catalog["countries"].values()
                     for r in c["reports"].values() if r["columns_measured"])
    try:
        shown = os.path.relpath(os.path.abspath(out_path), ROOT)
    except ValueError:  # Windows: --out on another drive
        shown = os.path.abspath(out_path)
    print("wrote %s" % shown)
    print("  catalog_version %s" % catalog["meta"]["catalog_version"])
    print("  countries      %d" % n_countries)
    print("  report_types   %d" % len(catalog["report_types"]))
    print("  country/report %d entries, %d with a measured column count" % (n_reports, n_measured))
    return 0


if __name__ == "__main__":
    sys.exit(main())
