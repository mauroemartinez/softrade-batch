#!/usr/bin/env python3
"""Build (or extend) a Softrade batch download manifest.

The manifest is the single source of truth for a batch run. It lives on disk so
a run survives the chat session that started it: if the conversation dies, a new
one reads the manifest and resumes at the first pending job.

Usage:
  python plan_run.py --out RUN_DIR \
      --country ar --country br \
      --report imports_detailed \
      --from 2023-01 --to 2025-12 \
      [--max-months 12] [--label "q3-research"]

Re-running against an existing manifest adds only the months that are missing;
jobs already in it are never touched. A period that overlaps one already
planned for the same country, report and filters is trimmed to the days no
job covers yet, so nothing is downloaded twice and a job that covers only part
of a month (say 2025-02-01..2025-02-15) gets the rest of that month planned.

Plan wide, narrow later. `--max-months` defaults to 12 because that is Softrade's
own ceiling, so a request that fits inside a year is ONE job and ONE consolidated
Excel. Do not pre-split into months on a hunch: a narrow query over a full year is
routinely a handful of operations, and twelve monthly jobs would mean twelve
downloads, twelve renames and eleven empty files. When a query does come back
truncated, split that job then, with `run_state.py split`.
"""
import argparse
import json
import os
import sys
import tempfile
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import _catalog
    import preflight as _preflight
except ImportError:  # scripts moved apart; validation just gets skipped
    _catalog = None
    _preflight = None

MANIFEST_NAME = "manifest.json"
# Softrade refuses a query wider than this, so it is also the ceiling for --max-months.
MAX_MONTHS = 12


def write_manifest(path, manifest):
    """Write manifest.json atomically: a temp file in the same directory, then
    os.replace. A crash or a full disk mid-write leaves the previous manifest
    whole instead of a truncated one that no command can read. Same format as
    always (indent 2, accents as-is, trailing newline), so diffs stay clean.

    Shared by run_state.py, inspect_download.py --record and tools/split_run.py.
    It does not lock: two writers at once can still lose one update.
    """
    folder = os.path.dirname(os.path.abspath(path))
    try:
        mode = os.stat(path).st_mode & 0o777
    except OSError:
        mode = 0o644
    fd, tmp = tempfile.mkstemp(prefix=".manifest-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def resolve_download_dir(manifest, run_dir):
    """download_dir as an absolute path. A relative one (old manifests, the
    coverage run) is relative to the run dir, never to the current directory."""
    d = manifest.get("download_dir") or "downloads"
    return d if os.path.isabs(d) else os.path.abspath(os.path.join(run_dir, d))


def month_floor(value):
    """Parse YYYY-MM (or YYYY-MM-DD) into a (year, month) tuple.

    Raises ValueError for anything that is not a real month (2026-13) or day
    (2026-02-30): with --skip-preflight nothing else looks at the dates.
    """
    parts = str(value).strip().split("-")
    if len(parts) not in (2, 3):
        raise ValueError("expected YYYY-MM, got %r" % value)
    try:
        nums = [int(p) for p in parts]
        date(nums[0], nums[1], nums[2] if len(nums) == 3 else 1)
    except ValueError:
        raise ValueError("%r is not a real YYYY-MM[-DD] date" % value)
    return nums[0], nums[1]


def month_index(ym):
    year, month = ym
    return year * 12 + (month - 1)


def from_index(idx):
    return idx // 12, (idx % 12) + 1


def last_day(year, month):
    if month == 12:
        return 31
    nxt = date(year, month + 1, 1)
    return (nxt.toordinal() - 1) - date(year, month, 1).toordinal() + 1


def split_range(start, end, max_months):
    """Split an inclusive month range into chunks of at most max_months."""
    if max_months < 1:
        raise ValueError("--max-months must be >= 1")
    s, e = month_index(start), month_index(end)
    if e < s:
        raise ValueError("--from is after --to")
    chunks = []
    cur = s
    while cur <= e:
        stop = min(cur + max_months - 1, e)
        sy, sm = from_index(cur)
        ey, em = from_index(stop)
        chunks.append(
            {
                "date_from": "%04d-%02d-01" % (sy, sm),
                "date_to": "%04d-%02d-%02d" % (ey, em, last_day(ey, em)),
            }
        )
        cur = stop + 1
    return chunks


def filters_key(filters):
    """Stable, hashable form of a filter set, for deduplication."""
    return tuple(sorted((k, tuple(v)) for k, v in (filters or {}).items()))


def _canon(country, report):
    """Canonical (COUNTRY, reportId), falling back to the raw values.

    Manifests written before catalog.json existed, or with --skip-preflight,
    hold the country and report exactly as typed. Comparing those raw against
    canonical ids made re-planning the same run duplicate every job.
    """
    cc = (country or "").strip().upper()
    if _catalog is not None:
        try:
            return cc, _catalog.resolve_report(_catalog.load(), report)
        except Exception:
            pass
    return cc, report


def _day_bounds(job):
    """(first, last) day ordinals of a job's period, or None when a date is a
    placeholder, unreadable or reversed. A bare YYYY-MM reads as the whole
    month, the same rule `run_state.py check` applies (`_bounds`)."""
    out = []
    for value, is_end in ((job.get("date_from"), False), (job.get("date_to"), True)):
        parts = str(value or "").split("-")
        try:
            y, m = int(parts[0]), int(parts[1])
            if len(parts) > 2:
                d = int(parts[2])
            else:
                d = last_day(y, m) if is_end else 1
            out.append(date(y, m, d).toordinal())
        except (IndexError, ValueError):
            return None
    return tuple(out) if out[0] <= out[1] else None


def covered_days(jobs):
    """{(country, report, filters_key): set of day ordinals} already planned.

    Every job counts, whatever its status: done, failed and skipped periods are
    already accounted for, and a `split` parent's days belong to its children.
    Jobs with placeholder or unreadable dates cover nothing.

    Days, not months: a job for 2025-02-01..2025-02-15 covers half of February.
    Counting the whole month as planned left 16..28 with no job at all, and
    `check` (which compares days) had nothing to report.
    """
    out = {}
    for j in jobs:
        bounds = _day_bounds(j)
        if bounds is None or "country" not in j or "report" not in j:
            continue
        cc, rid = _canon(j["country"], j["report"])
        out.setdefault((cc, rid, filters_key(j.get("filters"))), set()).update(
            range(bounds[0], bounds[1] + 1))
    return out


def missing_chunks(start, end, covered, max_months):
    """split_range over [start, end] minus the covered days: each run of
    uncovered days is split on its own, so a chunk never crosses into days
    another job already has. A run that starts or ends mid-month (next to a
    partial job) keeps that exact day as its bound."""
    first = date(start[0], start[1], 1).toordinal()
    last = date(end[0], end[1], last_day(*end)).toordinal()
    chunks, run = [], []
    for day in range(first, last + 2):
        if day <= last and day not in covered:
            run.append(day)
        elif run:
            a, b = date.fromordinal(run[0]), date.fromordinal(run[-1])
            part = split_range((a.year, a.month), (b.year, b.month), max_months)
            part[0]["date_from"] = a.isoformat()
            part[-1]["date_to"] = b.isoformat()
            chunks += part
            run = []
    return chunks


def build_jobs(countries, reports, chunks, filters=None):
    jobs = []
    for country in countries:
        for report in reports:
            for chunk in chunks:
                jobs.append(
                    {
                        "country": country,
                        "report": report,
                        "date_from": chunk["date_from"],
                        "date_to": chunk["date_to"],
                        # The filters are half the query. A job that records only
                        # country/report/dates cannot be reproduced: "importaciones
                        # de AR en 2024" is a different dataset for every importer.
                        # Leaving them in the chat means a resumed run silently
                        # queries something else.
                        "filters": dict(filters or {}),
                        "status": "pending",
                        "file": None,
                        "rows": None,
                        "records": None,
                        "attempts": 0,
                        "note": None,
                        "updated_at": None,
                    }
                )
    return jobs


def _first_filter_name(filters):
    for name in ("importador", "exportador", "proveedor", "comprador"):
        if filters.get(name):
            return name
    return None


# Which side of a report each company filter names. An import report's local
# company is the importer and its foreign counterparty the supplier; an export
# report's are the exporter and the buyer.
_SIDE = {
    "import": {"importador": "local", "proveedor": "counterparty"},
    "export": {"exportador": "local", "comprador": "counterparty"},
}


def _direction_problems(filters, direction, tag):
    """Company filters that make no sense for this report's direction."""
    if direction not in _SIDE:          # both / n/a: the form decides
        return []
    ok = _SIDE[direction]
    out = []
    for name in ("importador", "exportador", "proveedor", "comprador"):
        if filters.get(name) and name not in ok:
            right = [k for k, v in ok.items() if v == _SIDE_OF[name]]
            out.append("[%s] --%s no aplica a un reporte de %s%s"
                       % (tag, name,
                          "importaciones" if direction == "import" else "exportaciones",
                          " (usá --%s)" % right[0] if right else ""))
    return out


_SIDE_OF = {"importador": "local", "exportador": "local",
            "proveedor": "counterparty", "comprador": "counterparty"}


def validate(countries, reports, filters, date_from, date_to, skip=False):
    """Check every country/report against catalog.json before a manifest is built.

    Returns (canonical_countries, canonical_reports, catalog_version, warnings).
    `warnings` is the deduplicated list of preflight caveats (frozen bases,
    inferred names, euros/FOB, ...) so `main` can persist them in the manifest:
    a run resumed in a fresh chat then has the caveats to relay without rerunning
    preflight. Exits non-zero with a Spanish explanation if any combination is
    impossible; warnings are surfaced, not fatal.
    """
    if skip or _catalog is None:
        if not skip:
            print("aviso: catalog.json no disponible, salteo la validación", file=sys.stderr)
        return [c.upper() for c in countries], reports, None, []
    try:
        catalog = _catalog.load()
    except _catalog.CatalogError as ex:
        print("aviso: %s -- salteo la validación" % ex, file=sys.stderr)
        return [c.upper() for c in countries], reports, None, []

    by_company = _first_filter_name(filters)
    want_counterparty = bool(filters.get("proveedor") or filters.get("comprador"))
    canon_countries, canon_reports, problems, warns = [], [], [], []

    for raw_c in countries:
        for raw_r in reports:
            try:
                cc, rid, e = _catalog.entry(catalog, raw_c, raw_r)
            except _catalog.CatalogError as ex:
                problems.append(str(ex))
                continue
            if cc not in canon_countries:
                canon_countries.append(cc)
            if rid not in canon_reports:
                canon_reports.append(rid)

            tag = "%s/%s" % (cc, rid)
            problems += _direction_problems(
                filters, catalog["report_types"][rid]["direction"], tag)
            res = _preflight.evaluate(catalog, cc, rid, bool(by_company),
                                      date_from, date_to)
            if res["verdict"] == "IMPOSSIBLE":
                problems += ["[%s] %s" % (tag, m) for m in res["messages_es"]]
            elif res["verdict"] == "WARN":
                for m in res["messages_es"]:
                    line = "[%s] %s" % (tag, m)
                    if line not in warns:
                        warns.append(line)

            # a --proveedor filter needs the report to actually name the counterparty
            if want_counterparty and not (e["names"]["counterparty"] and
                                          e["names"]["counterparty"] != "unknown"):
                problems.append("[%s] pediste filtrar por la contraparte extranjera "
                                "pero este reporte no la nombra" % tag)

    for w in warns:
        print("  aviso  %s" % w, file=sys.stderr)
    if problems:
        print("\nplan_run: la corrida no se puede planificar así:\n", file=sys.stderr)
        for p in problems:
            print("  - %s" % p, file=sys.stderr)
        print("\nCorregí el pedido (o pasá --skip-preflight si sabés lo que hacés).",
              file=sys.stderr)
        sys.exit(2)

    return canon_countries, canon_reports, _catalog.version(catalog), warns


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="run directory; manifest.json is written inside it")
    ap.add_argument("--country", action="append", required=True, help="repeatable country code, e.g. ar")
    ap.add_argument("--report", action="append", required=True,
                    help="repeatable report id or free text, e.g. importDetalladas / 'impo detalladas'")
    ap.add_argument("--from", dest="date_from", required=True, help="first month, YYYY-MM")
    ap.add_argument("--to", dest="date_to", required=True, help="last month, YYYY-MM")
    ap.add_argument("--max-months", type=int, default=MAX_MONTHS,
                    help="max months per job (Softrade refuses queries over 12; leave at 12 "
                         "and split later with run_state.py split, only if a query truncates)")
    ap.add_argument("--label", default=None, help="free-text label for this run")
    ap.add_argument("--skip-preflight", action="store_true",
                    help="do not validate country/report/period against catalog.json")

    f = ap.add_argument_group(
        "filters",
        "Everything that narrows the query beyond country/report/period. Record "
        "these HERE, never only in the chat: they are what makes a resumed run "
        "reproduce the same dataset. Each is repeatable.")
    f.add_argument("--importador", action="append", metavar="NAME",
                   help="entity name exactly as Softrade spells it")
    f.add_argument("--exportador", action="append", metavar="NAME")
    f.add_argument("--proveedor", action="append", metavar="NAME",
                   help="foreign supplier, on import reports")
    f.add_argument("--comprador", action="append", metavar="NAME",
                   help="foreign buyer, on export reports")
    f.add_argument("--ncm", action="append", metavar="CODE",
                   help="tariff code, whatever the country's nomenclature calls it")
    f.add_argument("--aduana", action="append", metavar="NAME")
    f.add_argument("--pais-origen", dest="pais_origen", action="append", metavar="COUNTRY")
    f.add_argument("--marca", action="append", metavar="NAME")

    args = ap.parse_args(argv)
    if not 1 <= args.max_months <= MAX_MONTHS:
        ap.error("--max-months tiene que estar entre 1 y %d: Softrade no acepta "
                 "consultas de más de %d meses" % (MAX_MONTHS, MAX_MONTHS))

    filters = {k: v for k, v in (
        ("importador", args.importador), ("exportador", args.exportador),
        ("proveedor", args.proveedor), ("comprador", args.comprador),
        ("ncm", args.ncm), ("aduana", args.aduana),
        ("pais_origen", args.pais_origen), ("marca", args.marca),
    ) if v}

    # The period first, and always: --skip-preflight skips the catalog, not
    # the calendar.
    try:
        chunks = split_range(month_floor(args.date_from), month_floor(args.date_to),
                             args.max_months)
    except ValueError as ex:
        print("plan_run: período inválido (%s). Usá --from/--to YYYY-MM, con --from "
              "anterior o igual a --to." % ex, file=sys.stderr)
        sys.exit(2)

    countries, reports, catalog_version, warnings = validate(
        args.country, args.report, filters, args.date_from, args.date_to,
        skip=args.skip_preflight)

    fresh = build_jobs(countries, reports, chunks, filters)

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, MANIFEST_NAME)

    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            manifest = json.load(fh)
        covered = covered_days(manifest["jobs"])
        start, end = month_floor(args.date_from), month_floor(args.date_to)
        want = range(date(start[0], start[1], 1).toordinal(),
                     date(end[0], end[1], last_day(*end)).toordinal() + 1)
        added, trimmed = [], 0
        for country in countries:
            for report in reports:
                have = covered.get(
                    _canon(country, report) + (filters_key(filters),), set())
                # months planned in whole or in part, counted once each
                trimmed += len({(date.fromordinal(d).year, date.fromordinal(d).month)
                                for d in want if d in have})
                added += build_jobs([country], [report],
                                    missing_chunks(start, end, have, args.max_months),
                                    filters)
        if trimmed and added:
            print("  aviso  %d mes(es) del período ya estaban planificados (en todo o en "
                  "parte) con los mismos filtros; agrego solo los días que faltan" % trimmed,
                  file=sys.stderr)
        manifest["jobs"].extend(added)
        # keep the caveats current with the widened run
        merged = list(manifest.get("preflight") or [])
        for w in warnings:
            if w not in merged:
                merged.append(w)
        manifest["preflight"] = merged
        verb = "extended"
        count = len(added)
    else:
        manifest = {
            "version": 1,
            "label": args.label,
            "created_at": date.today().isoformat(),
            "download_dir": os.path.abspath(os.path.join(args.out, "downloads")),
            "max_months": args.max_months,
            "catalog_version": catalog_version,
            "preflight": warnings,
            "jobs": fresh,
        }
        verb = "created"
        count = len(fresh)

    download_dir = resolve_download_dir(manifest, args.out)
    os.makedirs(download_dir, exist_ok=True)
    write_manifest(path, manifest)

    total = len(manifest["jobs"])
    pending = sum(1 for j in manifest["jobs"] if j["status"] == "pending")
    print("%s %s" % (verb, path))
    print("  jobs %s (+%d)  pending %d" % (total, count, pending))
    print("  downloads -> %s" % download_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
