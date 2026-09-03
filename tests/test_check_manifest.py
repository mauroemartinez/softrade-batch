import json
import os
import tempfile
import unittest

import _bootstrap  # noqa: F401
import plan_run
import run_state


def check(run_dir):
    try:
        return run_state.main(["check", run_dir])
    except SystemExit as e:
        return e.code


class CheckManifest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _write(self, name, manifest):
        d = os.path.join(self.tmp, name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh)
        return d

    def test_fresh_plan_run_manifest_passes(self):
        d = os.path.join(self.tmp, "good")
        plan_run.main(["--out", d, "--country", "pe", "--report", "importaciones",
                       "--from", "2026-08", "--to", "2026-08",
                       "--importador", "X SAC"])
        self.assertEqual(check(d), 0)

    def test_non_canonical_report_id_fails(self):
        d = self._write("bad_report", {
            "jobs": [{"country": "AR", "report": "Importaciones Detalladas",
                      "date_from": "2026-08", "date_to": "2026-08", "status": "pending"}],
        })
        self.assertEqual(check(d), 1)

    def test_unknown_country_fails(self):
        d = self._write("bad_country", {
            "jobs": [{"country": "ZZ", "report": "import",
                      "date_from": "2026-08", "date_to": "2026-08", "status": "pending"}],
        })
        self.assertEqual(check(d), 1)

    def test_done_without_file_fails(self):
        d = self._write("bad_done", {
            "jobs": [{"country": "AR", "report": "import",
                      "date_from": "2026-08", "date_to": "2026-08",
                      "status": "done", "file": None, "rows": 10}],
        })
        self.assertEqual(check(d), 1)

    def test_date_placeholder_is_allowed(self):
        d = self._write("placeholder", {
            "jobs": [{"country": "EC", "report": "cargasIngresos",
                      "date_from": "latest", "date_to": "latest", "status": "pending"}],
        })
        self.assertEqual(check(d), 0)

    def test_country_report_mismatch_fails(self):
        d = self._write("mismatch", {
            "jobs": [{"country": "CL", "report": "importDetalladas",
                      "date_from": "2026-08", "date_to": "2026-08", "status": "pending"}],
        })
        self.assertEqual(check(d), 1)


if __name__ == "__main__":
    unittest.main()
