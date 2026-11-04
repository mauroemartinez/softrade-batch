import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

import _bootstrap

TOOLS = os.path.join(_bootstrap.ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
import split_run  # noqa: E402


def job(note, status="pending"):
    return {"country": "AR", "report": "import", "date_from": "latest",
            "date_to": "latest", "status": status, "attempts": 0, "note": note}


class SplitRun(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        os.makedirs(os.path.join(self.root, "corrida-catalogo"))
        src = os.path.join(self.root, "corrida-catalogo", "manifest.json")
        with open(src, "w", encoding="utf-8") as fh:
            json.dump({"jobs": [job("Pass A"), job("B3 Export-side")]}, fh)
        self._saved = (split_run.ROOT, split_run.SRC)
        split_run.ROOT, split_run.SRC = self.root, src

    def tearDown(self):
        split_run.ROOT, split_run.SRC = self._saved

    def _sub(self, side):
        return os.path.join(self.root, "corrida-catalogo", "split-" + side, "manifest.json")

    def _run(self, argv):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return split_run.main(argv)

    def _mark_done(self, side):
        with open(self._sub(side), encoding="utf-8") as fh:
            sub = json.load(fh)
        sub["jobs"][0]["status"] = "done"
        with open(self._sub(side), "w", encoding="utf-8") as fh:
            json.dump(sub, fh)

    def _status(self, side):
        with open(self._sub(side), encoding="utf-8") as fh:
            return json.load(fh)["jobs"][0]["status"]

    def test_rerun_with_only_pending_jobs_is_allowed(self):
        self.assertEqual(self._run([]), 0)
        self.assertEqual(self._run([]), 0)

    def test_rerun_refuses_to_wipe_progress(self):
        self.assertEqual(self._run([]), 0)
        self._mark_done("claude")
        self.assertNotEqual(self._run([]), 0)
        self.assertEqual(self._status("claude"), "done")

    def test_force_overwrites_progress(self):
        self.assertEqual(self._run([]), 0)
        self._mark_done("claude")
        self.assertEqual(self._run(["--force"]), 0)
        self.assertEqual(self._status("claude"), "pending")


    def _load(self, side):
        with open(self._sub(side), encoding="utf-8") as fh:
            return json.load(fh)

    def test_download_dir_is_relative_and_resolves_to_the_sub_run(self):
        # The sub-manifests are versioned and meant to be resumed on another
        # machine: no absolute path of this clone may end up in them. The
        # relative "downloads" is resolved against RUN_DIR by run_state.
        import run_state
        self.assertEqual(self._run([]), 0)
        elsewhere = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, elsewhere, True)
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(elsewhere)
        for side in ("claude", "chatgpt"):
            self.assertEqual(self._load(side)["download_dir"], "downloads")
            want = os.path.join(self.root, "corrida-catalogo", "split-" + side, "downloads")
            self.assertTrue(os.path.isdir(want))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                run_state.main(["next", os.path.dirname(self._sub(side)), "--json"])
            got = json.loads(out.getvalue())["download_dir"]
            self.assertEqual(os.path.normcase(os.path.abspath(got)), os.path.normcase(want))

    def test_preflight_warnings_are_carried_over(self):
        with open(split_run.SRC, encoding="utf-8") as fh:
            master = json.load(fh)
        master["preflight"] = ["[VE/importaciones] base congelada"]
        with open(split_run.SRC, "w", encoding="utf-8") as fh:
            json.dump(master, fh)
        self.assertEqual(self._run([]), 0)
        for side in ("claude", "chatgpt"):
            self.assertEqual(self._load(side)["preflight"],
                             ["[VE/importaciones] base congelada"])

    def test_no_preflight_in_the_master_is_an_empty_list(self):
        self.assertEqual(self._run([]), 0)
        self.assertEqual(self._load("claude")["preflight"], [])

    def test_failed_write_keeps_the_previous_sub_manifest(self):
        from unittest import mock
        self.assertEqual(self._run([]), 0)
        self._mark_done("claude")
        with mock.patch.object(json, "dump", side_effect=RuntimeError("boom")), \
                self.assertRaises(RuntimeError):
            self._run(["--force"])
        self.assertEqual(self._status("claude"), "done")
        sub_dir = os.path.dirname(self._sub("claude"))
        self.assertEqual(sorted(os.listdir(sub_dir)), ["downloads", "manifest.json"])


if __name__ == "__main__":
    unittest.main()
