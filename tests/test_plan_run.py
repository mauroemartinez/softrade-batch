import json
import os
import shutil
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
        self.addCleanup(shutil.rmtree, self.tmp, True)

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
        import _catalog
        self.assertEqual(m["catalog_version"], _catalog.version(_catalog.load()))
        self.assertIn("+", m["catalog_version"])

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
        self.addCleanup(shutil.rmtree, self.tmp, True)

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


class OverlappingReplan(unittest.TestCase):
    """Re-planning a period that overlaps the planned one must add only the
    months that are missing, never a second job over the same months."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.out = os.path.join(self.tmp, "run")

    def plan(self, date_from, date_to, *extra):
        import contextlib, io as _io
        with contextlib.redirect_stderr(_io.StringIO()), \
                contextlib.redirect_stdout(_io.StringIO()):
            status, code = run(["--out", self.out, "--country", "ar",
                                "--report", "imports_detailed",
                                "--from", date_from, "--to", date_to] + list(extra))
        self.assertEqual(status, "ok", code)
        with open(os.path.join(self.out, "manifest.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def periods(self, m):
        return [(j["date_from"], j["date_to"]) for j in m["jobs"]]

    def check(self):
        import contextlib, io as _io
        import run_state
        with contextlib.redirect_stdout(_io.StringIO()):
            return run_state.main(["check", self.out])

    def test_earlier_overlapping_period_adds_only_the_missing_months(self):
        self.plan("2026-01", "2026-07")
        m = self.plan("2025-07", "2026-06")
        self.assertEqual(self.periods(m), [("2026-01-01", "2026-07-31"),
                                           ("2025-07-01", "2025-12-31")])
        self.assertEqual(self.check(), 0)

    def test_later_overlapping_period_adds_only_the_missing_months(self):
        self.plan("2026-01", "2026-07")
        m = self.plan("2026-03", "2026-09")
        self.assertEqual(self.periods(m)[1:], [("2026-08-01", "2026-09-30")])
        self.assertEqual(self.check(), 0)

    def test_a_split_run_is_not_replanned(self):
        import contextlib, io as _io
        import run_state
        self.plan("2026-01", "2026-07")
        with contextlib.redirect_stdout(_io.StringIO()):
            run_state.main(["split", self.out, "--job", "0"])
        m = self.plan("2026-01", "2026-09")
        self.assertEqual(self.periods(m)[8:], [("2026-08-01", "2026-09-30")])
        self.assertEqual(self.check(), 0)

    def test_a_half_month_job_leaves_the_rest_of_the_month_missing(self):
        # A job over 2025-02-01..15 used to mark all of February as planned:
        # 16..28 got no job and `check` saw nothing wrong.
        os.makedirs(self.out)
        with open(os.path.join(self.out, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump({"version": 1, "download_dir": os.path.join(self.out, "downloads"),
                       "jobs": [{"country": "AR", "report": "importDetalladas",
                                 "date_from": "2025-02-01", "date_to": "2025-02-15",
                                 "filters": {}, "status": "done", "file": "a.xlsx",
                                 "rows": 1, "records": 1, "attempts": 0,
                                 "note": None, "updated_at": None}]}, fh)
        m = self.plan("2025-01", "2025-03")
        self.assertEqual(self.periods(m)[1:], [("2025-01-01", "2025-01-31"),
                                               ("2025-02-16", "2025-03-31")])
        self.assertEqual(self.check(), 0)

    def test_a_job_ending_mid_month_is_completed_from_the_next_day(self):
        self.assertEqual(plan_run.missing_chunks(
            (2026, 1), (2026, 3), plan_run.covered_days(
                [{"country": "AR", "report": "importDetalladas",
                  "date_from": "2026-01", "date_to": "2026-02-10"}])[
                ("AR", "importDetalladas", ())], 12),
            [{"date_from": "2026-02-11", "date_to": "2026-03-31"}])

    def test_other_filters_are_another_dataset(self):
        self.plan("2026-01", "2026-07", "--importador", "EMPRESA A")
        m = self.plan("2026-03", "2026-09", "--importador", "EMPRESA B")
        self.assertEqual(self.periods(m)[1:], [("2026-03-01", "2026-09-30")])


class CompanyFilterDirection(unittest.TestCase):
    """Each company filter names one side of one kind of report."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

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
        self.addCleanup(shutil.rmtree, tmp, True)
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


class PeriodAndMaxMonths(unittest.TestCase):
    """The period and --max-months are checked whatever --skip-preflight says:
    a month 13 or a 24-month job is a query Softrade cannot run."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.out = os.path.join(self.tmp, "run")

    def plan(self, date_from, date_to, *extra):
        import contextlib, io as _io
        with contextlib.redirect_stderr(_io.StringIO()), \
                contextlib.redirect_stdout(_io.StringIO()):
            return run(["--out", self.out, "--country", "ar",
                        "--report", "importDetalladas",
                        "--from", date_from, "--to", date_to] + list(extra))

    def assertRejected(self, result):
        self.assertEqual(result, ("exit", 2))
        self.assertFalse(os.path.exists(os.path.join(self.out, "manifest.json")))

    def test_month_out_of_range_is_rejected_even_with_skip_preflight(self):
        self.assertRejected(self.plan("2026-13", "2027-02", "--skip-preflight"))
        self.assertRejected(self.plan("2026-00", "2026-02", "--skip-preflight"))

    def test_impossible_day_is_rejected_even_with_skip_preflight(self):
        self.assertRejected(self.plan("2026-02-30", "2026-03", "--skip-preflight"))

    def test_garbage_date_is_rejected(self):
        self.assertRejected(self.plan("enero", "2026-03", "--skip-preflight"))
        self.assertRejected(self.plan("2026-01", "2026-13"))

    def test_reversed_period_is_rejected_even_with_skip_preflight(self):
        self.assertRejected(self.plan("2026-05", "2026-01", "--skip-preflight"))

    def test_max_months_over_twelve_is_rejected(self):
        self.assertRejected(self.plan("2025-01", "2026-12", "--max-months", "24"))
        self.assertRejected(self.plan("2025-01", "2026-12", "--max-months", "13",
                                      "--skip-preflight"))

    def test_max_months_under_one_is_rejected(self):
        self.assertRejected(self.plan("2026-01", "2026-03", "--max-months", "0"))
        self.assertRejected(self.plan("2026-01", "2026-03", "--max-months", "-1",
                                      "--skip-preflight"))

    def test_max_months_bounds_are_accepted(self):
        self.assertEqual(self.plan("2026-01", "2026-12", "--max-months", "12")[0], "ok")
        self.assertEqual(self.plan("2025-01", "2025-02", "--max-months", "1")[0], "ok")

    def test_month_floor_validates_the_month(self):
        self.assertEqual(plan_run.month_floor("2026-02-28"), (2026, 2))
        for bad in ("2026-13", "2026-00", "2026-02-30", "2026", "2026-xx"):
            with self.assertRaises(ValueError, msg=bad):
                plan_run.month_floor(bad)


class AtomicManifestWrite(unittest.TestCase):
    """A write that dies halfway must leave the previous manifest.json intact."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.path = os.path.join(self.tmp, "manifest.json")
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"jobs": ["original"]}, fh)

    def test_failed_write_keeps_the_old_file_and_leaves_no_temp(self):
        from unittest import mock
        with mock.patch.object(plan_run.json, "dump", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                plan_run.write_manifest(self.path, {"jobs": ["new"]})
        with open(self.path, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), {"jobs": ["original"]})
        self.assertEqual(os.listdir(self.tmp), ["manifest.json"])

    def test_format_is_unchanged(self):
        # indent=2, accents kept, trailing newline: existing manifests diff clean
        plan_run.write_manifest(self.path, {"label": "importación", "jobs": []})
        with open(self.path, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), '{\n  "label": "importación",\n  "jobs": []\n}\n')
        self.assertEqual(os.listdir(self.tmp), ["manifest.json"])

    def test_replanning_a_manifest_with_relative_download_dir(self):
        # Old manifests (and the split sub-runs) store "downloads": that is the
        # run dir's downloads/, never a folder under whatever the cwd happens to be.
        import contextlib, io as _io
        out = os.path.join(self.tmp, "r")
        os.makedirs(out)
        with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump({"version": 1, "download_dir": "downloads", "jobs": []}, fh)
        cwd = os.getcwd()
        elsewhere = os.path.join(self.tmp, "cwd")
        os.makedirs(elsewhere)
        os.chdir(elsewhere)
        self.addCleanup(os.chdir, cwd)
        with contextlib.redirect_stderr(_io.StringIO()), \
                contextlib.redirect_stdout(_io.StringIO()):
            self.assertEqual(run(["--out", out, "--country", "ar", "--report",
                                  "importDetalladas", "--from", "2026-01",
                                  "--to", "2026-02"])[0], "ok")
        self.assertTrue(os.path.isdir(os.path.join(out, "downloads")))
        self.assertEqual(os.listdir(elsewhere), [])


if __name__ == "__main__":
    unittest.main()
