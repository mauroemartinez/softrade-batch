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

Re-running against an existing manifest adds only the jobs that are missing;
jobs already marked done are never touched.

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
from datetime import date

MANIFEST_NAME = "manifest.json"


def month_floor(value):
    """Parse YYYY-MM (or YYYY-MM-DD) into a (year, month) tuple."""
    parts = value.split("-")
    if len(parts) < 2:
        raise ValueError("expected YYYY-MM, got %r" % value)
    return int(parts[0]), int(parts[1])


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


def job_key(job):
    return (job["country"], job["report"], job["date_from"], job["date_to"])


def build_jobs(countries, reports, chunks):
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="run directory; manifest.json is written inside it")
    ap.add_argument("--country", action="append", required=True, help="repeatable country code, e.g. ar")
    ap.add_argument("--report", action="append", required=True, help="repeatable report id, e.g. imports_detailed")
    ap.add_argument("--from", dest="date_from", required=True, help="first month, YYYY-MM")
    ap.add_argument("--to", dest="date_to", required=True, help="last month, YYYY-MM")
    ap.add_argument("--max-months", type=int, default=12,
                    help="max months per job (Softrade refuses queries over 12; leave at 12 "
                         "and split later with run_state.py split, only if a query truncates)")
    ap.add_argument("--label", default=None, help="free-text label for this run")
    args = ap.parse_args(argv)

    chunks = split_range(month_floor(args.date_from), month_floor(args.date_to), args.max_months)
    fresh = build_jobs(args.country, args.report, chunks)

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, MANIFEST_NAME)

    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            manifest = json.load(fh)
        existing = {job_key(j) for j in manifest["jobs"]}
        added = [j for j in fresh if job_key(j) not in existing]
        manifest["jobs"].extend(added)
        verb = "extended"
        count = len(added)
    else:
        manifest = {
            "version": 1,
            "label": args.label,
            "created_at": date.today().isoformat(),
            "download_dir": os.path.abspath(os.path.join(args.out, "downloads")),
            "max_months": args.max_months,
            "jobs": fresh,
        }
        verb = "created"
        count = len(fresh)

    os.makedirs(manifest["download_dir"], exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    total = len(manifest["jobs"])
    pending = sum(1 for j in manifest["jobs"] if j["status"] == "pending")
    print("%s %s" % (verb, path))
    print("  jobs %s (+%d)  pending %d" % (total, count, pending))
    print("  downloads -> %s" % manifest["download_dir"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
