#!/usr/bin/env python3
"""Inspect a downloaded Softrade export and report its shape.

Four jobs:
  1. Confirm the file is real data and not an error page or an empty export.
  2. Detect silent truncation. Softrade caps a query at 30,000 customs RECORDS,
     not rows, and the export expands each record into one row per line item. A
     complete file can therefore hold far more than 30,000 rows, and a truncated
     one can look perfectly normal. Counting rows cannot tell the difference.
  3. Print the column layout so it can be compared against, or written into,
     references/columns.md -- without ever loading the rows into the chat.
  4. Record the outcome in the manifest itself, with --record.

Usage:
  python inspect_download.py FILE [--json]
  python inspect_download.py FILE --record RUN_DIR --job 7

`--record` is the preferred path. It writes file, rows and records straight into
the manifest and picks the status from what the file actually contains, so no
count is ever retyped by hand:

  real data      -> done
  zero rows      -> skipped ("sin datos para el periodo")
  truncated      -> failed  (the file is incomplete; split the job and redo it)
  HTML / 0 bytes -> failed  (expired session or an export that never happened)

Exit codes: 0 file looks good, 2 file is empty or unreadable, 3 file is truncated.
"""
import argparse
import json
import os
import sys

# Softrade column names carry accents. On Windows the console defaults to cp1252
# and mangles them, which matters because these names get copied into references.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ERROR_MARKERS = ("<html", "<!doctype", "sesion expirada", "session expired", "login")

# Softrade refuses to return more than this many customs records per query, with
# the on-screen notice "Consulta demasiado extensa. Solo se toman en cuenta los
# primeros 30.000 registros". The Excel carries no trace of that warning.
RECORD_CAP = 30000


def looks_like_html(path):
    with open(path, "rb") as fh:
        head = fh.read(512).decode("utf-8", "ignore").lower().strip()
    return any(marker in head for marker in ERROR_MARKERS)


def read_table(path):
    import pandas as pd

    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm", ".xls"):
        # Softrade workbooks declare no default style; the warning is harmless.
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            return pd.read_excel(path, dtype=str)
    if ext in (".csv", ".txt"):
        for sep in (",", ";", "\t", "|"):
            try:
                frame = pd.read_csv(path, dtype=str, sep=sep, engine="python")
            except Exception:
                continue
            if frame.shape[1] > 1:
                return frame
        return pd.read_csv(path, dtype=str, engine="python")
    raise SystemExit("unsupported extension: %s" % ext)


def count_records(frame):
    """Number of customs records in the file, as opposed to line-item rows.

    Each record is one declaration and appears as one row per item, numbered from
    1 in the first `Item` column. Where `Identificador` is populated it is the
    better key, but several countries leave it as the literal "No disponible", so
    the item numbering is the reliable fallback.
    """
    cols = list(frame.columns)

    # Every country names the declaration id differently. Seen in the wild:
    # Identificador (AR, BO, EC, VE, GT, HN, SV, PR, NI, DO), Nro. Declaracion (CO),
    # DUA (PE, UY), Despacho (PY), Ordinal (CR, PA, MX, BR cargas), Operacion (BR).
    ID_NAMES = (
        "identificador", "nro. declaracion", "nro. declaración", "nro declaracion",
        "dua", "despacho", "ordinal", "operacion", "operación",
    )
    ident = next((c for c in cols if str(c).strip().lower() in ID_NAMES), None)
    if ident is not None:
        values = frame[ident].dropna()
        values = values[values != "No disponible"]
        if len(values):
            return int(values.nunique()), "distinct %s" % ident

    item = next((c for c in cols if str(c).strip().lower() == "item"), None)
    if item is not None:
        firsts = (frame[item].astype(str).str.strip() == "1").sum()
        if firsts:
            return int(firsts), "rows where %s is 1" % item

    return None, None


def record_outcome(run_dir, index, status, path, rows=None, records=None, note=None):
    """Write this file's real numbers into the manifest.

    The point of this function is that nobody retypes a row count. A count typed
    by hand is a count that can be wrong, and a wrong one corrupts both the
    closing summary and the quota tracking, silently.
    """
    from datetime import datetime

    manifest_path = os.path.join(run_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        sys.exit("no manifest at %s -- run plan_run.py first" % manifest_path)
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)

    jobs = manifest["jobs"]
    if index < 0 or index >= len(jobs):
        sys.exit("job index %d out of range (0..%d)" % (index, len(jobs) - 1))
    job = jobs[index]

    job["status"] = status
    job["file"] = os.path.basename(path)
    job["rows"] = rows
    job["records"] = records
    job["note"] = note
    if status == "failed":
        job["attempts"] = job.get("attempts", 0) + 1
    job["updated_at"] = datetime.now().isoformat(timespec="seconds")

    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    detail = ""
    if rows is not None:
        detail = ": %s rows" % format(rows, ",")
        detail += ", %s records" % format(records, ",") if records is not None else ", records unknown"
    print("manifest: job %d -> %s%s" % (index, status, detail))
    if note:
        print("          %s" % note)


def profile(frame):
    cols = []
    total = len(frame)
    for name in frame.columns:
        series = frame[name]
        filled = int(series.notna().sum())
        sample = None
        if filled:
            sample = str(series.dropna().iloc[0])[:40]
        cols.append(
            {
                "name": str(name),
                "filled": filled,
                "fill_pct": round(100.0 * filled / total, 1) if total else 0.0,
                "sample": sample,
            }
        )
    return cols


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path")
    ap.add_argument("--json", action="store_true", help="emit machine-readable output")
    ap.add_argument("--record", metavar="RUN_DIR",
                    help="write the outcome straight into RUN_DIR/manifest.json")
    ap.add_argument("--job", type=int, help="job index to record against (required with --record)")
    args = ap.parse_args(argv)

    if args.record and args.job is None:
        sys.exit("--job is required with --record")

    def record(status, rows=None, records=None, note=None):
        if args.record:
            record_outcome(args.record, args.job, status, args.path, rows, records, note)

    if not os.path.exists(args.path):
        sys.exit("no such file: %s" % args.path)

    size = os.path.getsize(args.path)
    if size == 0:
        print("EMPTY: 0 bytes -- the download did not produce a file")
        record("failed", note="0 bytes: the download never produced a file")
        return 2
    if looks_like_html(args.path):
        print("NOT DATA: file starts like an HTML page (expired session or an error screen)")
        record("failed", note="HTML instead of a spreadsheet: session probably expired")
        return 2

    frame = read_table(args.path)
    cols = profile(frame)
    records, how = count_records(frame)
    truncated = records is not None and records >= RECORD_CAP

    if args.json:
        print(json.dumps({
            "path": args.path,
            "bytes": size,
            "rows": len(frame),
            "records": records,
            "record_basis": how,
            "truncated": truncated,
            "columns": cols,
        }, ensure_ascii=False, indent=2))
        if truncated:
            record("failed", len(frame), records, "truncated at the %d-record cap; split and redo" % RECORD_CAP)
            return 3
        if not len(frame):
            record("skipped", 0, 0, "sin datos para el periodo")
            return 2
        record("done", len(frame), records)
        return 0

    print("file    %s" % os.path.basename(args.path))
    print("bytes   %d" % size)
    print("rows    %d" % len(frame))
    if records is not None:
        print("records %d  (%s)" % (records, how))
        if len(frame) and records:
            print("        %.2f rows per record" % (len(frame) / records))
    else:
        print("records unknown, no usable Identificador or Item column")
    print("columns %d" % len(cols))
    for col in cols:
        print("  %-38s %5.1f%% filled  e.g. %s" % (col["name"][:38], col["fill_pct"], col["sample"]))
    if not len(frame):
        print("WARNING: zero data rows -- filters may have matched nothing")
        record("skipped", 0, 0, "sin datos para el periodo")
        return 2
    if truncated:
        print()
        print("TRUNCATED: %d records hits Softrade's %d-record cap." % (records, RECORD_CAP))
        print("           Softrade kept only the first %d records and said so only" % RECORD_CAP)
        print("           on screen. This file is INCOMPLETE. Split the query into")
        print("           shorter periods, or narrow it, and download again.")
        print("           run_state.py split RUN_DIR --job N")
        record("failed", len(frame), records, "truncated at the %d-record cap; split and redo" % RECORD_CAP)
        return 3
    if records is not None and records > RECORD_CAP * 0.9:
        print()
        print("NOTE: %d records is close to the %d cap. The next period may truncate." % (records, RECORD_CAP))
    record("done", len(frame), records)
    return 0


if __name__ == "__main__":
    sys.exit(main())
