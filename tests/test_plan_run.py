import json
import os
import tempfile
import unittest

import _bootstrap  # noqa: F401
import plan_run


def run(args):
    """Call plan_run.main, returning ('ok', None) or ('exit', code)."""
    try:
        plan_run.main(args)
        return "ok", None
    except SystemExit as e:
        return "exit", e.code


class PlanRunValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _manifest(self, sub="run"):
        with open(os.path.join(self.tmp, sub, "manifest.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def test_three_year_range_still_splits_into_three_legal_jobs(self):
        status, _ = run([
            "--out", os.path.join(self.tmp, "run"),
            "--country", "ar", "--report", "imports_detailed",
            "--from", "2023-01", "--to", "2025-12",
            "--importador", "NOMBRE EXACTO S.A.",
        ])
        self.assertEqual(status, "ok")
        m = self._manifest()
        self.assertEqual(len(m["jobs"]), 3)
        for j in m["jobs"]:
            y0 = int(j["date_from"][:4])
            y1 = int(j["date_to"][:4])
            self.assertEqual(y0, y1)  # <= 12 months
            self.assertEqual(j["report"], "importDetalladas")  # canonicalised
            self.assertEqual(j["filters"]["importador"], ["NOMBRE EXACTO S.A."])
        self.assertEqual(m["catalog_version"], "2026-09-02")

    def test_report_a_country_does_not_offer_is_rejected(self):
        status, code = run([
            "--out", os.path.join(self.tmp, "bad"),
            "--country", "cl", "--report", "imports_detailed",
            "--from", "2025-01", "--to", "2025-06",
        ])
        self.assertEqual(status, "exit")
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "bad", "manifest.json")))

    def test_by_company_on_anonymous_export_is_rejected(self):
        status, code = run([
            "--out", os.path.join(self.tmp, "bad2"),
            "--country", "ar", "--report", "exportaciones",
            "--from", "2026-01", "--to", "2026-06",
            "--exportador", "X S.A.",
        ])
        self.assertEqual(status, "exit")
        self.assertEqual(code, 2)

    def test_proveedor_filter_needs_a_counterparty_column(self):
        status, code = run([
            "--out", os.path.join(self.tmp, "bad3"),
            "--country", "ar", "--report", "importDetalladas",  # AR has no Proveedor
            "--from", "2026-01", "--to", "2026-06",
            "--proveedor", "ACME GMBH",
        ])
        self.assertEqual(status, "exit")
        self.assertEqual(code, 2)

    def test_frozen_base_with_old_period_warns_but_still_plans(self):
        status, _ = run([
            "--out", os.path.join(self.tmp, "warn"),
            "--country", "ve", "--report", "importaciones",
            "--from", "2023-01", "--to", "2023-12",
        ])
        self.assertEqual(status, "ok")
        m = self._manifest("warn")
        self.assertEqual(len(m["jobs"]), 1)
        # the caveat is persisted so a resumed run can relay it
        self.assertTrue(any("congelada" in w for w in m["preflight"]))

    def test_skip_preflight_bypasses_validation(self):
        status, _ = run([
            "--out", os.path.join(self.tmp, "skip"),
            "--country", "cl", "--report", "importDetalladas",
            "--from", "2025-01", "--to", "2025-06",
            "--skip-preflight",
        ])
        self.assertEqual(status, "ok")


if __name__ == "__main__":
    unittest.main()
