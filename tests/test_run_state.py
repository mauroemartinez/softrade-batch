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


class RunStateBase(unittest.TestCase):
    """A seven-month importDetalladas run for one company, split into months."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            plan_run.main([
                "--out", self.dir, "--country", "ar", "--report", "imports_detailed",
                "--from", "2026-01", "--to", "2026-07",
                "--importador", "MI EMPRESA S.A.", "--ncm", "854442",
            ])

    def rs(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = run_state.main([argv[0], self.dir] + list(argv[1:]))
        self.out = buf.getvalue()
        return rc

    def manifest(self):
        with open(os.path.join(self.dir, "manifest.json"), encoding="utf-8") as fh:
            return json.load(fh)


class Split(RunStateBase):
    def test_parent_is_marked_and_children_are_appended(self):
        # Indices the agent already holds must keep pointing at the same job.
        self.rs("split", "--job", "0")
        jobs = self.manifest()["jobs"]
        self.assertEqual(jobs[0]["status"], "split")
        self.assertEqual(len(jobs), 8)
        self.assertEqual([j["date_from"][:7] for j in jobs[1:]],
                         ["2026-%02d" % m for m in range(1, 8)])
        self.assertTrue(all(j["status"] == "pending" for j in jobs[1:]))

    def test_children_inherit_the_filters(self):
        # Splitting a period must never silently widen the query.
        self.rs("split", "--job", "0")
        for job in self.manifest()["jobs"][1:]:
            self.assertEqual(job["filters"]["importador"], ["MI EMPRESA S.A."])
            self.assertEqual(job["filters"]["ncm"], ["854442"])

    def test_a_single_month_cannot_be_split(self):
        # Period splitting is exhausted: the agent must narrow the query instead.
        self.rs("split", "--job", "0")
        with self.assertRaises(SystemExit):
            self.rs("split", "--job", "1")

    def test_a_done_job_cannot_be_split(self):
        self.rs("done", "--job", "0", "--file", "a.xlsx", "--rows", "5")
        with self.assertRaises(SystemExit):
            self.rs("split", "--job", "0")

    def test_a_split_parent_cannot_be_split_again(self):
        # A second split appended a second set of pending children with the
        # same months, and `next` handed out every period twice.
        self.rs("split", "--job", "0")
        with self.assertRaises(SystemExit) as cm:
            self.rs("split", "--job", "0")
        self.assertNotIn(cm.exception.code, (0, None))
        self.assertEqual(len(self.manifest()["jobs"]), 8)


class ResetSplitParent(RunStateBase):
    # Resetting a split parent left it pending next to its pending children:
    # the same period came back from `next` twice.

    def setUp(self):
        super().setUp()
        self.rs("split", "--job", "0")          # jobs 1..7 pending

    def test_reset_of_a_split_parent_is_refused(self):
        with self.assertRaises(SystemExit) as cm:
            self.rs("reset", "--job", "0")
        self.assertNotIn(cm.exception.code, (0, None))
        jobs = self.manifest()["jobs"]
        self.assertEqual(jobs[0]["status"], "split")
        self.assertEqual(len(jobs), 8)

    def _orphan_pending_parent(self, status="pending"):
        # The state the old `reset` left behind: parent pending next to its
        # pending children. Written by hand because `reset` now refuses it.
        path = os.path.join(self.dir, "manifest.json")
        m = self.manifest()
        m["jobs"][0]["status"] = status
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(m, fh)

    def test_next_never_offers_a_parent_with_children(self):
        self._orphan_pending_parent()
        self.rs("next")
        self.assertEqual(self.out.splitlines()[0], "job 1")
        self.rs("next", "--json")
        self.assertEqual(json.loads(self.out)["index"], 1)

    def test_next_skips_a_failed_parent_with_children(self):
        self._orphan_pending_parent("failed")
        for i in range(1, 8):
            self.rs("skip", "--job", str(i), "--note", "sin datos")
        self.rs("next")
        self.assertIn("no pending", self.out)

    def test_split_repairs_a_pending_parent_without_new_children(self):
        self._orphan_pending_parent()
        self.assertEqual(self.rs("split", "--job", "0"), 0)
        jobs = self.manifest()["jobs"]
        self.assertEqual(jobs[0]["status"], "split")
        self.assertEqual(len(jobs), 8)
        self.assertIn("repaired", self.out)

    def test_a_done_parent_with_children_is_not_split(self):
        self._orphan_pending_parent("done")
        with self.assertRaises(SystemExit) as cm:
            self.rs("split", "--job", "0")
        self.assertIn("skip", str(cm.exception.code))
        self.assertEqual(len(self.manifest()["jobs"]), 8)

    def test_a_child_can_still_be_reset(self):
        self.rs("done", "--job", "1", "--file", "a.xlsx", "--rows", "3")
        self.assertEqual(self.rs("reset", "--job", "1"), 0)
        self.assertEqual(self.manifest()["jobs"][1]["status"], "pending")


class NextOrdering(RunStateBase):
    # SKILL.md promises failed jobs come back only once nothing is pending.
    # Otherwise an expired session retries the same broken job forever.

    def setUp(self):
        super().setUp()
        self.rs("split", "--job", "0")          # jobs 1..7 pending

    def offered(self):
        self.rs("next")
        head = self.out.splitlines()[0]
        return None if "no pending" in head else int(head.split()[1])

    def test_pending_comes_before_failed(self):
        self.rs("fail", "--job", "1", "--note", "sesion vencida")
        self.assertEqual(self.offered(), 2)

    def test_failed_is_offered_once_nothing_is_pending(self):
        self.rs("fail", "--job", "1", "--note", "x")
        for i in range(2, 8):
            self.rs("skip", "--job", str(i), "--note", "sin datos")
        self.assertEqual(self.offered(), 1)
        self.assertIn("RETRY", self.out)

    def test_the_split_parent_is_never_offered(self):
        for i in range(1, 8):
            self.rs("skip", "--job", str(i), "--note", "sin datos")
        self.assertIsNone(self.offered())

    def test_next_prints_the_filters(self):
        # A resumed chat has only this output to rebuild the query from.
        self.offered()
        self.assertIn("MI EMPRESA S.A.", self.out)
        self.assertIn("854442", self.out)

    def test_json_next_matches_text_next(self):
        self.rs("fail", "--job", "1", "--note", "x")
        self.rs("next", "--json")
        self.assertEqual(json.loads(self.out)["index"], 2)


class Totals(RunStateBase):
    # Rows and customs operations are different numbers; 17 rows can be 2 ops.

    def test_rows_and_records_are_counted_separately(self):
        self.rs("done", "--job", "0", "--file", "a.xlsx", "--rows", "17", "--records", "2")
        self.assertEqual(run_state.run_totals(self.manifest()), (17, 2, 0))

    def test_a_done_job_without_counts_is_flagged_not_dropped(self):
        self.rs("done", "--job", "0", "--file", "a.xlsx")
        self.assertEqual(run_state.run_totals(self.manifest())[2], 1)
        self.assertIn("WARNING", self.out)

    def test_status_reports_both_numbers(self):
        self.rs("done", "--job", "0", "--file", "a.xlsx", "--rows", "17", "--records", "2")
        self.rs("status")
        self.assertIn("rows     17", self.out)
        self.assertIn("records  2", self.out)

    def test_reset_clears_the_counts(self):
        self.rs("done", "--job", "0", "--file", "a.xlsx", "--rows", "17", "--records", "2")
        self.rs("reset", "--job", "0")
        job = self.manifest()["jobs"][0]
        self.assertEqual((job["status"], job["rows"], job["records"]), ("pending", None, None))


class StatusJson(RunStateBase):
    # What a resumed chat reads for the closing summary: its shape is a contract.

    def setUp(self):
        super().setUp()
        self.rs("split", "--job", "0")          # jobs 1..7 pending
        self.rs("done", "--job", "1", "--file", "a.xlsx", "--rows", "17", "--records", "2")
        self.rs("done", "--job", "2", "--file", "b.xlsx", "--rows", "4")
        self.rs("fail", "--job", "3", "--note", "sesion vencida")
        self.rs("skip", "--job", "4", "--note", "sin datos")

    def status(self):
        self.assertEqual(self.rs("status", "--json"), 0)
        return json.loads(self.out)

    def test_counts_and_totals(self):
        st = self.status()
        self.assertEqual(st["total"], 8)
        self.assertEqual(st["counts"], {"split": 1, "done": 2, "failed": 1,
                                        "skipped": 1, "pending": 3})
        self.assertEqual((st["rows"], st["records"]), (21, 2))
        self.assertEqual(st["files_missing_record_count"], 1)
        self.assertEqual(st["rows_per_record"], 10.5)
        self.assertIsNone(st["label"])
        self.assertEqual(st["catalog_version"], self.manifest()["catalog_version"])
        self.assertEqual(st["preflight"], self.manifest()["preflight"])

    def test_failed_jobs_are_listed(self):
        failed = self.status()["failed"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["index"], 3)
        self.assertEqual(failed[0]["note"], "sesion vencida")
        self.assertEqual(failed[0]["country"], "AR")
        self.assertEqual(failed[0]["date_from"], "2026-03-01")

    def test_rows_per_record_is_null_without_records(self):
        self.rs("reset", "--job", "1")
        self.assertIsNone(self.status()["rows_per_record"])

    def test_status_does_not_write(self):
        before = self.manifest()
        self.status()
        self.assertEqual(self.manifest(), before)


class ErrorBranches(RunStateBase):
    # The SystemExit messages the agent sees when it gets an index or a flag
    # wrong. None of them may touch the manifest.

    def assertRefused(self, *argv, says):
        before = self.manifest()
        with self.assertRaises(SystemExit) as cm:
            self.rs(*argv)
        self.assertIn(says, str(cm.exception.code))
        self.assertEqual(self.manifest(), before)

    def test_job_index_out_of_range(self):
        for verb in ("done", "fail", "skip", "split", "reset"):
            self.assertRefused(verb, "--job", "9", "--file", "a.xlsx", says="out of range")
        self.assertRefused("fail", "--job", "-1", says="out of range")

    def test_job_is_required_for_writing_commands(self):
        for verb in ("done", "fail", "skip", "split", "reset"):
            self.assertRefused(verb, says="--job is required")

    def test_done_needs_the_file(self):
        self.assertRefused("done", "--job", "0", "--rows", "3", says="--file is required")

    def test_split_of_a_skipped_one_month_job_is_refused(self):
        self.rs("split", "--job", "0")
        self.rs("skip", "--job", "1", "--note", "sin datos")
        self.assertRefused("split", "--job", "1", says="single month")

    def test_split_wider_max_months_than_the_job_is_refused(self):
        self.assertRefused("split", "--job", "0", "--max-months", "7", says="<= --max-months")

    def test_split_with_an_impossible_date_is_a_clear_error(self):
        # month_floor rejects 2025-02-30; split must say so, not traceback.
        m = self.manifest()
        m["jobs"][0]["date_to"] = "2025-02-30"
        with open(os.path.join(self.dir, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(m, fh, indent=2)
        self.assertRefused("split", "--job", "0", "--max-months", "1", says="invalid date")

    def test_missing_manifest(self):
        empty = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, empty, True)
        for verb in ("next", "status", "check"):
            with self.assertRaises(SystemExit) as cm:
                run_state.main([verb, empty])
            self.assertIn("no manifest", str(cm.exception.code))
        self.assertEqual(os.listdir(empty), [])

    def test_corrupt_manifest_is_a_clear_error(self):
        with open(os.path.join(self.dir, "manifest.json"), "w", encoding="utf-8") as fh:
            fh.write('{"jobs": [')
        with self.assertRaises(SystemExit) as cm:
            self.rs("status")
        self.assertIn("not valid JSON", str(cm.exception.code))

    def test_fail_counts_attempts(self):
        self.rs("fail", "--job", "0", "--note", "x")
        self.rs("fail", "--job", "0", "--note", "y")
        job = self.manifest()["jobs"][0]
        self.assertEqual((job["status"], job["attempts"], job["note"]), ("failed", 2, "y"))


class RelativeDownloadDir(RunStateBase):
    # split_run's sub-manifests (and the coverage master) store "downloads":
    # `next` must point at RUN_DIR/downloads, not at the agent's cwd.

    def setUp(self):
        super().setUp()
        path = os.path.join(self.dir, "manifest.json")
        m = self.manifest()
        m["download_dir"] = "downloads"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(m, fh)

    def test_next_rebases_it_on_the_run_dir(self):
        want = os.path.join(os.path.abspath(self.dir), "downloads")
        self.rs("next", "--json")
        self.assertEqual(json.loads(self.out)["download_dir"], want)
        self.rs("next")
        self.assertIn("save_to    %s" % want, self.out)

    def test_the_stored_value_is_left_alone(self):
        self.rs("fail", "--job", "0", "--note", "x")
        self.assertEqual(self.manifest()["download_dir"], "downloads")


class AtomicSave(RunStateBase):
    # Both writers of an existing manifest: a crash mid-write must not leave a
    # truncated manifest.json behind.

    def _boom(self):
        from unittest import mock
        return mock.patch.object(json, "dump", side_effect=RuntimeError("boom"))

    def test_run_state_save(self):
        before = self.manifest()
        with self._boom(), self.assertRaises(RuntimeError):
            self.rs("fail", "--job", "0", "--note", "x")
        self.assertEqual(self.manifest(), before)
        self.assertNotIn(".tmp", " ".join(os.listdir(self.dir)))

    def test_inspect_download_record(self):
        import inspect_download
        before = self.manifest()
        with self._boom(), self.assertRaises(RuntimeError), \
                contextlib.redirect_stdout(io.StringIO()):
            inspect_download.record_outcome(self.dir, 0, "done", "x.xlsx", rows=3, records=1)
        self.assertEqual(self.manifest(), before)
        self.assertNotIn(".tmp", " ".join(os.listdir(self.dir)))
        with contextlib.redirect_stdout(io.StringIO()):
            inspect_download.record_outcome(self.dir, 0, "done", "x.xlsx", rows=3, records=1)
        self.assertEqual(self.manifest()["jobs"][0]["rows"], 3)


if __name__ == "__main__":
    unittest.main()
