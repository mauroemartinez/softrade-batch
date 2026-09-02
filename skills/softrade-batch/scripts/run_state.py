#!/usr/bin/env python3
"""Read and update a Softrade batch manifest.

Every command prints a few lines at most. That is the point: the agent driving a
long batch must never hold the whole manifest in context, only the next job.

  python run_state.py next   RUN_DIR
  python run_state.py status RUN_DIR
  python run_state.py quota  RUN_DIR [--quota 200000]
  python run_state.py done   RUN_DIR --job 7 --file arg_imports_2024.xlsx [--rows 15230]
  python run_state.py fail   RUN_DIR --job 7 --note "filtro de pais no cargo"
  python run_state.py skip   RUN_DIR --job 7 --note "sin datos para el periodo"
  python run_state.py reset  RUN_DIR --job 7
"""
import argparse
import json
import os
import sys
from datetime import datetime

MANIFEST_NAME = "manifest.json"
TERMINAL = {"done", "skipped"}

# Softrade accounts carry a monthly row allowance and the application displays
# consumption nowhere at all. The manifest is the only place it gets counted, so
# these thresholds exist to stop a run before it quietly eats the month.
DEFAULT_QUOTA = 200000
WARN_AT = 0.50
STOP_AT = 0.80


def load(run_dir):
    path = os.path.join(run_dir, MANIFEST_NAME)
    if not os.path.exists(path):
        sys.exit("no manifest at %s -- run plan_run.py first" % path)
    with open(path, encoding="utf-8") as fh:
        return path, json.load(fh)


def save(path, manifest):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def pick(manifest, index):
    jobs = manifest["jobs"]
    if index < 0 or index >= len(jobs):
        sys.exit("job index %d out of range (0..%d)" % (index, len(jobs) - 1))
    return jobs[index]


def cmd_next(manifest, _args):
    for i, job in enumerate(manifest["jobs"]):
        if job["status"] in ("pending", "failed"):
            print("job %d" % i)
            print("  country    %s" % job["country"])
            print("  report     %s" % job["report"])
            print("  date_from  %s" % job["date_from"])
            print("  date_to    %s" % job["date_to"])
            print("  status     %s (attempts %d)" % (job["status"], job["attempts"]))
            if job.get("note"):
                print("  last_note  %s" % job["note"])
            print("  save_to    %s" % manifest["download_dir"])
            return 0
    print("no pending jobs -- run complete")
    return 0


def cmd_quota(manifest, args):
    limit = args.quota or DEFAULT_QUOTA
    totals = month_totals(manifest)
    if not totals:
        print("nothing downloaded yet in this run")
        return 0
    print("rows downloaded, by calendar month (limit %s)" % format(limit, ","))
    for month in sorted(totals):
        used = totals[month]
        print("  %-10s %10s  %5.1f%%" % (month, format(used, ","), 100.0 * used / limit))
    line = quota_line(manifest, limit)
    if line:
        level, used, pct = line
        print()
        if level == "STOP":
            print("STOP: %.0f%% of this month's allowance is gone (%s rows)." % (pct * 100, format(used, ",")))
            print("      Do not start another tramo without asking the user first.")
        elif level == "WARN":
            print("WARN: %.0f%% of this month's allowance is gone (%s rows)." % (pct * 100, format(used, ",")))
            print("      Tell the user before continuing.")
    print()
    print("This run only. Downloads made outside this manifest are not counted,")
    print("and Softrade itself reports consumption nowhere.")
    return 0


def cmd_status(manifest, _args):
    counts = {}
    for job in manifest["jobs"]:
        counts[job["status"]] = counts.get(job["status"], 0) + 1
    total = len(manifest["jobs"])
    done = counts.get("done", 0)
    print("%s: %d/%d done" % (manifest.get("label") or "run", done, total))
    for status in sorted(counts):
        print("  %-8s %d" % (status, counts[status]))
    failed = [(i, j) for i, j in enumerate(manifest["jobs"]) if j["status"] == "failed"]
    for i, job in failed[:10]:
        print("  ! job %d %s %s %s..%s: %s" % (i, job["country"], job["report"], job["date_from"], job["date_to"], job.get("note")))
    return 0


def _stamp(job):
    job["updated_at"] = datetime.now().isoformat(timespec="seconds")


def month_totals(manifest):
    """Rows downloaded per calendar month, keyed YYYY-MM by download date."""
    totals = {}
    for job in manifest["jobs"]:
        if job["status"] != "done" or not job.get("rows"):
            continue
        stamp = job.get("updated_at") or ""
        month = stamp[:7] or "sin-fecha"
        totals[month] = totals.get(month, 0) + int(job["rows"])
    return totals


def quota_line(manifest, limit):
    """One line on this calendar month's consumption, or None if nothing spent."""
    this_month = datetime.now().strftime("%Y-%m")
    used = month_totals(manifest).get(this_month, 0)
    if not used:
        return None
    pct = used / float(limit)
    if pct >= STOP_AT:
        level = "STOP"
    elif pct >= WARN_AT:
        level = "WARN"
    else:
        level = "ok"
    return level, used, pct


def cmd_done(manifest, args):
    job = pick(manifest, args.job)
    if not args.file:
        sys.exit("--file is required: record the file that actually landed on disk")
    job["status"] = "done"
    job["file"] = args.file
    job["rows"] = args.rows
    job["note"] = args.note
    _stamp(job)
    print("job %d -> done (%s)" % (args.job, args.file))
    line = quota_line(manifest, args.quota or DEFAULT_QUOTA)
    if line:
        level, used, pct = line
        if level in ("WARN", "STOP"):
            print("%s: %s rows this calendar month, %.0f%% of the allowance." % (level, format(used, ","), pct * 100))
            if level == "STOP":
                print("      Stop and ask the user before the next tramo.")
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


def cmd_reset(manifest, args):
    job = pick(manifest, args.job)
    job["status"] = "pending"
    job["file"] = None
    job["note"] = args.note
    _stamp(job)
    print("job %d -> pending" % args.job)
    return 0


COMMANDS = {
    "next": (cmd_next, False),
    "status": (cmd_status, False),
    "quota": (cmd_quota, False),
    "done": (cmd_done, True),
    "fail": (cmd_fail, True),
    "skip": (cmd_skip, True),
    "reset": (cmd_reset, True),
}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=sorted(COMMANDS))
    ap.add_argument("run_dir")
    ap.add_argument("--job", type=int, help="job index from `next`")
    ap.add_argument("--file", help="filename that landed in download_dir")
    ap.add_argument("--rows", type=int, help="row count of the downloaded file")
    ap.add_argument("--note", help="free-text note")
    ap.add_argument("--quota", type=int, help="monthly row allowance (default %d)" % DEFAULT_QUOTA)
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
