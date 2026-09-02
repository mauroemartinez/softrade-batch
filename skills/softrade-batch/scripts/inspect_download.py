#!/usr/bin/env python3
"""Inspect a downloaded Softrade export and report its shape.

Three jobs:
  1. Confirm the file is real data and not an error page or an empty export.
  2. Detect silent truncation. Softrade caps a query at 30,000 customs RECORDS,
     not rows, and the export expands each record into one row per line item. A
     complete file can therefore hold far more than 30,000 rows, and a truncated
     one can look perfectly normal. Counting rows cannot tell the difference.
  3. Print the column layout so it can be compared against, or written into,
     references/columns.md -- without ever loading the rows into the chat.

Usage:
  python inspect_download.py FILE [--schema references/columns.md] [--json]

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
    args = ap.parse_args(argv)

    if not os.path.exists(args.path):
        sys.exit("no such file: %s" % args.path)

    size = os.path.getsize(args.path)
    if size == 0:
        print("EMPTY: 0 bytes -- the download did not produce a file")
        return 2
    if looks_like_html(args.path):
        print("NOT DATA: file starts like an HTML page (expired session or an error screen)")
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
            return 3
        return 0 if len(frame) else 2

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
        return 2
    if truncated:
        print()
        print("TRUNCATED: %d records hits Softrade's %d-record cap." % (records, RECORD_CAP))
        print("           Softrade kept only the first %d records and said so only" % RECORD_CAP)
        print("           on screen. This file is INCOMPLETE. Split the query into")
        print("           shorter periods, or narrow it, and download again.")
        return 3
    if records is not None and records > RECORD_CAP * 0.9:
        print()
        print("NOTE: %d records is close to the %d cap. The next period may truncate." % (records, RECORD_CAP))
    return 0


if __name__ == "__main__":
    sys.exit(main())
