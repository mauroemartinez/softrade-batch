#!/usr/bin/env python3
"""Split corrida-catalogo/manifest.json into two disjoint sub-runs.

The coverage run is one manifest with 112 jobs. To run it on two Softrade
accounts in parallel (one driven by Claude, one by ChatGPT) each driver needs
its OWN manifest and OWN download dir, or the two processes race on the same
file and grab the same jobs.

This carves the 112 jobs by their `note` tag:

  claude  ->  Pass A  + B1 Detalladas + B2 Cargas   (new forms, most unknowns,
              highest-value targets: MX Cargas Totales, US Cargas Maritimas)
  chatgpt ->  B3 Export-side LatAm + B4 Asia/Africa + Pass C anonymous
              (standard import/export form, mechanical, volume-heavy)

The original manifest is left untouched as the 112-job reference. Nothing
here merges results back: copying the sub-runs' done/failed/skipped state into
the master manifest (and the markdown) is a manual step at the end.

Re-running refuses to overwrite a sub-manifest that already has progress (any
job not "pending"), because that would wipe the sub-run's state. Pass --force
only when that loss is intended.

Each sub-manifest carries the master's `preflight` caveats and a relative
`download_dir` ("downloads", i.e. its own split-<side>/downloads: run_state
resolves it against the sub-run's RUN_DIR, not the cwd), and is written
atomically. Relative on purpose: these manifests are versioned and resumed on
other machines, so no absolute path of this clone may end up in them.

Usage:  python tools/split_run.py [--force]
"""
import argparse
import json
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "corrida-catalogo", "manifest.json")

sys.path.insert(0, os.path.join(ROOT, "skills", "softrade-batch", "scripts"))
from plan_run import write_manifest  # noqa: E402  (atomic: temp file + os.replace)


def side_of(note):
    n = (note or "").lower()
    if "pass a" in n or re.search(r"\bf\d+\b", n) or "normativa" in n:
        return "claude"
    if "b1 detalladas" in n or "b2 cargas" in n:
        return "claude"
    return "chatgpt"  # B3, B4, Pass C


def _progress(path):
    """Number of jobs not in "pending" in an existing sub-manifest (0 if absent)."""
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as fh:
        existing = json.load(fh)
    return sum(1 for j in existing.get("jobs") or []
               if not isinstance(j, dict) or j.get("status") != "pending")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true",
                    help="overwrite sub-manifests even if they already have progress")
    args = ap.parse_args(argv)

    with open(SRC, encoding="utf-8") as fh:
        master = json.load(fh)

    buckets = {"claude": [], "chatgpt": []}
    for job in master["jobs"]:
        buckets[side_of(job.get("note"))].append(job)

    # Check both sides before writing either, so a refusal leaves nothing half done.
    if not args.force:
        busy = []
        for side in buckets:
            path = os.path.join(ROOT, "corrida-catalogo", "split-" + side, "manifest.json")
            n = _progress(path)
            if n:
                busy.append("%s (%d job(s) no pending)" % (os.path.relpath(path, ROOT), n))
        if busy:
            print("no sobrescribo sub-corridas con avance: %s.\n"
                  "Eso borraría su estado. Volcá los resultados al manifiesto maestro a mano,\n"
                  "o repetí con --force si de verdad querés descartarlos." % "; ".join(busy),
                  file=sys.stderr)
            return 1

    for side, jobs in buckets.items():
        out_dir = os.path.join(ROOT, "corrida-catalogo", "split-" + side)
        # Stored relative ("downloads"): run_state.download_dir() re-bases it
        # against this sub-run's RUN_DIR. An absolute path would leak this
        # clone's location into the versioned manifest.
        os.makedirs(os.path.join(out_dir, "downloads"), exist_ok=True)
        sub = {
            "version": 1,
            "label": "cobertura de columnas -- sub-run %s" % side,
            "created_at": master.get("created_at"),
            "download_dir": "downloads",
            "max_months": master.get("max_months", 1),
            "catalog_version": master.get("catalog_version"),
            "date_convention": master.get("date_convention"),
            # the caveats a driver relays to the user (`run_state.py status`)
            "preflight": list(master.get("preflight") or []),
            "parent": "corrida-catalogo/manifest.json",
            "jobs": jobs,
        }
        path = os.path.join(out_dir, "manifest.json")
        write_manifest(path, sub)
        done = sum(1 for j in jobs if j["status"] == "done")
        pend = sum(1 for j in jobs if j["status"] == "pending")
        print("%-8s %3d jobs  (%d done, %d pending)  -> %s"
              % (side, len(jobs), done, pend, os.path.relpath(path, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
