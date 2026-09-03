#!/usr/bin/env python3
"""Answer, without opening a browser, whether a Softrade request can be resolved.

SKILL.md Step 0 says to check a request is even answerable before planning:
does this country/report exist, is the data still alive, and (if the user wants
to attribute to a company) does the form name that side at all. Today that is a
manual read of four markdown files. This does it as one deterministic call
against references/catalog.json.

Usage:
  python scripts/preflight.py --country ar --report "impo detalladas" \
      [--by-company] [--from 2026-01 --to 2026-07] [--json]

Verdicts and exit codes:
  0  OK          the combo is valid, current, and (if asked) company-attributable
  1  WARN        usable, but with caveats the user must hear first
  2  IMPOSSIBLE  the report does not exist, or cannot answer the question asked

`messages_es` in the JSON output are the exact sentences to relay to the user.
"""
import argparse
import datetime as dt
import json
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

try:
    import _catalog
except ImportError:  # allow running from another cwd
    sys.path.insert(0, __file__.rsplit("/", 1)[0].rsplit("\\", 1)[0])
    import _catalog

OK, WARN, IMPOSSIBLE = "OK", "WARN", "IMPOSSIBLE"
_RANK = {OK: 0, WARN: 1, IMPOSSIBLE: 2}
_EXIT = {OK: 0, WARN: 1, IMPOSSIBLE: 2}


def _ym(value):
    """YYYY-MM or YYYY-MM-DD -> date on the first of that month."""
    if not value:
        return None
    p = value.split("-")
    return dt.date(int(p[0]), int(p[1]), 1)


def _fmt_month(d):
    return "%02d/%04d" % (d.month, d.year)


def evaluate(catalog, country, report, by_company=False,
             date_from=None, date_to=None, today=None):
    today = today or dt.date.today()
    out = {
        "country": None, "country_name": None,
        "report": None, "report_label": None, "report_alias_in": report,
        "nomenclature": None, "cutoff": None, "vitality": None,
        "columns_measured": None, "by_company": bool(by_company),
        "company_side": None, "date_from": date_from, "date_to": date_to,
        "effective_to": None, "verdict": OK, "messages_es": [],
    }

    def say(level, msg):
        if _RANK[level] > _RANK[out["verdict"]]:
            out["verdict"] = level
        out["messages_es"].append(msg)

    # --- resolve country + report -------------------------------------------
    try:
        cc, rid, e = _catalog.entry(catalog, country, report)
    except _catalog.CatalogError as ex:
        out["verdict"] = IMPOSSIBLE
        out["messages_es"].append(str(ex))
        return out

    ct = catalog["countries"][cc]
    rt = catalog["report_types"][rid]
    out.update(country=cc, country_name=ct["name_es"], report=rid,
               report_label=rt["label_es"], nomenclature=ct["nomenclature"],
               cutoff=e.get("cutoff"), columns_measured=e.get("columns_measured"))

    if rid == "normativa":
        say(IMPOSSIBLE, "Normativa son regulaciones, no datos de comercio exterior: no hay un dataset para exportar.")
        return out

    # --- vitality ---------------------------------------------------------------
    vit, months = _catalog.vitality(e, today=today)
    out["vitality"] = vit
    cutoff_d = _catalog.parse_iso(e.get("cutoff"))
    if vit == "congelada":
        say(WARN, "La base de %s / %s está congelada en %s: pedirle datos recientes "
                  "devuelve vacío y parece un error de filtro."
                  % (cc, rt["label_es"], _fmt_month(cutoff_d) if cutoff_d else "una fecha vieja"))
    elif vit == "rezagada":
        say(WARN, "Los datos de %s / %s llegan hasta %s: sirven para histórico, no para "
                  "'este año'." % (cc, rt["label_es"], _fmt_month(cutoff_d)))
    elif vit == "desconocida":
        say(WARN, "La vigencia de %s / %s no está relevada: confirmá contra el cabezal "
                  "azul del sitio hasta qué fecha hay datos." % (cc, rt["label_es"]))

    # daily-updated country: the pre-filled month is still accumulating
    if cutoff_d and (today - cutoff_d).days <= 10:
        say(WARN, "%s actualiza casi a diario (último dato %s). El mes en curso todavía "
                  "se está cargando y una consulta con filtro angosto puede volver "
                  "incompleta; preferí el último mes cerrado."
                  % (cc, _fmt_month(cutoff_d)))

    # --- date range vs cutoff ------------------------------------------------
    d_from, d_to = _ym(date_from), _ym(date_to)
    if cutoff_d:
        cutoff_month = dt.date(cutoff_d.year, cutoff_d.month, 1)
        if d_from and d_from > cutoff_month:
            say(IMPOSSIBLE, "Pedís desde %s pero %s / %s sólo tiene datos hasta %s."
                % (_fmt_month(d_from), cc, rt["label_es"], _fmt_month(cutoff_d)))
        elif d_to and d_to > cutoff_month:
            out["effective_to"] = _fmt_month(cutoff_month)
            say(WARN, "%s / %s llega hasta %s; aunque pidas hasta %s vas a recibir sólo "
                      "hasta ahí." % (cc, rt["label_es"], _fmt_month(cutoff_d), _fmt_month(d_to)))

    # --- company attribution ----------------------------------------------------
    local = e["names"]["local"]
    direction = rt["direction"]
    side_word = "exportador" if direction == "export" else "importador"
    if by_company:
        if local is None:
            say(IMPOSSIBLE, "%s / %s no publica el %s: no hay columna ni filtro por "
                            "empresa. Decíselo al usuario antes de planificar."
                            % (cc, rt["label_es"], side_word))
            if cc == "AR" and direction == "export":
                out["messages_es"].append(
                    "Alternativa para AR exportaciones: la columna 'Marca - Sufijos' "
                    "a veces nombra la firma, pero es una estimación, no un dato oficial.")
        elif local == "no_disponible":
            say(IMPOSSIBLE, "%s / %s trae una columna de %s pero está en 'No disponible' "
                            "en el 100%% de las filas y no hay filtro: no se puede atribuir "
                            "a una empresa." % (cc, rt["label_es"], side_word))
        elif local == "unknown":
            say(WARN, "El formulario de %s / %s no se relevó: puede tener o no filtro por "
                      "empresa. Confirmalo al abrirlo antes de prometer la atribución."
                      % (cc, rt["label_es"]))
            out["company_side"] = "unknown"
        elif str(local).lower().startswith("probable"):
            out["company_side"] = local
            say(WARN, "%s marca la empresa como '%s': es un nombre inferido por Softrade, "
                      "no un registro oficial. Pasale esa palabra al usuario."
                      % (cc, local))
        else:
            out["company_side"] = local
            counter = e["names"]["counterparty"]
            msg = "%s / %s filtra por '%s'" % (cc, rt["label_es"], local)
            msg += " y nombra la contraparte ('%s')." % counter if counter and counter != "unknown" else "."
            out["messages_es"].append(msg)

    # --- nomenclature + euros trap -----------------------------------------
    if ct["nomenclature"] == "Codigo NC":  # the EU block, incl. España
        say(WARN, "Europa (Codigo NC): los valores vienen en EUROS y son FOB, no USD CIF, "
                  "y el filtro de país es 'País de Procedencia', no de origen. No lo "
                  "mezcles con datos de otras regiones.")

    if e.get("note") and e["note"] not in out["messages_es"]:
        out["messages_es"].append("Nota: " + e["note"])

    if out["verdict"] == OK:
        out["messages_es"].insert(0, "Consulta válida y con datos vigentes.")
    return out


def _human(out):
    L = []
    alias = ""
    if out["report_alias_in"] and out["report_alias_in"] != out["report"]:
        alias = "  (%s)" % out["report_alias_in"]
    L.append("consulta      %s / %s%s" % (out["country"] or "?", out["report"] or "?", alias))
    if out["country_name"]:
        L.append("país          %s" % out["country_name"])
    if out["report_label"]:
        L.append("reporte       %s" % out["report_label"])
    if out["vitality"]:
        L.append("vitalidad     %-11s último dato %s" % (out["vitality"].upper(), out["cutoff"] or "s/d"))
    if out["nomenclature"]:
        L.append("nomenclatura  %s  (comparte 6 dígitos del SA con el resto)" % out["nomenclature"])
    if out["columns_measured"]:
        L.append("columnas      %d medidas" % out["columns_measured"])
    elif out["columns_measured"] is None and out["report"]:
        L.append("columnas      sin medir todavía")
    if out["by_company"]:
        cs = out["company_side"]
        L.append("por empresa   %s" % ("OK: filtro " + cs if cs and cs != "unknown"
                                       else "ver mensajes"))
    L.append("veredicto     %s" % out["verdict"])
    for m in out["messages_es"]:
        L.append("  - " + m)
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--country", required=True)
    ap.add_argument("--report", required=True, help="canonical id or free text ('impo detalladas', 'las expo')")
    ap.add_argument("--by-company", action="store_true", dest="by_company",
                    help="the user wants to attribute rows to a named company")
    ap.add_argument("--from", dest="date_from", metavar="YYYY-MM")
    ap.add_argument("--to", dest="date_to", metavar="YYYY-MM")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--catalog", help="path to catalog.json (default: alongside references/)")
    args = ap.parse_args(argv)

    try:
        catalog = _catalog.load(args.catalog)
    except _catalog.CatalogError as ex:
        print(ex, file=sys.stderr)
        return 2

    out = evaluate(catalog, args.country, args.report, args.by_company,
                   args.date_from, args.date_to)

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(_human(out))
    return _EXIT[out["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
