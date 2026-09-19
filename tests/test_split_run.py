import contextlib
import io
import json
import os
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


if __name__ == "__main__":
    unittest.main()
