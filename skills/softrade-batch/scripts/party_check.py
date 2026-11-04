#!/usr/bin/env python3
"""How many of the names in a download are really trading companies?

Customs declarations name the importer of record. Bill-of-lading data (the Cargas
family) names whoever the carrier delivers to, which is often a forwarder, a
shipping line or a bank under a "TO ORDER" bill. A ranking of "top importers"
built on those names silently mixes buyers with logistics companies, and the
logistics companies float to the top because they consolidate many clients.

This script measures that before anyone attributes volume to a company. For
every party column it finds (Consignatario, Shipper, Notify, Importador, Operador,
Proveedor, ...) it reports the share of rows whose name is:

  to_order    "TO ORDER", "A LA ORDEN" and variants: no buyer named at all
  logistics   a known forwarder / NVOCC / shipping line brand
  generic     a name built on logistics words (LOGISTICS, FREIGHT, CARGO, ...);
              a heuristic, so read it as "probably", not "certainly"

Usage:
  python party_check.py FILE [--json] [--no-names]

--no-names hides the top-10 name list, for when the output will be shared: the
names are real companies from licensed data.
"""
import argparse
import json
import os
import re
import sys
import unicodedata

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# Columns that name a party, as Softrade spells them across countries. "operador"
# is the free-zone company in CR Zona Franca and PA Zona Libre (references/cargas.md).
# Compared after norm_column(), so write them lowercase, unaccented, single-spaced.
PARTY_COLUMNS = (
    "consignatario", "shipper", "notify", "remitente", "forwarder",
    "importador", "probable importador", "exportador", "probable exportador",
    "proveedor", "probable proveedor", "comprador", "probable comprador",
    "operador",
)

TO_ORDER = re.compile(r"\b(TO\s+(THE\s+)?ORDER|A\s+LA\s+ORDEN|AL?\s+ORDEN\s+DE|ORDER\s+OF)\b")

# Brands, matched as whole words. Kept short and unambiguous on purpose: a false
# "logistics" flag on a real importer is worse than a missed forwarder. Brands that
# are also ordinary words (EVERGREEN, AGILITY, MSC, ZIM) only count next to the word
# the carrier trades under ("AGILITY FITNESS" stays a company). Brands are checked
# before GENERIC, so "AGILITY LOGISTICS" is "logistics", not "generic".
LOGISTICS_BRANDS = re.compile(r"\b(" + "|".join([
    r"KUEHNE", r"K\s*\+\s*N", r"DHL", r"DSV", r"EXPEDITORS", r"SCHENKER", r"CEVA",
    r"GEODIS", r"PANALPINA", r"BOLLORE", r"NIPPON\s+EXPRESS", r"KINTETSU",
    r"C\.?\s*H\.?\s+ROBINSON", r"AGILITY\s+(LOGISTICS|GLOBAL\s+INTEGRATED)",
    r"HELLMANN", r"DACHSER", r"RHENUS",
    r"MAERSK", r"MEDITERRANEAN\s+SHIPPING", r"MSC\s+(MEDITERRANEAN|SHIPPING|CHILE|ARGENTINA|"
    r"PERU|COLOMBIA|MEXICO|BRASIL|BRAZIL|URUGUAY|PARAGUAY|ECUADOR|PANAMA|AGENCIA)",
    r"CMA\s*CGM", r"HAPAG",
    r"EVERGREEN\s+(MARINE|LINE|SHIPPING)", r"COSCO", r"OCEAN\s+NETWORK\s+EXPRESS",
    r"YANG\s+MING", r"ZIM\s+(INTEGRATED|LINE|SHIPPING)",
    r"HAMBURG\s+SUD", r"WAN\s+HAI", r"HYUNDAI\s+MERCHANT", r"UPS\s+SUPPLY",
    r"FEDEX\s+TRADE", r"SEABOARD\s+MARINE",
]) + r")\b")

GENERIC = re.compile(r"\b(" + "|".join([
    r"LOGISTIC[AS]?", r"LOGISTICS", r"LOGISTICA", r"FREIGHT", r"FORWARD(ING|ERS?)?",
    r"SHIPPING", r"CARGO", r"NVOCC", r"TRANSITARI[OA]S?", r"AGENCIA\s+MARITIMA",
    r"AGENTE\s+DE\s+CARGA", r"DESPACHANTE", r"CUSTOMS\s+BROKER",
    r"TRANSPORT(E|ES|ATION|S)?", r"MULTIMODAL", r"SUPPLY\s*CHAIN",
]) + r")\b")


def classify(name):
    n = str(name).upper()
    if TO_ORDER.search(n):
        return "to_order"
    if LOGISTICS_BRANDS.search(n):
        return "logistics"
    if GENERIC.search(n):
        return "generic"
    return "company"


def norm_column(name):
    """'Probable  Importador ' / 'CONSIGNATARIO' / 'Operadór' -> PARTY_COLUMNS spelling."""
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.split()).casefold()


def party_columns(frame):
    return [c for c in frame.columns if norm_column(c) in PARTY_COLUMNS]


def analyse(frame, top=10):
    out = {}
    for col in party_columns(frame):
        values = frame[col].dropna().astype(str).str.strip()
        values = values[(values != "") & (values != "No disponible")]
        if not len(values):
            out[str(col)] = {"rows_named": 0}
            continue
        kinds = values.map(classify)
        share = {k: round(100.0 * (kinds == k).sum() / len(values), 1)
                 for k in ("to_order", "logistics", "generic", "company")}
        counts = values.value_counts().head(top)
        out[str(col)] = {
            "rows_named": int(len(values)),
            "distinct": int(values.nunique()),
            "share_pct": share,
            "top": [{"name": n, "rows": int(c), "kind": classify(n)}
                    for n, c in counts.items()],
        }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-names", action="store_true",
                    help="omit the top-name lists (the names are real companies)")
    args = ap.parse_args(argv)

    if not os.path.exists(args.path):
        sys.exit("no such file: %s" % args.path)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from inspect_download import read_table

    result = analyse(read_table(args.path))
    if args.no_names:
        for v in result.values():
            v.pop("top", None)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not result:
        print("no party columns found (Consignatario, Importador, Proveedor, ...)")
        return 0
    for col, v in result.items():
        if not v.get("rows_named"):
            print("%-22s no names" % col)
            continue
        s = v["share_pct"]
        print("%-22s %d rows, %d distinct | TO ORDER %.1f%% | logistics brand %.1f%% | "
              "logistics words %.1f%% | other %.1f%%"
              % (col, v["rows_named"], v["distinct"], s["to_order"], s["logistics"],
                 s["generic"], s["company"]))
        for t in v.get("top", []):
            flag = "" if t["kind"] == "company" else "  <- %s" % t["kind"]
            print("    %6d  %s%s" % (t["rows"], t["name"][:60], flag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
