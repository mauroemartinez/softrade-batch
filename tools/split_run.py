#!/usr/bin/env python3
"""Split corrida-catalogo/manifest.json into two disjoint sub-runs.

The coverage run is one manifest with 112 jobs. To run it on two Softrade
accounts in parallel (one driven by Claude, one by ChatGPT) each driver needs
its OWN manifest and OWN download dir, or the two processes race on the same
file and grab the same jobs.

This carves the 112 jobs by their `note` tag:

  claude  ->  Pass A  + B1 Detalladas + B2 Cargas   (new forms, most traps,
              highest-value targets: MX Cargas Totales, US Cargas Maritimas)
  chatgpt ->  B3 Export-side LatAm + B4 Asia/Africa + Pass C anonymous
              (standard import/export form, mechanical, volume-heavy)

The original manifest is left untouched as the 112-job reference. Results from
both sub-runs are reflected back into the reference and the markdown at the end.

Usage:  python tools/split_run.py
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "corrida-catalogo", "manifest.json")


def side_of(note):
    n = (note or "").lower()
    if "pass a" in n or re.search(r"\bf\d+\b", n) or "normativa" in n:
        return "claude"
    if "b1 detalladas" in n or "b2 cargas" in n:
        return "claude"
    return "chatgpt"  # B3, B4, Pass C


def main():
    with open(SRC, encoding="utf-8") as fh:
        master = json.load(fh)

    buckets = {"claude": [], "chatgpt": []}
    for job in master["jobs"]:
        buckets[side_of(job.get("note"))].append(job)

    for side, jobs in buckets.items():
        out_dir = os.path.join(ROOT, "corrida-catalogo", "split-" + side)
        os.makedirs(os.path.join(out_dir, "downloads"), exist_ok=True)
        sub = {
            "version": 1,
            "label": "cobertura de columnas -- sub-run %s" % side,
            "created_at": master.get("created_at"),
            "download_dir": "downloads",
            "max_months": master.get("max_months", 1),
            "catalog_version": master.get("catalog_version"),
            "date_convention": master.get("date_convention"),
            "parent": "corrida-catalogo/manifest.json",
            "jobs": jobs,
        }
        path = os.path.join(out_dir, "manifest.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(sub, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        done = sum(1 for j in jobs if j["status"] == "done")
        pend = sum(1 for j in jobs if j["status"] == "pending")
        print("%-8s %3d jobs  (%d done, %d pending)  -> %s"
              % (side, len(jobs), done, pend, os.path.relpath(path, ROOT)))


if __name__ == "__main__":
    main()
