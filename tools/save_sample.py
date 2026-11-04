#!/usr/bin/env python3
"""Archive the most recent Softrade download as a documented sample.

Moves the newest matching file out of the browser's download directory into
ejemplos_queries/<COUNTRY>/<report>/ and writes an info.md next to it recording
the exact query that produced it, plus the column profile.

Nunca pisa nada en silencio: si la carpeta ya tiene un info.md (otra muestra del
mismo reporte), la nueva se documenta en info-2.md, info-3.md, ... Si ya existe
un archivo con el mismo nombre, se niega salvo --force, que lo reemplaza junto
con el info que lo documentaba.

Usage:
  python tools/save_sample.py --country AR --report importaciones_detalladas \
      --match detalle_ARimportDetalladas --ncm 8544 --period 07/2026 \
      [--note "sin filtro de empresa"] [--force]
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSPECT = os.path.join(ROOT, "skills", "softrade-batch", "scripts", "inspect_download.py")
DEST_ROOT = os.path.join(ROOT, "ejemplos_queries")


def newest(download_dir, match, max_age_s=900):
    hits = glob.glob(os.path.join(download_dir, "%s*.xlsx" % match))
    hits = [h for h in hits if time.time() - os.path.getmtime(h) < max_age_s]
    if not hits:
        return None
    return max(hits, key=os.path.getmtime)


def info_path(dest_dir, fname, force=False):
    """info.md para la primera muestra de la carpeta, info-N.md para las siguientes.
    Con force, reusa el info que ya documentaba ese mismo archivo, aunque haya
    huecos en la numeración (p. ej. un info.md borrado a mano)."""
    names = ["info.md"] + ["info-%d.md" % n for n in range(2, 1000)]
    if force:
        tag = "| Archivo | `%s` |" % fname
        for name in names:
            path = os.path.join(dest_dir, name)
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8", errors="replace") as fh:
                if tag in fh.read():
                    return path
    for name in names:
        path = os.path.join(dest_dir, name)
        if not os.path.exists(path):
            return path
    sys.exit("demasiados info-N.md en %s" % dest_dir)


def profile(path):
    out = subprocess.run(
        [sys.executable, INSPECT, path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return out.stdout.strip(), out.returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--country", required=True, help="two-letter code, e.g. AR")
    ap.add_argument("--report", required=True, help="folder name, e.g. importaciones_detalladas")
    ap.add_argument("--match", required=True, help="filename prefix Softrade used")
    ap.add_argument("--ncm", default=None, help="tariff filter used")
    ap.add_argument("--period", default=None, help="period used, e.g. 07/2026")
    ap.add_argument("--extra", default=None, help="any other filter used")
    ap.add_argument("--note", default=None, help="free-text observation")
    ap.add_argument("--downloads", default=os.path.expanduser("~/Downloads"))
    ap.add_argument("--force", action="store_true",
                    help="replace a sample with the same filename (and its info)")
    args = ap.parse_args()

    src = newest(args.downloads, args.match)
    if not src:
        sys.exit("no recent download matching %s* in %s" % (args.match, args.downloads))

    dest_dir = os.path.join(DEST_ROOT, args.country.upper(), args.report)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(src))
    if os.path.exists(dest) and not args.force:
        sys.exit("ya existe %s; no lo piso (usa --force para reemplazarlo)"
                 % os.path.relpath(dest, ROOT))
    info = info_path(dest_dir, os.path.basename(dest), args.force)
    shutil.move(src, dest)

    text, rc = profile(dest)
    verdict = {0: "completo", 2: "vacio o ilegible", 3: "TRUNCADO"}.get(rc, "rc=%d" % rc)

    lines = [
        "# %s / %s" % (args.country.upper(), args.report.replace("_", " ")),
        "",
        "Muestra bajada el %s." % time.strftime("%Y-%m-%d"),
        "",
        "## Consulta exacta",
        "",
        "| Filtro | Valor |",
        "|---|---|",
        "| Periodo | %s |" % (args.period or "por defecto, el ultimo mes cargado"),
    ]
    if args.ncm:
        lines.append("| Posicion arancelaria | %s |" % args.ncm)
    if args.extra:
        lines.append("| Otros | %s |" % args.extra)
    lines += [
        "| Archivo | `%s` |" % os.path.basename(dest),
        "| Estado | **%s** |" % verdict,
        "",
        "## Perfil de columnas",
        "",
        "```",
        text,
        "```",
    ]
    if args.note:
        lines += ["", "## Nota", "", args.note]

    with open(info, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print("guardado  %s" % os.path.relpath(dest, ROOT))
    print("info      %s" % os.path.relpath(info, ROOT))
    print("estado    %s" % verdict)
    first = [l for l in text.splitlines() if l.startswith(("rows", "records", "columns"))]
    for l in first:
        print("          %s" % l)


if __name__ == "__main__":
    main()
