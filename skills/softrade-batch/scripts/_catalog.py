#!/usr/bin/env python3
"""Shared access to references/catalog.json for the query-engine scripts.

`preflight.py` and `plan_run.py` both need to: load the catalog, turn a
free-text report name into a canonical id, look up a (country, report) entry,
and judge vitality against today. That logic lives here so the two stay in sync.

Nothing in here touches the browser or the network.
"""
import datetime as _dt
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG_PATH = os.path.join(_HERE, os.pardir, "references", "catalog.json")


class CatalogError(Exception):
    """Bad country / report / lookup. Message is user-facing (Spanish)."""


def load(path=None):
    p = path or CATALOG_PATH
    if not os.path.exists(p):
        # catalog.json viene con la skill; tools/build_catalog.py vive en el repo,
        # fuera de la skill instalada, así que el arreglo es reinstalar, no regenerar.
        raise CatalogError(
            "no encuentro catalog.json en %s -- la instalación de la skill está "
            "incompleta: reinstalá el plugin o volvé a copiar la carpeta "
            "skills/softrade-batch entera (regenerarlo con tools/build_catalog.py "
            "es tarea de mantenimiento, desde un clon del repo)" % p)
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def version(catalog):
    """The catalog_version a manifest should carry.

    meta.catalog_version ("<latest survey date>+<hash>", written by
    tools/build_catalog.py) changes whenever any entry does; meta.captured alone
    does not move on a partial survey pass. Older catalogs without the field fall
    back to meta.captured.
    """
    meta = catalog.get("meta") or {}
    return meta.get("catalog_version") or meta.get("captured")


def _norm(text):
    """Lowercase, strip accents and punctuation, collapse spaces."""
    text = (text or "").strip().lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")):
        text = text.replace(a, b)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def resolve_report(catalog, name):
    """Free-text or canonical report name -> canonical id.

    Raises CatalogError with the candidate list when it is ambiguous or unknown.
    """
    if name in catalog["report_types"]:
        return name

    n = _norm(name)
    aliases = {_norm(k): v for k, v in catalog.get("report_aliases", {}).items()}
    # also let the canonical ids match case-insensitively
    for rid in catalog["report_types"]:
        aliases.setdefault(_norm(rid), rid)
        aliases.setdefault(_norm(catalog["report_types"][rid]["label_es"]), rid)

    if n in aliases:
        return aliases[n]

    # Second chance: the same words, forgiving singular/plural, filler words and
    # word order ("exportación detallada", "historico de importaciones"). A key
    # that two different reports share is dropped rather than guessed.
    by_key = {}
    for k, v in aliases.items():
        by_key.setdefault(_key(k), set()).add(v)
    hit = by_key.get(_key(name))
    if hit and len(hit) == 1:
        return next(iter(hit))

    # Anything looser is only a suggestion. Resolving on a substring used to let
    # a short alias win silently: "exportación detallada" contains "expo" and
    # came back as plain `export`, a plausible and wrong report.
    near = sorted({v for k, v in aliases.items() if n and (n in k or k in n)})
    if near:
        raise CatalogError(
            "no reconozco el reporte %r. ¿Quisiste decir %s? Usá el id exacto."
            % (name, " / ".join(near)))
    raise CatalogError("no reconozco el reporte %r" % name)


_FILLER = {"de", "del", "la", "las", "los", "el", "y"}


def _stem(word):
    """Crude singular form, applied identically to input and aliases."""
    if len(word) > 4 and word.endswith("es"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


def _key(text):
    words = [w for w in _norm(text).split() if w not in _FILLER]
    return " ".join(sorted(_stem(w) for w in words))


def country(catalog, code):
    cc = (code or "").strip().upper()
    if cc not in catalog["countries"]:
        raise CatalogError("país desconocido: %r" % code)
    return cc, catalog["countries"][cc]


_REPORT_ORDER = list(  # stable, useful order for listing a country's reports
    ("import", "importDetalladas", "importTotalizadas", "export",
     "exportDetalladas", "exportTotalizadas", "otrasOperaciones",
     "historicoImport", "historicoExport", "cargasIngresos", "cargasSalidas",
     "cargasMaritimasIngresos", "cargasMaritimasSalidas", "cargasMaritimas",
     "cargasTotalesIngresos", "cargasTotalesSalidas", "cargasAereas",
     "cargasTerrestres", "cargasHistoricoIngresos", "cargasHistoricoSalidas",
     "zonaFranca", "zonaLibreIngresos", "zonaLibreSalidas", "transitos",
     "normativa"))


def offered_reports(country_entry):
    """A country's report ids in a readable order."""
    rank = {rid: i for i, rid in enumerate(_REPORT_ORDER)}
    return sorted(country_entry["reports"], key=lambda r: rank.get(r, 99))


def entry(catalog, code, report):
    """(canonical_country, canonical_report, report_entry_dict)."""
    cc, c = country(catalog, code)
    rid = resolve_report(catalog, report)
    if rid not in c["reports"]:
        offered = ", ".join(offered_reports(c))
        raise CatalogError(
            "%s no ofrece '%s'. Reportes de %s: %s" % (cc, rid, cc, offered))
    return cc, rid, c["reports"][rid]


def parse_iso(d):
    if not d:
        return None
    return _dt.date.fromisoformat(d)


def vitality(cat_entry, today=None, thresholds=None):
    """('viva'|'rezagada'|'congelada'|'desconocida', months_stale_or_None).

    Uses the stored override if present (a few reports are 'al día' with no
    exact date); otherwise computes from `cutoff` against today. Pass
    `catalog["meta"]["vitality_thresholds_months"]` as `thresholds`, or editing
    those numbers in the catalog changes nothing.
    """
    if cat_entry.get("vitality"):
        return cat_entry["vitality"], None
    cutoff = parse_iso(cat_entry.get("cutoff"))
    if cutoff is None:
        return "desconocida", None
    today = today or _dt.date.today()
    months = (today.year - cutoff.year) * 12 + (today.month - cutoff.month)
    return _bucket(months, thresholds), months


def _bucket(months, thresholds=None):
    thresholds = thresholds or {"viva": 4, "rezagada": 18}
    if months <= thresholds["viva"]:
        return "viva"
    if months <= thresholds["rezagada"]:
        return "rezagada"
    return "congelada"


def bucket_for(catalog, months):
    return _bucket(months, catalog["meta"].get("vitality_thresholds_months"))
