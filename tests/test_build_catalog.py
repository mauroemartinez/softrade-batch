"""tools/build_catalog.py: CLI (--help / --check / --out) and catalog_version.

The drift guard (`test_check_passes_on_committed_catalog`) fails when someone
edits build_catalog.py without regenerating references/catalog.json.
"""
import contextlib
import copy
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
import build_catalog  # noqa: E402
import _catalog  # noqa: E402


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = build_catalog.main(argv)
        except SystemExit as ex:  # argparse --help / usage errors
            code = ex.code
    return code, out.getvalue(), err.getvalue()


class BuildCatalogCli(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        # Any write that escapes --out lands here, never on the real catalog.json.
        saved = build_catalog.OUT
        self.addCleanup(setattr, build_catalog, "OUT", saved)
        build_catalog.OUT = os.path.join(self.tmp, "default", "catalog.json")

    def test_help_writes_nothing(self):
        code, out, _ = run(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("--check", out)
        self.assertFalse(os.path.exists(build_catalog.OUT))
        self.assertEqual(os.listdir(self.tmp), [])

    def test_no_args_writes_default_out(self):
        code, out, _ = run([])
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(build_catalog.OUT))
        self.assertIn("wrote", out)

    def test_out_writes_to_given_path(self):
        dest = os.path.join(self.tmp, "sub", "cat.json")
        code, _, _ = run(["--out", dest])
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(build_catalog.OUT))
        with open(dest, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), build_catalog.build())

    def test_check_passes_on_committed_catalog(self):
        # drift guard: build in memory and compare with the shipped catalog.json
        code, out, err = run(["--check", "--out", _catalog.CATALOG_PATH])
        self.assertEqual(code, 0, out + err)

    def test_check_detects_stale_file_and_writes_nothing(self):
        dest = os.path.join(self.tmp, "cat.json")
        stale = build_catalog.build()
        stale["countries"]["AR"]["reports"]["import"]["columns_measured"] = 99
        del stale["countries"]["UY"]
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(stale, fh)
        before = os.path.getmtime(dest)
        code, out, err = run(["--check", "--out", dest])
        self.assertEqual(code, 1)
        self.assertIn("AR/import", out + err)
        self.assertIn("UY", out + err)
        self.assertEqual(os.path.getmtime(dest), before)
        with open(dest, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["countries"]["AR"]["reports"]["import"]["columns_measured"], 99)

    def test_check_ignores_line_endings_and_formatting(self):
        dest = os.path.join(self.tmp, "cat.json")
        text = json.dumps(build_catalog.build(), ensure_ascii=False).replace("\n", "\r\n")
        with open(dest, "w", encoding="utf-8", newline="") as fh:
            fh.write(text + "\r\n")
        code, out, err = run(["--check", "--out", dest])
        self.assertEqual(code, 0, out + err)

    def test_check_missing_file_fails(self):
        code, _, _ = run(["--check", "--out", os.path.join(self.tmp, "nope.json")])
        self.assertEqual(code, 1)

    def test_check_valid_json_that_is_not_an_object_fails_cleanly(self):
        # null / [] / "x" parse fine but are not a catalog: short message, exit 1, no traceback
        for text in ("null", "[]", '"x"', "3"):
            with self.subTest(text=text):
                dest = os.path.join(self.tmp, "cat.json")
                with open(dest, "w", encoding="utf-8") as fh:
                    fh.write(text)
                code, out, err = run(["--check", "--out", dest])
                self.assertEqual(code, 1)
                self.assertIn("no puedo leer", err)

    def test_check_malformed_countries_reports_diff_without_crashing(self):
        dest = os.path.join(self.tmp, "cat.json")
        bad = build_catalog.build()
        bad["countries"]["AR"] = 5
        bad["countries"]["UY"]["reports"] = []
        bad["countries"]["CL"]["reports"]["import"] = None
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(bad, fh)
        code, out, err = run(["--check", "--out", dest])
        self.assertEqual(code, 1)
        self.assertIn("AR", out)
        self.assertIn("UY", out)
        self.assertIn("CL/import", out)
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump({"countries": [], "meta": None}, fh)
        code, out, err = run(["--check", "--out", dest])
        self.assertEqual(code, 1)
        self.assertIn("desactualizado", out)


class CatalogVersion(unittest.TestCase):
    def test_build_is_deterministic(self):
        self.assertEqual(build_catalog.build(), build_catalog.build())

    def test_version_is_in_meta_and_starts_with_latest_survey(self):
        cat = build_catalog.build()
        v = cat["meta"]["catalog_version"]
        dates = [cat["meta"]["captured"]] + [
            e["surveyed"] for c in cat["countries"].values()
            for e in c["reports"].values() if e.get("surveyed")]
        self.assertTrue(v.startswith(max(dates) + "+"), v)
        self.assertEqual(build_catalog.catalog_version(cat), v)

    def test_version_changes_when_an_entry_changes(self):
        cat = build_catalog.build()
        tweaked = copy.deepcopy(cat)
        tweaked["countries"]["BO"]["reports"]["export"]["note"] += " (corregido)"
        self.assertNotEqual(build_catalog.catalog_version(tweaked),
                            build_catalog.catalog_version(cat))
        # the tweak did not leak into the module's data
        self.assertEqual(build_catalog.build(), cat)

    def test_version_changes_when_a_new_survey_date_appears(self):
        cat = build_catalog.build()
        tweaked = copy.deepcopy(cat)
        tweaked["countries"]["AR"]["reports"]["import"]["surveyed"] = "2099-01-01"
        self.assertTrue(build_catalog.catalog_version(tweaked).startswith("2099-01-01+"))

    def test_catalog_helper_reads_version_with_captured_fallback(self):
        cat = build_catalog.build()
        self.assertEqual(_catalog.version(cat), cat["meta"]["catalog_version"])
        old = copy.deepcopy(cat)
        del old["meta"]["catalog_version"]
        self.assertEqual(_catalog.version(old), cat["meta"]["captured"])


if __name__ == "__main__":
    unittest.main()
