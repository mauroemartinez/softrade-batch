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


class SplitRange(unittest.TestCase):
    """Softrade refuses queries over 12 months; never emit an illegal job, and never
    split more than necessary (one period that fits = one consolidated Excel)."""

    def test_seven_months_is_one_job(self):
        c = plan_run.split_range((2026, 1), (2026, 7), 12)
        self.assertEqual([(x["date_from"], x["date_to"]) for x in c],
                         [("2026-01-01", "2026-07-31")])

    def test_twelve_is_one_and_thirteen_is_two(self):
        self.assertEqual(len(plan_run.split_range((2026, 1), (2026, 12), 12)), 1)
        self.assertEqual(len(plan_run.split_range((2025, 1), (2026, 1), 12)), 2)

    def test_month_ends(self):
        one = lambda y, m: plan_run.split_range((y, m), (y, m), 1)[0]["date_to"]
        self.assertEqual(one(2026, 2), "2026-02-28")
        self.assertEqual(one(2028, 2), "2028-02-29")   # leap year
        self.assertEqual(one(2026, 4), "2026-04-30")
        self.assertEqual(one(2026, 12), "2026-12-31")

    def test_bad_ranges_are_rejected(self):
        with self.assertRaises(ValueError):
            plan_run.split_range((2026, 7), (2026, 1), 12)
        with self.assertRaises(ValueError):
            plan_run.split_range((2026, 1), (2026, 7), 0)


class Filters(unittest.TestCase):
    """Filters are half the query: a manifest without them cannot be reproduced
    once the chat that confirmed the company is gone."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def plan(self, *extra):
        out = os.path.join(self.tmp, "run")
        status, code = run(["--out", out, "--country", "ar",
                            "--report", "imports_detailed",
                            "--from", "2026-01", "--to", "2026-07"] + list(extra))
        self.assertEqual(status, "ok", code)
        with open(os.path.join(out, "manifest.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def test_no_filters_is_an_empty_dict(self):
        self.assertEqual(self.plan()["jobs"][0]["filters"], {})

    def test_repeated_flag_accumulates(self):
        f = self.plan("--ncm", "8544", "--ncm", "8536")["jobs"][0]["filters"]
        self.assertEqual(f["ncm"], ["8544", "8536"])

    def test_other_company_same_period_is_a_new_job(self):
        self.plan("--importador", "EMPRESA A")
        self.assertEqual(len(self.plan("--importador", "EMPRESA B")["jobs"]), 2)

    def test_replanning_the_same_query_adds_nothing(self):
        self.plan("--importador", "EMPRESA A")
        self.assertEqual(len(self.plan("--importador", "EMPRESA A")["jobs"]), 1)


class CompanyFilterDirection(unittest.TestCase):
    """Each company filter names one side of one kind of report."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def plan(self, country, report, *extra):
        import contextlib, io as _io
        with contextlib.redirect_stderr(_io.StringIO()),                 contextlib.redirect_stdout(_io.StringIO()):
            return run(["--out", os.path.join(self.tmp, "r"), "--country", country,
                        "--report", report, "--from", "2026-01", "--to", "2026-07"]
                       + list(extra))

    def test_exportador_on_an_import_report_is_rejected(self):
        self.assertEqual(self.plan("ar", "import", "--exportador", "ACME SA"), ("exit", 2))

    def test_proveedor_on_an_export_report_is_rejected(self):
        self.assertEqual(self.plan("py", "export", "--proveedor", "X"), ("exit", 2))

    def test_comprador_on_an_export_report_that_names_buyers_is_fine(self):
        self.assertEqual(self.plan("ec", "export", "--comprador", "BUYER")[0], "ok")


class ExtendingOldManifests(unittest.TestCase):
    """Re-planning a run built before catalog.json existed must not duplicate it."""

    def test_raw_country_and_report_match_their_canonical_form(self):
        tmp = tempfile.mkdtemp()
        out = os.path.join(tmp, "r")
        os.makedirs(out)
        legacy = {"version": 1, "download_dir": os.path.join(out, "downloads"),
                  "jobs": [{"country": "ar", "report": "imports_detailed",
                            "date_from": "2026-01-01", "date_to": "2026-07-31",
                            "filters": {}, "status": "done", "file": "a.xlsx",
                            "rows": 1, "records": 1, "attempts": 0, "note": None,
                            "updated_at": None}]}
        with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(legacy, fh)
        import contextlib, io as _io
        with contextlib.redirect_stderr(_io.StringIO()),                 contextlib.redirect_stdout(_io.StringIO()):
            run(["--out", out, "--country", "ar", "--report", "importDetalladas",
                 "--from", "2026-01", "--to", "2026-07"])
        with open(os.path.join(out, "manifest.json"), encoding="utf-8") as fh:
            self.assertEqual(len(json.load(fh)["jobs"]), 1)


if __name__ == "__main__":
    unittest.main()
