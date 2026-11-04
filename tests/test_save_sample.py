import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

import _bootstrap

TOOLS = os.path.join(_bootstrap.ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
import save_sample  # noqa: E402

NAME = "detalle_ARimportDetalladas_20260801_101500.xlsx"


class SaveSample(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.downloads = os.path.join(tmp.name, "Downloads")
        self.dest_root = os.path.join(tmp.name, "ejemplos_queries")
        os.makedirs(self.downloads)
        self.dest_dir = os.path.join(self.dest_root, "AR", "importaciones_detalladas")
        patches = [
            mock.patch.object(save_sample, "DEST_ROOT", self.dest_root),
            mock.patch.object(save_sample, "ROOT", tmp.name),
            # inspect_download necesita pandas y un xlsx real; acá solo importa el archivado
            mock.patch.object(save_sample, "profile", lambda path: ("rows: 3", 0)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def download(self, name=NAME, body="nuevo"):
        path = os.path.join(self.downloads, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return path

    def run_main(self, *extra):
        argv = ["save_sample.py", "--country", "ar", "--report", "importaciones_detalladas",
                "--match", "detalle_ARimportDetalladas", "--downloads", self.downloads] + list(extra)
        out = io.StringIO()
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(out):
            save_sample.main()
        return out.getvalue()

    def read(self, name):
        with open(os.path.join(self.dest_dir, name), encoding="utf-8") as fh:
            return fh.read()

    def test_normal_save_moves_file_and_writes_info(self):
        src = self.download()
        out = self.run_main("--ncm", "8544", "--period", "07/2026", "--note", "sin filtro")
        self.assertFalse(os.path.exists(src))
        self.assertEqual(self.read(NAME), "nuevo")
        info = self.read("info.md")
        self.assertIn("| Posicion arancelaria | 8544 |", info)
        self.assertIn("| Periodo | 07/2026 |", info)
        self.assertIn("`%s`" % NAME, info)
        self.assertIn("**completo**", info)
        self.assertIn("sin filtro", info)
        self.assertIn("guardado", out)

    def test_no_recent_download_exits(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_main()
        self.assertIn("no recent download", str(cm.exception.code))

    def test_second_sample_keeps_previous_info(self):
        self.download()
        self.run_main("--ncm", "8544")
        other = NAME.replace("101500", "113000")
        self.download(other)
        self.run_main("--ncm", "8471")
        first, second = self.read("info.md"), self.read("info-2.md")
        self.assertIn("8544", first)
        self.assertIn("`%s`" % NAME, first)
        self.assertIn("8471", second)
        self.assertIn("`%s`" % other, second)

    def test_same_filename_refused_without_force(self):
        self.download(body="viejo")
        self.run_main("--ncm", "8544")
        src = self.download(body="nuevo")
        with self.assertRaises(SystemExit) as cm:
            self.run_main("--ncm", "8471")
        self.assertIn("--force", str(cm.exception.code))
        # nada se tocó: la descarga sigue en Downloads y la muestra vieja intacta
        self.assertTrue(os.path.exists(src))
        self.assertEqual(self.read(NAME), "viejo")
        self.assertIn("8544", self.read("info.md"))
        self.assertFalse(os.path.exists(os.path.join(self.dest_dir, "info-2.md")))

    def test_force_replaces_file_and_its_own_info(self):
        self.download(body="viejo")
        self.run_main("--ncm", "8544")
        other = NAME.replace("101500", "113000")
        self.download(other)
        self.run_main("--ncm", "8471")
        self.download(body="nuevo")
        self.run_main("--ncm", "9999", "--force")
        self.assertEqual(self.read(NAME), "nuevo")
        # se reescribe el info que documentaba ese archivo, no el de la otra muestra
        self.assertIn("9999", self.read("info.md"))
        self.assertIn("8471", self.read("info-2.md"))
        self.assertFalse(os.path.exists(os.path.join(self.dest_dir, "info-3.md")))

    def test_force_finds_info_past_a_gap(self):
        # info.md borrado a mano: el que documenta NAME es info-2.md
        other = NAME.replace("101500", "113000")
        self.download(other)
        self.run_main("--ncm", "8471")
        self.download(body="viejo")
        self.run_main("--ncm", "8544")
        os.remove(os.path.join(self.dest_dir, "info.md"))
        self.download(body="nuevo")
        self.run_main("--ncm", "9999", "--force")
        self.assertEqual(self.read(NAME), "nuevo")
        self.assertIn("9999", self.read("info-2.md"))
        self.assertIn("`%s`" % NAME, self.read("info-2.md"))
        # no queda un info.md nuevo duplicando la documentación de NAME
        self.assertFalse(os.path.exists(os.path.join(self.dest_dir, "info.md")))
        self.assertTrue(os.path.exists(os.path.join(self.dest_dir, other)))


if __name__ == "__main__":
    unittest.main()
