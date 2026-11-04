#!/usr/bin/env python3
"""Merge the downloads of a finished Softrade run into one workbook.

A segmented run (a job split by month after truncation) or a request that spans
several years or countries ends with N files. Joining them by hand is where
operations get duplicated, or two reports with different columns get mixed. This
does it from the manifest, so the user gets one file:

  python merge_run.py RUN_DIR                       (-> RUN_DIR/consolidado.xlsx)
  python merge_run.py RUN_DIR --out todo.csv        (csv: one country/report only)
  python merge_run.py RUN_DIR --allow-partial       (merge despite pending/failed jobs)
  python merge_run.py RUN_DIR --json

What it does:
  - takes every `done` job, leaving out split parents: their months belong to
    their children, so merging both would count the period twice;
  - refuses while jobs are pending or failed, unless --allow-partial (the
    summary then says PARCIAL, and so must the hand-over);
  - groups by country + report, one xlsx sheet each. Within a group every file
    must have the same columns (order may differ); a mismatch is an error that
    names the columns, never a silent union full of blanks;
  - adds `origen_job` and `origen_periodo` to every row;
  - drops a row only when it repeats a row already kept from another job of the
    same group whose period OVERLAPS this one. Identical rows inside one file, or
    in non-overlapping months, are real line items and stay;
  - recounts rows and operations (records) on the merged data, with
    inspect_download's own counting, and prints both;
  - flags the segments that look wrong next to their siblings (same country,
    report and filters): empty while the others have data, far fewer rows than
    the others, most of them empty, or a file whose row count no longer matches
    the manifest. That is the "segmented run that came back mostly empty" check
    of SKILL.md Step 3: run the whole period once as a single job and compare.

Cells keep the type Softrade exported: numbers and dates stay numbers and dates
(FOB and kg still add up), codes stored as text keep their leading zeros. Columns,
duplicates and operations are compared on the text form of each cell.

Each file is looked up only in the manifest's download_dir (a relative one is
relative to RUN_DIR); a file that is not there is an error, never a guess.

Exit codes: 0 merged, nothing suspicious; 1 refused (pending/failed jobs, column
mismatch, missing or unreadable file, nothing to merge); 3 merged, but some
segments were flagged -- verify them before handing the file over.
"""
import argparse
import json
import os
import re
import statistics
import sys
from collections import Counter

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inspect_download  # noqa: E402
import run_state  # noqa: E402

EXIT_OK, EXIT_REFUSED, EXIT_FLAGGED = 0, 1, 3
DEFAULT_OUT = "consolidado.xlsx"
SOURCE_COLS = ("origen_job", "origen_periodo")

# A segment with fewer rows than this share of its siblings' median is flagged.
# Below SMALL_MIN_MEDIAN rows the siblings are too thin for the ratio to mean
# anything, so only outright empties are flagged there.
SMALL_RATIO = 0.1
SMALL_MIN_MEDIAN = 20

XLSX_MAX_ROWS = 1048575  # Excel's sheet limit, minus the header row


def resolve_file(manifest, run_dir, name):
    """Where job `file` lives: download_dir only, resolved like run_state does
    (absolute, or relative to RUN_DIR). No fallback to RUN_DIR or the cwd: a
    same-named file there is not this job's download."""
    path = os.path.join(run_state._plan_run().resolve_download_dir(manifest, run_dir), name)
    return path if os.path.isfile(path) else None


def read_typed(path, text):
    """The same sheet with the cell types the workbook stores (numbers, dates),
    for the output. A csv has no types, so it stays as text."""
    if os.path.splitext(path)[1].lower() not in (".xlsx", ".xlsm", ".xls"):
        return text
    import warnings

    import pandas as pd

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        typed = pd.read_excel(path, dtype=object)  # raw cells: "0854" stays str
    if typed.shape != text.shape:
        return text  # cannot be lined up row by row; text is still correct
    typed.columns = text.columns
    return typed


def load_frame(path):
    """((text, typed), None) or (None, reason). Same checks as inspect_download.
    `text` (all str) is for comparing; `typed` keeps numbers and dates for writing."""
    if os.path.getsize(path) == 0:
        return None, "0 bytes"
    if inspect_download.looks_like_html(path):
        return None, "HTML en vez de planilla (sesión vencida?)"
    try:
        text = inspect_download.read_table(path)
        return (text, read_typed(path, text)), None
    except ImportError as exc:
        sys.exit("missing dependency (%s: %s); install pandas, openpyxl and xlrd, then re-run"
                 % (type(exc).__name__, exc))
    except SystemExit as exc:
        return None, str(exc.code)
    except Exception as exc:
        return None, "ilegible (%s: %s)" % (type(exc).__name__, str(exc)[:120])


def period(job):
    return "%s..%s" % (job.get("date_from"), job.get("date_to"))


def overlaps(a, b):
    """Do two jobs cover a common day? A placeholder date ("latest") cannot be
    placed, so it is assumed to overlap: only whole-row repeats are dropped, and
    a whole row repeated across two queries is the same line item."""
    ba, bb = run_state._bounds(a), run_state._bounds(b)
    if ba is None or bb is None:
        return True
    return ba[0] <= bb[1] and bb[0] <= ba[1]


def sheet_name(key, used):
    base = re.sub(r"[\[\]:*?/\\]", "_", "%s_%s" % key)[:31]
    name, n = base, 2
    while name in used:
        suffix = "_%d" % n
        name, n = base[:31 - len(suffix)] + suffix, n + 1
    used.add(name)
    return name


def flag_segments(segments):
    """Per-job flags and group-level warnings for the near-empty check.

    segments: [(index, job, rows)] with rows read from the file (0 for skipped).
    """
    flags = {i: [] for i, _, _ in segments}
    group_flags = []
    siblings = {}
    for i, job, rows in segments:
        key = (str(job.get("country", "")).upper(), job.get("report"),
               json.dumps(job.get("filters") or {}, sort_keys=True, ensure_ascii=False))
        siblings.setdefault(key, []).append((i, job, rows))

    for (cc, rid, _), members in siblings.items():
        if len(members) < 2:
            continue
        for i, job, rows in members:
            others = [r for k, _, r in members if k != i]
            med = statistics.median(others)
            if rows == 0 and max(others) > 0:
                flags[i].append("vacío: 0 filas mientras otros tramos hermanos traen hasta %s"
                                % format(max(others), ","))
            elif rows and med >= SMALL_MIN_MEDIAN and rows < SMALL_RATIO * med:
                flags[i].append("pocas filas: %s contra una mediana de %s en los tramos hermanos"
                                % (format(rows, ","), format(int(med), ",")))
        empties = sum(1 for _, _, r in members if r == 0)
        if empties * 2 > len(members):
            span = "%s..%s" % (min(str(j.get("date_from")) for _, j, _ in members),
                               max(str(j.get("date_to")) for _, j, _ in members))
            group_flags.append(
                "%s %s: mayoría de tramos vacíos (%d de %d) en %s. Corré el período completo "
                "una vez como un solo job y compará operaciones (SKILL.md, Step 3)"
                % (cc, rid, empties, len(members), span))
    return flags, group_flags


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("--out", help="output .xlsx or .csv (default RUN_DIR/%s)" % DEFAULT_OUT)
    ap.add_argument("--allow-partial", action="store_true",
                    help="merge the done jobs even if some are pending or failed")
    ap.add_argument("--json", action="store_true", help="machine-readable summary")
    args = ap.parse_args(argv)

    out_path = args.out or os.path.join(args.run_dir, DEFAULT_OUT)
    ext = os.path.splitext(out_path)[1].lower()
    if ext not in (".xlsx", ".csv"):
        sys.exit("--out must end in .xlsx or .csv, not %r" % ext)

    _, manifest = run_state.load(args.run_dir)
    jobs = manifest.get("jobs") or []
    parents = {j.get("split_from") for j in jobs if isinstance(j, dict)}
    usable = [(i, j) for i, j in enumerate(jobs) if isinstance(j, dict) and i not in parents]
    open_jobs = [(i, j) for i, j in usable if j.get("status") in ("pending", "failed")]
    done = [(i, j) for i, j in usable if j.get("status") == "done"]
    skipped = [(i, j) for i, j in usable if j.get("status") == "skipped"]

    problems = []

    def refuse():
        if args.json:
            print(json.dumps({"ok": False, "output": None, "problems": problems},
                             ensure_ascii=False, indent=2))
        else:
            print("merge: %d problema(s), no se escribió nada:" % len(problems))
            for p in problems:
                print("  - %s" % p)
        return EXIT_REFUSED

    if open_jobs and not args.allow_partial:
        for i, j in open_jobs[:10]:
            problems.append("job %d %s %s %s está %s%s" % (
                i, j.get("country"), j.get("report"), period(j), j.get("status"),
                ": %s" % j["note"] if j.get("note") else ""))
        if len(open_jobs) > 10:
            problems.append("... y %d más" % (len(open_jobs) - 10))
        problems.append("terminá la corrida o pasá --allow-partial y decí que el archivo es parcial")
        return refuse()

    keys = []
    for _, j in done:
        key = (str(j.get("country", "")).upper(), j.get("report"))
        if key not in keys:
            keys.append(key)
    if ext == ".csv" and len(keys) > 1:
        problems.append("un .csv admite un solo país/reporte y hay %d (%s); usá --out con .xlsx "
                        "(una hoja por país/reporte)" % (len(keys), ", ".join("%s %s" % k for k in keys)))
        return refuse()

    frames, typed = {}, {}
    for i, j in done:
        if not j.get("file"):
            problems.append("job %d: done pero sin 'file'" % i)
            continue
        path = resolve_file(manifest, args.run_dir, j["file"])
        if path is None:
            problems.append("job %d: no encuentro %s en download_dir" % (i, j["file"]))
            continue
        pair, err = load_frame(path)
        if err:
            problems.append("job %d: %s -- %s" % (i, j["file"], err))
            continue
        frame = pair[0]
        clash = [c for c in SOURCE_COLS if c in frame.columns]
        if clash:
            problems.append("job %d: el archivo ya trae columna(s) %s" % (i, ", ".join(clash)))
            continue
        frames[i], typed[i] = pair

    # Same country + report must mean same layout.
    by_key = {k: [] for k in keys}
    for i, j in done:
        if i in frames:
            by_key[(str(j.get("country", "")).upper(), j.get("report"))].append(i)
    for key, members in by_key.items():
        if not members:
            continue
        ref = members[0]
        ref_cols = [str(c) for c in frames[ref].columns]
        for i in members[1:]:
            cols = [str(c) for c in frames[i].columns]
            if set(cols) != set(ref_cols):
                missing = [c for c in ref_cols if c not in cols]
                extra = [c for c in cols if c not in ref_cols]
                problems.append("%s %s: job %d tiene columnas distintas que job %d (faltan: %s; sobran: %s)"
                                % (key[0], key[1], i, ref, ", ".join(missing) or "-",
                                   ", ".join(extra) or "-"))
    if problems:
        return refuse()

    # Near-empty check, on the rows actually in the files.
    segments = [(i, j, len(frames[i])) for i, j in done]
    segments += [(i, j, 0) for i, j in skipped]
    segments.sort(key=lambda s: s[0])
    flags, group_flags = flag_segments(segments)
    for i, j in done:
        recorded = j.get("rows")
        if recorded is not None and int(recorded) != len(frames[i]):
            flags[i].append("el manifiesto dice %s filas y el archivo tiene %s"
                            % (format(int(recorded), ","), format(len(frames[i]), ",")))

    import pandas as pd

    dropped = {}
    records = {}
    groups = []
    used_sheets = set()
    for key, members in by_key.items():
        if not members:
            continue
        cols = [str(c) for c in frames[members[0]].columns]
        kept_rows = {}  # job -> Counter of rows kept from it
        parts, texts = [], []
        for i in members:
            frame, out = frames[i], typed[i]
            frame.columns = [str(c) for c in frame.columns]
            out.columns = [str(c) for c in out.columns]
            frame, out = frame[cols], out[cols]
            records[i] = inspect_download.count_records(frame)[0]
            tuples = list(frame.fillna("").itertuples(index=False, name=None))
            budget = Counter()
            for k, kept in kept_rows.items():
                if overlaps(jobs[k], jobs[i]):
                    budget.update(kept)
            mask = []
            for t in tuples:
                if budget[t] > 0:
                    budget[t] -= 1
                    mask.append(False)
                else:
                    mask.append(True)
            kept_rows[i] = Counter(t for t, m in zip(tuples, mask) if m)
            dropped[i] = mask.count(False)
            # Compared as text, written with the workbook's own types.
            out = out[mask].copy()
            out[SOURCE_COLS[0]] = str(i)
            out[SOURCE_COLS[1]] = period(jobs[i])
            parts.append(out)
            texts.append(frame[mask])
        merged = pd.concat(parts, ignore_index=True)
        if ext == ".xlsx" and len(merged) > XLSX_MAX_ROWS:
            problems.append("%s %s: %s filas no entran en una hoja de Excel; usá --out con .csv"
                            % (key[0], key[1], format(len(merged), ",")))
            continue
        recs, how = inspect_download.count_records(pd.concat(texts, ignore_index=True))
        groups.append({"country": key[0], "report": key[1],
                       "sheet": sheet_name(key, used_sheets) if ext == ".xlsx" else None,
                       "jobs": members, "rows": len(merged), "records": recs,
                       "record_basis": how, "duplicates_dropped": sum(dropped[i] for i in members),
                       "frame": merged})
    if problems:
        return refuse()

    if groups:
        parent = os.path.dirname(os.path.abspath(out_path))
        os.makedirs(parent, exist_ok=True)
        if ext == ".csv":
            groups[0]["frame"].to_csv(out_path, index=False, encoding="utf-8-sig")
        else:
            with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
                for g in groups:
                    g["frame"].to_excel(writer, sheet_name=g["sheet"], index=False)

    flagged = any(flags.values()) or bool(group_flags)
    partial = bool(open_jobs)
    # Nothing written is a refusal even when segments were flagged: exit 3
    # promises a file to verify and hand over.
    rc = EXIT_REFUSED if not groups else (EXIT_FLAGGED if flagged else EXIT_OK)

    job_rows = []
    for i, j, rows in segments:
        job_rows.append({"index": i, "country": j.get("country"), "report": j.get("report"),
                         "period": period(j), "status": j.get("status"), "rows": rows,
                         "records": records.get(i, 0 if j.get("status") == "skipped" else None),
                         "dropped": dropped.get(i, 0), "flags": flags[i]})

    if args.json:
        print(json.dumps({
            "ok": bool(groups),
            "output": os.path.abspath(out_path) if groups else None,
            "partial": partial,
            "open_jobs": [i for i, _ in open_jobs],
            "groups": [{k: v for k, v in g.items() if k != "frame"} for g in groups],
            "jobs": job_rows,
            "warnings": group_flags,
            "flagged": flagged,
        }, ensure_ascii=False, indent=2))
        return rc

    for r in job_rows:
        line = "  job %-4d %s %s  %s  %-7s %s filas" % (
            r["index"], r["country"], r["report"], r["period"], r["status"], format(r["rows"], ","))
        if r["records"] is not None:
            line += ", %s ops" % format(r["records"], ",")
        if r["dropped"]:
            line += "  (-%d duplicadas por solape)" % r["dropped"]
        print(line)
        for f in r["flags"]:
            print("           ! %s" % f)
    for i, j in open_jobs:
        print("  job %-4d %s %s  %s  %s -- NO incluido" % (
            i, j.get("country"), j.get("report"), period(j), j.get("status")))

    if not groups:
        print("merge: ningún job done con datos, no se escribió nada")
    else:
        print("merge%s: %s" % (" PARCIAL" if partial else "", os.path.abspath(out_path)))
        for g in groups:
            # Rows and operations are different numbers; always give both.
            recs = format(g["records"], ",") if g["records"] is not None else "desconocidas"
            print("  %s%s %s: %d job(s), %s filas, %s ops%s" % (
                "[%s] " % g["sheet"] if g["sheet"] else "", g["country"], g["report"],
                len(g["jobs"]), format(g["rows"], ","), recs,
                ", %d filas duplicadas quitadas" % g["duplicates_dropped"] if g["duplicates_dropped"] else ""))
        if partial:
            print("  PARCIAL: %d job(s) pendientes o fallidos no están incluidos; decíselo al usuario"
                  % len(open_jobs))
    for w in group_flags:
        print("  ! %s" % w)
    if flagged and groups:
        print("verificá los tramos marcados con ! antes de entregar (exit %d)" % EXIT_FLAGGED)
    return rc


if __name__ == "__main__":
    sys.exit(main())
