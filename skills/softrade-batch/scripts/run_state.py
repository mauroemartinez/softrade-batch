#!/usr/bin/env python3
"""Read and update a Softrade batch manifest.

Every command prints a few lines at most. That is the point: the agent driving a
long batch must never hold the whole manifest in context, only the next job.

  python run_state.py next   RUN_DIR            [--json]
  python run_state.py status RUN_DIR            [--json]
  python run_state.py check  RUN_DIR            (static integrity check vs catalog.json)
  python run_state.py done   RUN_DIR --job 7 --file arg_imports_2024.xlsx [--rows 15230] [--records 2]
  python run_state.py fail   RUN_DIR --job 7 --note "filtro de pais no cargo"
  python run_state.py skip   RUN_DIR --job 7 --note "sin datos para el periodo"
  python run_state.py split  RUN_DIR --job 7 [--max-months 1]
  python run_state.py reset  RUN_DIR --job 7

Prefer `inspect_download.py FILE --record RUN_DIR --job 7` over typing `done`
by hand: it fills file, rows and records from the file itself. Every row count
entered manually is a row count that can be wrong.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

MANIFEST_NAME = "manifest.json"
TERMINAL = {"done", "skipped", "split"}


def _plan_run():
    """plan_run.py, which holds the date helpers and the atomic manifest writer."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import plan_run
    except ImportError:
        sys.exit("cannot import plan_run.py -- keep both scripts in the same directory")
    return plan_run


def load(run_dir):
    path = os.path.join(run_dir, MANIFEST_NAME)
    if not os.path.exists(path):
        sys.exit("no manifest at %s -- run plan_run.py first" % path)
    with open(path, encoding="utf-8") as fh:
        try:
            return path, json.load(fh)
        except ValueError as e:
            sys.exit("manifest at %s is not valid JSON (%s).\n"
                     "Do not re-plan over it: fix it by hand or restore it from a copy."
                     % (path, e))


def save(path, manifest):
    # temp file + os.replace: a write cut short never leaves half a manifest
    _plan_run().write_manifest(path, manifest)


def download_dir(manifest, args):
    """The manifest's download_dir, absolute. A relative one (split_run's
    sub-runs, the coverage master) is relative to RUN_DIR, not to the cwd."""
    return _plan_run().resolve_download_dir(manifest, args.run_dir)


def pick(manifest, index):
    jobs = manifest["jobs"]
    if index < 0 or index >= len(jobs):
        sys.exit("job index %d out of range (0..%d)" % (index, len(jobs) - 1))
    return jobs[index]


def children_of(manifest, index):
    """Indices of the jobs that `split` created from job `index`."""
    return [i for i, j in enumerate(manifest["jobs"])
            if isinstance(j, dict) and j.get("split_from") == index]


def cmd_next(manifest, args):
    # Pending first, failed only once nothing pending is left. Handing a failed
    # job straight back means a run that hit an expired session retries the same
    # broken job forever instead of getting on with the work that can succeed.
    #
    # A job that has children is never handed out, whatever its status: its
    # months belong to them. A manifest left by the old `reset` (parent back to
    # pending next to its children) re-downloaded the whole period on top of
    # them. `split --job N` repairs such a parent.
    parents = {j.get("split_from") for j in manifest["jobs"] if isinstance(j, dict)}
    ordered = [(i, j) for i, j in enumerate(manifest["jobs"])
               if j["status"] == "pending" and i not in parents]
    ordered += [(i, j) for i, j in enumerate(manifest["jobs"])
                if j["status"] == "failed" and i not in parents]

    if getattr(args, "json", False):
        if not ordered:
            print(json.dumps({"done": True}, ensure_ascii=False))
            return 0
        i, job = ordered[0]
        payload = dict(job)
        payload["index"] = i
        payload["download_dir"] = download_dir(manifest, args)
        payload["catalog_version"] = manifest.get("catalog_version")
        payload["preflight"] = manifest.get("preflight") or []
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    for i, job in ordered:
        print("job %d" % i)
        print("  country    %s" % job["country"])
        print("  report     %s" % job["report"])
        print("  date_from  %s" % job["date_from"])
        print("  date_to    %s" % job["date_to"])
        # The filters define the dataset as much as the dates do. Print them
        # every time, so a run resumed in a fresh chat sets the same query
        # instead of quietly downloading a different one.
        filters = job.get("filters") or {}
        if filters:
            for name in sorted(filters):
                print("  %-10s %s" % (name, ", ".join(filters[name])))
        else:
            print("  filters    (none: whole country/period)")
        print("  status     %s (attempts %d)" % (job["status"], job["attempts"]))
        if job.get("note"):
            print("  last_note  %s" % job["note"])
        if job["status"] == "failed":
            print("  RETRY      this job already failed; nothing pending is left.")
            print("             If it fails the same way again, stop and tell the user.")
        print("  save_to    %s" % download_dir(manifest, args))
        return 0
    print("no pending jobs -- run complete")
    return 0


def cmd_status(manifest, args):
    counts = {}
    for job in manifest["jobs"]:
        counts[job["status"]] = counts.get(job["status"], 0) + 1
    total = len(manifest["jobs"])
    done = counts.get("done", 0)
    rows, records, unknown = run_totals(manifest)

    if getattr(args, "json", False):
        print(json.dumps({
            "label": manifest.get("label"),
            "total": total,
            "counts": counts,
            "rows": rows,
            "records": records,
            "files_missing_record_count": unknown,
            "rows_per_record": round(rows / records, 2) if records else None,
            "catalog_version": manifest.get("catalog_version"),
            "preflight": manifest.get("preflight") or [],
            "failed": [
                {"index": i, "country": j["country"], "report": j["report"],
                 "date_from": j["date_from"], "date_to": j["date_to"], "note": j.get("note")}
                for i, j in enumerate(manifest["jobs"]) if j["status"] == "failed"
            ],
        }, ensure_ascii=False, indent=2))
        return 0

    print("%s: %d/%d done" % (manifest.get("label") or "run", done, total))
    for status in sorted(counts):
        print("  %-8s %d" % (status, counts[status]))

    # Rows and records are different numbers and users conflate them constantly.
    # A run of 17 rows can be 2 customs operations. Always show both, and never
    # let a closing summary quote only one.
    print("  rows     %s" % format(rows, ","))
    if unknown:
        print("  records  %s  (+%d file(s) with no record count)" % (format(records, ","), unknown))
    else:
        print("  records  %s" % format(records, ","))
    if records:
        print("           %.2f rows per record" % (rows / float(records)))

    failed = [(i, j) for i, j in enumerate(manifest["jobs"]) if j["status"] == "failed"]
    for i, job in failed[:10]:
        print("  ! job %d %s %s %s..%s: %s" % (i, job["country"], job["report"], job["date_from"], job["date_to"], job.get("note")))

    caveats = manifest.get("preflight") or []
    if caveats:
        print("  preflight (relay these to the user):")
        for c in caveats:
            print("    - %s" % c)
    return 0


def _stamp(job):
    job["updated_at"] = datetime.now().isoformat(timespec="seconds")


def run_totals(manifest):
    """(rows, records, files_missing_a_record_count) across done jobs."""
    rows = records = unknown = 0
    for job in manifest["jobs"]:
        if job["status"] != "done":
            continue
        rows += int(job.get("rows") or 0)
        # A done job with no record count is counted as unknown even when it has
        # no row count either. Leaving it out entirely would make the summary
        # read as complete while a file goes unreported.
        if job.get("records") is None:
            unknown += 1
        else:
            records += int(job["records"])
    return rows, records, unknown


def cmd_done(manifest, args):
    job = pick(manifest, args.job)
    if not args.file:
        sys.exit("--file is required: record the file that actually landed on disk")
    job["status"] = "done"
    job["file"] = args.file
    job["rows"] = args.rows
    job["records"] = args.records
    job["note"] = args.note
    _stamp(job)
    if args.rows is None:
        print("job %d -> done (%s)" % (args.job, args.file))
        print("  WARNING: no row count recorded, so the closing summary cannot")
        print("           report this job. Prefer inspect_download.py --record,")
        print("           which fills it in from the file itself.")
    elif args.records is None:
        print("job %d -> done (%s): %s rows, records unknown" % (args.job, args.file, format(args.rows, ",")))
    else:
        print("job %d -> done (%s): %s rows, %s records" % (
            args.job, args.file, format(args.rows, ","), format(args.records, ",")))
    return 0


def cmd_fail(manifest, args):
    job = pick(manifest, args.job)
    job["status"] = "failed"
    job["attempts"] = job.get("attempts", 0) + 1
    job["note"] = args.note
    _stamp(job)
    print("job %d -> failed (attempt %d): %s" % (args.job, job["attempts"], args.note))
    return 0


def cmd_skip(manifest, args):
    job = pick(manifest, args.job)
    job["status"] = "skipped"
    job["note"] = args.note
    _stamp(job)
    print("job %d -> skipped: %s" % (args.job, args.note))
    return 0


def cmd_split(manifest, args):
    """Break one too-big job into shorter ones, after Softrade refused it.

    This is the second rung of the escalation ladder in SKILL.md: try the whole
    period first, split only when the query actually came back truncated or with
    the "demasiado extensa" notice. Splitting up front turns a single download
    into twelve for no reason, most of them coming back empty.

    The original job is marked `split` rather than deleted, and the new jobs are
    appended, so every index the agent has already seen keeps pointing at the
    same job.

    On a job that already has children but is not `split` (what `check` reports
    as "padre e hijos"), it only marks the job `split` again, without new jobs.
    """
    job = pick(manifest, args.job)
    # Splitting twice appended a second set of pending children over the same
    # months, and `next` handed every period out twice.
    kids = children_of(manifest, args.job)
    if job["status"] == "done":
        if kids:
            sys.exit("job %d is done but has children (%s) over the same period.\n"
                     "`skip` the children that duplicate it instead."
                     % (args.job, ", ".join(str(k) for k in kids)))
        sys.exit("job %d is done -- `reset` it first if you really mean to split it" % args.job)
    if kids and job["status"] != "split":
        # Repair, not a second split: a parent that already has children but
        # is not `split` (the old `reset` left it pending) goes back to `split`
        # and the children it has are kept. No new jobs are created.
        job["status"] = "split"
        job["note"] = args.note or "re-marked split: already has children %s" % (
            ", ".join(str(k) for k in kids))
        _stamp(job)
        print("job %d -> split (repaired; existing children: %s)" % (
            args.job, ", ".join(str(k) for k in kids)))
        print("  no new jobs; run `next` to keep working on the children")
        return 0
    if job["status"] == "split":
        sys.exit(
            "job %d is already split (children: %s).\n"
            "Work on the children instead: split one of them if it is still too large."
            % (args.job, ", ".join(str(k) for k in kids) or "none found"))

    pr = _plan_run()
    month_floor, month_index, split_range = pr.month_floor, pr.month_index, pr.split_range

    date_from = str(job["date_from"]).strip().lower()
    date_to = str(job["date_to"]).strip().lower()
    if date_from in _DATE_PLACEHOLDERS or date_to in _DATE_PLACEHOLDERS:
        sys.exit(
            "job %d uses deferred dates (%s..%s), so it cannot be split by period yet.\n"
            "Open the report, read the concrete loaded month from Softrade, then either\n"
            "record that concrete YYYY-MM date on the job or narrow the query itself\n"
            "(for example use a 6-digit heading instead of 4 digits)." % (
                args.job, job["date_from"], job["date_to"])
        )

    try:
        start, end = month_floor(job["date_from"]), month_floor(job["date_to"])
    except ValueError as e:
        sys.exit(
            "job %d has an invalid date (%s..%s): %s.\n"
            "Fix it by hand in manifest.json; `check` lists it." % (
                args.job, job["date_from"], job["date_to"], e)
        )
    span = month_index(end) - month_index(start) + 1
    max_months = args.max_months or 1

    if span <= 1:
        sys.exit(
            "job %d is already a single month (%s..%s) and still too large.\n"
            "Splitting by period cannot help. Narrow the query itself: add an\n"
            "NCM-SIM code, an aduana, or a country of origin, and plan those as\n"
            "separate jobs with plan_run.py." % (args.job, job["date_from"], job["date_to"])
        )
    if span <= max_months:
        sys.exit("job %d already spans %d month(s), which is <= --max-months %d" % (args.job, span, max_months))

    chunks = split_range(start, end, max_months)
    added = []
    for chunk in chunks:
        added.append({
            "country": job["country"],
            "report": job["report"],
            "date_from": chunk["date_from"],
            "date_to": chunk["date_to"],
            # Sub-jobs inherit the parent's filters. Splitting a period must not
            # silently widen the query.
            "filters": dict(job.get("filters") or {}),
            "status": "pending",
            "file": None,
            "rows": None,
            "records": None,
            "attempts": 0,
            "note": "split from job %d" % args.job,
            "split_from": args.job,
            "updated_at": None,
        })

    first = len(manifest["jobs"])
    manifest["jobs"].extend(added)
    job["status"] = "split"
    job["note"] = args.note or ("split into %d jobs of <=%d month(s)" % (len(added), max_months))
    _stamp(job)

    print("job %d -> split (%s..%s, %d months)" % (args.job, job["date_from"], job["date_to"], span))
    print("  %d new jobs, indices %d..%d" % (len(added), first, first + len(added) - 1))
    print("  run `next` to pick them up in order")
    return 0


def cmd_reset(manifest, args):
    job = pick(manifest, args.job)
    # A split parent covers the same months as its children. Putting it back to
    # pending next to them means `next` downloads that period twice. Reset the
    # children that need it instead; the parent stays `split`.
    kids = children_of(manifest, args.job)
    if kids:
        sys.exit(
            "job %d was split into jobs %s, so it cannot go back to pending:\n"
            "the period would be downloaded twice. Reset the child job(s) that\n"
            "need redoing instead." % (args.job, ", ".join(str(k) for k in kids)))
    job["status"] = "pending"
    job["file"] = None
    job["rows"] = None
    job["records"] = None
    job["note"] = args.note
    _stamp(job)
    print("job %d -> pending" % args.job)
    return 0


_VALID_STATUS = {"pending", "done", "failed", "skipped", "split"}
# date fields may hold a real date or a deferred-resolution placeholder that the
# browser step turns into a concrete month (used by the coverage run)
_DATE_PLACEHOLDERS = {"latest", "ultimo mes cargado", "último mes cargado",
                      "ultimo mes cerrado", "último mes cerrado"}


# Softrade refuses a query wider than this, so a job spanning more is dead on
# arrival no matter how the browser step fills the form.
_MAX_SPAN_MONTHS = 12


def _load_catalog():
    """(catalog, error). catalog is None with no error only when _catalog.py is
    absent, i.e. the scripts were copied without the query engine. A catalog
    that exists but does not load is an error, not a reason to skip validation.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(os.path.join(here, "_catalog.py")):
        return None, None
    sys.path.insert(0, here)
    try:
        import _catalog
        return _catalog.load(), None
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)


def _catalog_version(catalog, manifest_version):
    """The catalog's version in the format the manifest uses. "<date>+<hash>"
    (meta.catalog_version, see _catalog.version) for current manifests; a
    date-only one predates that field and was meta.captured, so it is compared
    against meta.captured instead of warning on every old run."""
    meta = catalog.get("meta") or {}
    if "+" in str(manifest_version):
        return meta.get("catalog_version") or meta.get("captured")
    return meta.get("captured")


def _parse_date(s):
    """YYYY-MM or YYYY-MM-DD -> (year, month), or None if not a real date."""
    m = re.match(r"^(\d{4})-(\d{2})(?:-(\d{2}))?$", s)
    if not m:
        return None
    try:
        datetime(int(m.group(1)), int(m.group(2)), int(m.group(3) or 1))
    except ValueError:
        return None
    return int(m.group(1)), int(m.group(2))


def _check_report(args, jobs, problems, warnings):
    ok = not problems
    if getattr(args, "json", False):
        print(json.dumps({"ok": ok, "jobs": jobs, "problems": problems,
                          "warnings": warnings}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    for w in warnings:
        print("  aviso  %s" % w)
    if problems:
        print("\ncheck: %d problema(s):" % len(problems))
        for p in problems:
            print("  - %s" % p)
        return 1
    print("check: %d jobs, sin problemas%s" % (
        jobs, " (%d avisos)" % len(warnings) if warnings else ""))
    return 0


def _bounds(job):
    """(first_day, last_day) of a job's period as (y, m, d) tuples, or None when
    a date is a placeholder or not a real date. A bare YYYY-MM reads as the whole
    month, so 2026-02 and 2026-02-01..2026-02-28 compare as the same period."""
    out = []
    for d, end in ((job.get("date_from"), False), (job.get("date_to"), True)):
        s = str(d or "")
        ym = _parse_date(s)
        if ym is None:
            return None
        if len(s) > 7:
            out.append((ym[0], ym[1], int(s[8:10])))
        elif end:
            nxt = datetime(ym[0] + ym[1] // 12, ym[1] % 12 + 1, 1)
            out.append((ym[0], ym[1], (nxt - datetime(ym[0], ym[1], 1)).days))
        else:
            out.append((ym[0], ym[1], 1))
    return tuple(out) if out[0] <= out[1] else None


def cmd_check(manifest, args):
    """Static integrity check of a manifest, before or after a run.

    Catches the mistakes that a hand-built or machine-generated manifest tends to
    have: a report id that is not canonical, a country the catalog does not know,
    a `done` job with no file, a bad status, impossible or reversed dates, a
    period wider than Softrade accepts, duplicated or overlapping jobs, a `split`
    job with no children, a job with children that is not `split`. Read-only.
    Exits 1 if anything is wrong so it can gate a review.
    """
    problems, warnings = [], []
    catalog, cat_err = _load_catalog()
    if cat_err:
        problems.append("catalog.json no cargó (%s): no puedo validar país/reporte" % cat_err)
        return _check_report(args, 0, problems, warnings)
    report_ids = set(catalog["report_types"]) if catalog else None
    countries = catalog["countries"] if catalog else None

    jobs = manifest.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        problems.append("el manifiesto no tiene jobs")
        return _check_report(args, 0, problems, warnings)

    seen = {}
    periods = {}       # (país, reporte, filtros) -> [(índice, inicio, fin)]
    children = set()
    for j in jobs:
        if isinstance(j, dict) and isinstance(j.get("split_from"), int):
            children.add(j["split_from"])

    for i, j in enumerate(jobs):
        tag = "job %d" % i
        if not isinstance(j, dict):
            problems.append("%s: no es un objeto (%s)" % (tag, type(j).__name__))
            continue
        for key in ("country", "report", "date_from", "date_to", "status"):
            if key not in j:
                problems.append("%s: falta el campo '%s'" % (tag, key))
        st = j.get("status")
        if st not in _VALID_STATUS:
            problems.append("%s: status inválido %r" % (tag, st))
        cc = str(j.get("country", "")).upper()
        rid = j.get("report")
        if report_ids is not None and rid not in report_ids:
            problems.append("%s: report %r no es un id canónico (%s...)" % (
                tag, rid, ", ".join(sorted(report_ids)[:4])))
        elif countries is not None:
            if cc not in countries:
                problems.append("%s: país %r no está en catalog.json" % (tag, cc))
            elif rid not in countries[cc]["reports"]:
                problems.append("%s: %s no ofrece %r" % (tag, cc, rid))

        parsed = []
        for d in (j.get("date_from"), j.get("date_to")):
            s = str(d or "")
            if s.lower() in _DATE_PLACEHOLDERS:
                parsed.append(None)
                continue
            ym = _parse_date(s)
            if ym is None:
                problems.append("%s: fecha %r no es una fecha YYYY-MM[-DD] real ni un placeholder conocido" % (tag, d))
            parsed.append(ym)
        if parsed[0] and parsed[1]:
            # both are real YYYY-MM[-DD] here, so string order is date order
            if str(j["date_from"]) > str(j["date_to"]):
                problems.append("%s: date_from %s es posterior a date_to %s" % (
                    tag, j["date_from"], j["date_to"]))
            else:
                span = (parsed[1][0] - parsed[0][0]) * 12 + parsed[1][1] - parsed[0][1] + 1
                if span > _MAX_SPAN_MONTHS:
                    problems.append("%s: abarca %d meses (%s..%s); Softrade no acepta más de %d" % (
                        tag, span, j["date_from"], j["date_to"], _MAX_SPAN_MONTHS))

        fkey = json.dumps(j.get("filters") or {}, sort_keys=True, ensure_ascii=False)
        key = (cc, rid, str(j.get("date_from")), str(j.get("date_to")), fkey)
        if key in seen:
            problems.append("%s: duplicado del job %d (mismo país, reporte, fechas y filtros)" % (
                tag, seen[key]))
        else:
            seen[key] = i
            # Same query over months another job already covers: not a duplicate,
            # but those months get downloaded twice. A `split` parent overlaps its
            # children on purpose and is never downloaded, so it is left out.
            bounds = _bounds(j)
            if bounds and st != "split":
                others = periods.setdefault((cc, rid, fkey), [])
                for k, a, b in others:
                    if bounds[0] <= b and a <= bounds[1]:
                        problems.append("%s: se solapa con el job %d (mismo país, reporte y filtros; "
                                        "%s..%s) -- esos meses se bajarían dos veces" % (
                                            tag, k, j["date_from"], j["date_to"]))
                        break
                others.append((i,) + bounds)

        if st == "split" and i not in children:
            problems.append("%s: status split pero ningún job tiene split_from %d" % (tag, i))
        if i in children and st != "split":
            problems.append("%s: status %s pero hay jobs con split_from %d -- el período se "
                            "bajaría dos veces (padre e hijos)%s" % (
                                tag, st, i,
                                "" if st == "done" else
                                "; `run_state.py split --job %d` lo vuelve a marcar split" % i))
        if st == "done":
            if not j.get("file"):
                problems.append("%s: done pero sin 'file'" % tag)
            if j.get("rows") is None:
                warnings.append("%s: done sin conteo de filas (usá inspect_download.py --record)" % tag)
        att = j.get("attempts", 0)
        if att is None:
            att = 0
        if isinstance(att, bool) or not isinstance(att, int):
            problems.append("%s: attempts %r no es un entero" % (tag, att))
        elif att < 0:
            problems.append("%s: attempts negativo" % tag)

    cv = manifest.get("catalog_version")
    want = _catalog_version(catalog, cv) if catalog else None
    if cv and want and cv != want:
        warnings.append("catalog_version del manifiesto (%s) != catalog.json (%s)" % (
            cv, want))
    if catalog is None:
        warnings.append("_catalog.py no está junto a este script: no validé país/reporte")

    return _check_report(args, len(jobs), problems, warnings)


COMMANDS = {
    "next": (cmd_next, False),
    "status": (cmd_status, False),
    "check": (cmd_check, False),
    "done": (cmd_done, True),
    "fail": (cmd_fail, True),
    "skip": (cmd_skip, True),
    "split": (cmd_split, True),
    "reset": (cmd_reset, True),
}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=sorted(COMMANDS))
    ap.add_argument("run_dir")
    ap.add_argument("--job", type=int, help="job index from `next`")
    ap.add_argument("--file", help="filename that landed in download_dir")
    ap.add_argument("--rows", type=int, help="row count of the downloaded file")
    ap.add_argument("--records", type=int, help="distinct customs operations in the file (not rows)")
    ap.add_argument("--max-months", type=int, help="months per sub-job for `split` (default 1)")
    ap.add_argument("--note", help="free-text note")
    ap.add_argument("--json", action="store_true",
                    help="machine-readable output for `next`, `status` and `check`")
    args = ap.parse_args(argv)

    handler, writes = COMMANDS[args.command]
    path, manifest = load(args.run_dir)
    if writes and args.job is None:
        sys.exit("--job is required for `%s`" % args.command)
    rc = handler(manifest, args)
    if writes:
        save(path, manifest)
    return rc


if __name__ == "__main__":
    sys.exit(main())
