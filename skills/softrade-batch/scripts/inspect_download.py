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
  corrupt file   -> failed  (a download cut short; download it again)

When the layout has no record key (no identifier and no Item column) the cap is
checked against ROWS instead. Rows are never fewer than records, so under the cap
the file is surely complete; at or over it, it may be truncated and is treated as
such. The output says when the count is by rows.

Exit codes: 0 file looks good, 2 file is empty or unreadable, 3 file is truncated.
"""
import argparse
import io
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

# What an error page carries and a data file does not: HTML tags and whole
# phrases only. A bare word such as "login" also matches an importer
# ("LOGINTER S.A.") in the first bytes of a CSV, which are data, not markup.
ERROR_MARKERS = ("<html", "<!doctype", "<head", "<body", "<form",
                 "sesion expirada", "sesión expirada", "session expired")

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
        text = io.StringIO(decode_text(path))
        for sep in rank_separators(text.getvalue()):
            text.seek(0)
            try:
                frame = pd.read_csv(text, dtype=str, sep=sep, engine="python")
            except Exception:
                continue
            if frame.shape[1] > 1:
                return frame
        text.seek(0)
        return pd.read_csv(text, dtype=str, engine="python")
    raise SystemExit("unsupported extension: %s" % ext)


def decode_text(path):
    """The file's text. UTF-8 first (a BOM is dropped so it cannot hide the first
    header), then cp1252, which is what Excel writes as "CSV" on a Spanish
    Windows. latin-1 decodes any byte, so it is the last resort.

    A UTF-16/UTF-32 BOM (Excel's "Texto Unicode") picks that codec: cp1252
    would decode those bytes without error into NUL-laden headers. NUL bytes
    without a BOM are not text Softrade or Excel writes, so they raise and the
    file is reported UNREADABLE instead of read as garbage."""
    import codecs

    with open(path, "rb") as fh:
        data = fh.read()
    # UTF-32 first: its little-endian BOM begins with UTF-16's.
    for boms, encoding in (((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE), "utf-32"),
                           ((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE), "utf-16")):
        if data.startswith(boms):
            return data.decode(encoding)
    if b"\x00" in data:
        raise ValueError("NUL bytes in a text file without a UTF-16/UTF-32 BOM")
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def rank_separators(text, sample_lines=200):
    """Candidate separators, best first: only those that split the header into 2+
    columns, ordered by how many lines of a sample have exactly the header's
    column count. A comma inside one header ("Valor FOB, USD") or inside decimals
    ("5,5") splits a line or two, never the whole file consistently. Ties keep
    the order `,` `;` tab `|`."""
    import csv
    import itertools

    # Only the head of the file, cut at a line end, so a big export is not
    # copied once per candidate.
    if len(text) > 65536:
        text = text[:text.rfind("\n", 0, 65536) + 1] or text[:65536]
    scored = []
    for order, sep in enumerate((",", ";", "\t", "|")):
        reader = csv.reader(io.StringIO(text), delimiter=sep)
        rows = [r for r in itertools.islice(reader, sample_lines) if r]
        if not rows or len(rows[0]) < 2:
            continue
        width = len(rows[0])
        consistent = sum(1 for r in rows if len(r) == width)
        scored.append((-consistent, order, sep))
    return [sep for _, _, sep in sorted(scored)]


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
            # Mexico's Ordinal is the pedimento with the item number glued on:
            # "06255386-0001". Counting those verbatim counts ROWS, not
            # declarations, which inflates the record count and silently defeats
            # truncation detection on the highest-volume country in the catalog.
            # Strip the suffix, but only when the column really looks like that,
            # so the other countries using Ordinal are left alone.
            stripped = values.astype(str).str.strip()
            compound = stripped.str.match(r"^\d+-\d+$")
            if compound.mean() > 0.5:
                base = stripped.str.split("-").str[0]
                return int(base.nunique()), "distinct %s, item suffix stripped" % ident
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
    by hand is a count that can be wrong, and a wrong one corrupts the closing
    summary silently.
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

    # Atomic (temp file + os.replace), shared with plan_run/run_state: a write
    # cut short must not leave half a manifest behind.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from plan_run import write_manifest
    except ImportError:
        sys.exit("cannot import plan_run.py -- keep the scripts in the same directory")
    write_manifest(manifest_path, manifest)

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

    try:
        frame = read_table(args.path)
    except SystemExit:
        raise
    except ImportError as exc:
        # A missing pandas/openpyxl/xlrd is the environment's fault, not the file's:
        # leave the manifest alone so the job is not marked failed and re-downloaded.
        sys.exit("missing dependency (%s: %s); install pandas, openpyxl and xlrd, then re-run"
                 % (type(exc).__name__, exc))
    except Exception as exc:
        # A download cut short leaves a zip without its central directory, and
        # pandas/openpyxl/zipfile each raise their own exception type for it.
        reason = "%s: %s" % (type(exc).__name__, str(exc)[:120])
        print("UNREADABLE: the file could not be parsed (%s)" % reason)
        print("            Probably a partial or corrupt download; download it again.")
        record("failed", note="unreadable spreadsheet (%s): download again" % reason)
        return 2
    cols = profile(frame)
    records, how = count_records(frame)
    # Without a record key, rows are the only count. Rows >= records, so this can
    # only over-flag, never let a truncated file through.
    by_rows = records is None
    counted = len(frame) if by_rows else records
    truncated = counted >= RECORD_CAP and len(frame) > 0
    basis = "rows (no record key column)" if by_rows else "records"
    trunc_note = ("truncated at the %d-record cap; split and redo" % RECORD_CAP if not by_rows
                  else "possibly truncated: %d rows >= %d cap, counted by rows (no record key); split and redo"
                  % (len(frame), RECORD_CAP))

    if args.json:
        print(json.dumps({
            "path": args.path,
            "bytes": size,
            "rows": len(frame),
            "records": records,
            "record_basis": how,
            "truncated": truncated,
            "truncation_basis": basis,
            "columns": cols,
        }, ensure_ascii=False, indent=2))
        if truncated:
            record("failed", len(frame), records, trunc_note)
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
        print("        truncation is checked by ROWS, not records")
    print("columns %d" % len(cols))
    for col in cols:
        print("  %-38s %5.1f%% filled  e.g. %s" % (col["name"][:38], col["fill_pct"], col["sample"]))
    if not len(frame):
        print("WARNING: zero data rows -- filters may have matched nothing")
        record("skipped", 0, 0, "sin datos para el periodo")
        return 2
    if truncated and by_rows:
        print()
        print("POSSIBLY TRUNCATED: %d rows reaches Softrade's %d-record cap, counted" % (len(frame), RECORD_CAP))
        print("           by ROWS because this layout has no record key. Records may be")
        print("           fewer than rows, but the file cannot be shown complete. Split")
        print("           the query into shorter periods and download again.")
        print("           run_state.py split RUN_DIR --job N")
        record("failed", len(frame), records, trunc_note)
        return 3
    if truncated:
        print()
        print("TRUNCATED: %d records hits Softrade's %d-record cap." % (records, RECORD_CAP))
        print("           Softrade kept only the first %d records and said so only" % RECORD_CAP)
        print("           on screen. This file is INCOMPLETE. Split the query into")
        print("           shorter periods, or narrow it, and download again.")
        print("           run_state.py split RUN_DIR --job N")
        record("failed", len(frame), records, trunc_note)
        return 3
    if counted > RECORD_CAP * 0.9:
        print()
        print("NOTE: %d %s is close to the %d cap. The next period may truncate."
              % (counted, "rows (counted by rows, no record key)" if by_rows else "records", RECORD_CAP))
    record("done", len(frame), records)
    return 0


if __name__ == "__main__":
    sys.exit(main())
