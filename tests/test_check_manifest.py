import contextlib
import io
import json
import os
import shutil
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


def check_json(run_dir):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run_state.main(["check", run_dir, "--json"])
    return rc, json.loads(buf.getvalue())


def split(run_dir, job):
    try:
        return run_state.main(["split", run_dir, "--job", str(job)])
    except SystemExit as e:
        return e.code


class CheckManifest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

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

    def _job(self, **kw):
        j = {"country": "AR", "report": "import", "date_from": "2026-01",
             "date_to": "2026-03", "status": "pending", "attempts": 0}
        j.update(kw)
        return j

    def test_reversed_dates_fail(self):
        d = self._write("reversed", {"jobs": [self._job(date_from="2026-05", date_to="2026-02")]})
        self.assertEqual(check(d), 1)

    def test_impossible_date_fails(self):
        d = self._write("month13", {"jobs": [self._job(date_from="2026-13", date_to="2026-13")]})
        self.assertEqual(check(d), 1)
        d = self._write("feb30", {"jobs": [self._job(date_from="2026-02-30", date_to="2026-03-01")]})
        self.assertEqual(check(d), 1)

    def test_day_precision_same_month_passes(self):
        d = self._write("days", {"jobs": [self._job(date_from="2026-02-01", date_to="2026-02-28")]})
        self.assertEqual(check(d), 0)

    def test_span_over_twelve_months_fails(self):
        d = self._write("wide", {"jobs": [self._job(date_from="2025-01", date_to="2026-01")]})
        self.assertEqual(check(d), 1)
        d = self._write("twelve", {"jobs": [self._job(date_from="2025-02", date_to="2026-01")]})
        self.assertEqual(check(d), 0)

    def test_duplicate_jobs_fail(self):
        d = self._write("dup", {"jobs": [self._job(filters={"a": ["1"]}), self._job(filters={"a": ["1"]})]})
        self.assertEqual(check(d), 1)
        d = self._write("nodup", {"jobs": [self._job(filters={"a": ["1"]}), self._job(filters={"a": ["2"]})]})
        self.assertEqual(check(d), 0)

    def test_overlapping_jobs_fail(self):
        # Not a duplicate, but months 2026-03..2026-04 get downloaded twice.
        d = self._write("overlap", {"jobs": [
            self._job(date_from="2026-01", date_to="2026-04"),
            self._job(date_from="2026-03", date_to="2026-06")]})
        rc, out = check_json(d)
        self.assertEqual(rc, 1)
        self.assertTrue(any("solapa" in p for p in out["problems"]))

    def test_adjacent_or_differently_filtered_jobs_pass(self):
        d = self._write("adjacent", {"jobs": [
            self._job(date_from="2026-01", date_to="2026-03"),
            self._job(date_from="2026-04", date_to="2026-06")]})
        self.assertEqual(check(d), 0)
        d = self._write("half_months", {"jobs": [
            self._job(date_from="2026-02-01", date_to="2026-02-14"),
            self._job(date_from="2026-02-15", date_to="2026-02-28")]})
        self.assertEqual(check(d), 0)
        d = self._write("other_filters", {"jobs": [
            self._job(filters={"a": ["1"]}),
            self._job(filters={"a": ["2"]}, date_from="2026-02")]})
        self.assertEqual(check(d), 0)

    def test_pending_parent_with_children_fails(self):
        # What `reset` of a split parent used to leave behind.
        d = self._write("reset_parent", {"jobs": [self._job()]})
        self.assertEqual(split(d, 0), 0)
        path = os.path.join(d, "manifest.json")
        with open(path, encoding="utf-8") as fh:
            m = json.load(fh)
        m["jobs"][0]["status"] = "pending"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(m, fh)
        rc, out = check_json(d)
        self.assertEqual(rc, 1)
        self.assertTrue(any("job 0" in p and "split_from" in p for p in out["problems"]))
        # ...and the problem it reports has a CLI fix: `split` re-marks the
        # parent without appending a second set of children.
        n = len(m["jobs"])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(split(d, 0), 0)
        with open(path, encoding="utf-8") as fh:
            m = json.load(fh)
        self.assertEqual(m["jobs"][0]["status"], "split")
        self.assertEqual(len(m["jobs"]), n)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(check(d), 0)

    def test_split_without_children_fails(self):
        d = self._write("orphan_split", {"jobs": [self._job(status="split")]})
        self.assertEqual(check(d), 1)

    def test_split_via_command_passes(self):
        d = self._write("real_split", {"jobs": [self._job()]})
        self.assertEqual(split(d, 0), 0)
        self.assertEqual(check(d), 0)

    def test_non_dict_job_is_reported_not_crash(self):
        d = self._write("not_dict", {"jobs": [self._job(), "job suelto"]})
        self.assertEqual(check(d), 1)

    def test_non_integer_attempts_is_reported_not_crash(self):
        d = self._write("attempts", {"jobs": [self._job(attempts="dos")]})
        self.assertEqual(check(d), 1)

    def test_catalog_load_failure_fails_check(self):
        import _catalog
        saved = _catalog.CATALOG_PATH
        _catalog.CATALOG_PATH = os.path.join(self.tmp, "no-such-catalog.json")
        try:
            d = self._write("nocat", {"jobs": [self._job()]})
            rc, out = check_json(d)
        finally:
            _catalog.CATALOG_PATH = saved
        self.assertEqual(rc, 1)
        self.assertFalse(out["ok"])
        self.assertTrue(any("catalog.json" in p for p in out["problems"]))

    def test_check_json_output(self):
        d = self._write("json_ok", {"jobs": [self._job()]})
        rc, out = check_json(d)
        self.assertEqual(rc, 0)
        self.assertEqual((out["ok"], out["jobs"], out["problems"]), (True, 1, []))
        d = self._write("json_bad", {"jobs": [self._job(date_from="2026-13")]})
        rc, out = check_json(d)
        self.assertEqual(rc, 1)
        self.assertFalse(out["ok"])
        self.assertTrue(out["problems"])

    def _version_warnings(self, name, cv):
        d = self._write(name, {"catalog_version": cv, "jobs": [self._job()]})
        rc, out = check_json(d)
        self.assertEqual(rc, 0)
        return [w for w in out["warnings"] if "catalog_version" in w]

    def test_current_catalog_version_has_no_warning(self):
        import _catalog
        cv = _catalog.version(_catalog.load())
        self.assertEqual(self._version_warnings("cv_now", cv), [])

    def test_stale_catalog_version_warns(self):
        self.assertEqual(len(self._version_warnings("cv_old", "2000-01-01+deadbeef")), 1)

    def test_legacy_date_only_version_compares_against_captured(self):
        import _catalog
        captured = _catalog.load()["meta"]["captured"]
        self.assertEqual(self._version_warnings("cv_legacy", captured), [])
        self.assertEqual(len(self._version_warnings("cv_legacy_old", "2000-01-01")), 1)

    def test_split_deferred_date_exits_cleanly(self):
        d = self._write("latest_split", {
            "jobs": [{"country": "EC", "report": "cargasIngresos",
                      "date_from": "latest", "date_to": "latest",
                      "status": "pending", "attempts": 0}],
        })
        self.assertNotEqual(split(d, 0), 0)


if __name__ == "__main__":
    unittest.main()
