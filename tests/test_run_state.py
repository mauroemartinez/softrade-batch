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


if __name__ == "__main__":
    unittest.main()
