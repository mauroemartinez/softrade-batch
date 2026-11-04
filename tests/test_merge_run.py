import contextlib
import io
import json
import os
import tempfile
import unittest

import _bootstrap  # noqa: F401
import merge_run

COLS = ["Identificador", "Item", "Importador", "FOB"]


def rows_for(prefix, n, items=1):
    """n declarations of `items` line items each, ids unique per prefix."""
    return [["%s-%03d" % (prefix, d), str(i), "MI EMPRESA S.A.", str(10 * d + i)]
            for d in range(1, n + 1) for i in range(1, items + 1)]


def job(country, report, date_from, date_to, status="done", file=None, rows=None, **extra):
    j = {"country": country, "report": report, "date_from": date_from, "date_to": date_to,
         "filters": {}, "status": status, "file": file, "rows": rows, "records": None,
         "attempts": 0, "note": None, "updated_at": None}
    j.update(extra)
    return j


class MergeBase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name
        self.dl = os.path.join(self.dir, "downloads")
        os.makedirs(self.dl)
        self.jobs = []

    def add(self, country, report, date_from, date_to, data=None, cols=COLS, status="done", **extra):
        """Append a job; with `data`, write its xlsx/csv and record it as done."""
        name = None
        if data is not None:
            import pandas as pd
            name = "%s_%s_%s.xlsx" % (country, report, date_from)
            if extra.pop("csv", False):
                name = name[:-5] + ".csv"
                pd.DataFrame(data, columns=cols).to_csv(os.path.join(self.dl, name), index=False)
            else:
                pd.DataFrame(data, columns=cols).to_excel(os.path.join(self.dl, name), index=False)
        rows = extra.pop("rows", len(data) if data is not None else (0 if status == "skipped" else None))
        self.jobs.append(job(country, report, date_from, date_to, status=status, file=name,
                             rows=rows, **extra))
        return len(self.jobs) - 1

    def write_manifest(self):
        with open(os.path.join(self.dir, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump({"version": 1, "label": "test", "download_dir": "downloads",
                       "jobs": self.jobs}, fh, ensure_ascii=False, indent=2)

    def merge(self, *argv):
        self.write_manifest()
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                rc = merge_run.main([self.dir] + list(argv))
            except SystemExit as exc:
                rc = exc.code if isinstance(exc.code, int) else 1
                if not isinstance(exc.code, int):
                    err.write(str(exc.code))
        self.out = out.getvalue() + err.getvalue()
        return rc

    def sheets(self, name="consolidado.xlsx"):
        import pandas as pd
        return pd.read_excel(os.path.join(self.dir, name), sheet_name=None, dtype=str)


class Concatenates(MergeBase):
    def test_done_children_merged_and_split_parent_left_out(self):
        self.add("AR", "importDetalladas", "2026-01", "2026-03", status="split")
        for m in (1, 2, 3):
            self.add("AR", "importDetalladas", "2026-%02d" % m, "2026-%02d" % m,
                     rows_for("M%d" % m, 10, items=2), split_from=0)
        self.assertEqual(self.merge(), 0, self.out)
        sheets = self.sheets()
        self.assertEqual(list(sheets), ["AR_importDetalladas"])
        frame = sheets["AR_importDetalladas"]
        self.assertEqual(len(frame), 60)
        self.assertEqual(list(frame.columns), COLS + ["origen_job", "origen_periodo"])
        self.assertEqual(sorted(frame["origen_job"].unique()), ["1", "2", "3"])
        self.assertIn("2026-02..2026-02", set(frame["origen_periodo"]))
        # rows and operations, recounted from the merged data
        self.assertIn("60", self.out)
        self.assertIn("30", self.out)

    def test_a_parent_with_children_is_skipped_even_if_done(self):
        self.add("AR", "importDetalladas", "2026-01", "2026-02", rows_for("P", 5))
        self.add("AR", "importDetalladas", "2026-01", "2026-01", rows_for("A", 5), split_from=0)
        self.add("AR", "importDetalladas", "2026-02", "2026-02", rows_for("B", 5), split_from=0)
        self.assertEqual(self.merge(), 0, self.out)
        frame = self.sheets()["AR_importDetalladas"]
        self.assertEqual(sorted(frame["origen_job"].unique()), ["1", "2"])

    def test_one_sheet_per_country_and_report(self):
        self.add("AR", "importDetalladas", "2026-01", "2026-01", rows_for("A", 3))
        self.add("UY", "import", "2026-01", "2026-01", rows_for("U", 4), cols=["DUA", "Item", "X", "Y"])
        self.assertEqual(self.merge(), 0, self.out)
        sheets = self.sheets()
        self.assertEqual(sorted(sheets), ["AR_importDetalladas", "UY_import"])
        self.assertEqual(len(sheets["UY_import"]), 4)

    def test_csv_output_and_csv_inputs(self):
        self.add("AR", "importDetalladas", "2026-01", "2026-01", rows_for("A", 3), csv=True)
        self.add("AR", "importDetalladas", "2026-02", "2026-02", rows_for("B", 3))
        out = os.path.join(self.dir, "todo.csv")
        self.assertEqual(self.merge("--out", out), 0, self.out)
        import pandas as pd
        frame = pd.read_csv(out, dtype=str)
        self.assertEqual(len(frame), 6)
        self.assertIn("origen_job", frame.columns)

    def test_csv_refuses_more_than_one_country_or_report(self):
        self.add("AR", "importDetalladas", "2026-01", "2026-01", rows_for("A", 3))
        self.add("UY", "import", "2026-01", "2026-01", rows_for("U", 3))
        out = os.path.join(self.dir, "todo.csv")
        self.assertEqual(self.merge("--out", out), 1)
        self.assertFalse(os.path.exists(out))
        self.assertIn(".xlsx", self.out)


class Refuses(MergeBase):
    def test_pending_or_failed_jobs_block_without_allow_partial(self):
        self.add("AR", "importDetalladas", "2026-01", "2026-01", rows_for("A", 3))
        self.add("AR", "importDetalladas", "2026-02", "2026-02", status="pending")
        self.add("AR", "importDetalladas", "2026-03", "2026-03", status="failed")
        self.assertEqual(self.merge(), 1)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "consolidado.xlsx")))
        self.assertIn("job 1", self.out)
        self.assertIn("job 2", self.out)
        self.assertIn("--allow-partial", self.out)

    def test_allow_partial_merges_what_is_done(self):
        self.add("AR", "importDetalladas", "2026-01", "2026-01", rows_for("A", 3))
        self.add("AR", "importDetalladas", "2026-02", "2026-02", status="pending")
        rc = self.merge("--allow-partial")
        self.assertIn(rc, (0, 3), self.out)
        self.assertEqual(len(self.sheets()["AR_importDetalladas"]), 3)
        self.assertIn("PARCIAL", self.out)

    def test_columns_must_match_within_a_country_and_report(self):
        self.add("AR", "importDetalladas", "2026-01", "2026-01", rows_for("A", 3))
        self.add("AR", "importDetalladas", "2026-02", "2026-02", rows_for("B", 3),
                 cols=["Identificador", "Item", "Importador", "CIF"])
        self.assertEqual(self.merge(), 1)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "consolidado.xlsx")))
        self.assertIn("FOB", self.out)
        self.assertIn("CIF", self.out)
        self.assertIn("job 1", self.out)

    def test_column_order_alone_is_not_a_mismatch(self):
        self.add("AR", "importDetalladas", "2026-01", "2026-01", rows_for("A", 3))
        reordered = [[r[1], r[0], r[2], r[3]] for r in rows_for("B", 3)]
        self.add("AR", "importDetalladas", "2026-02", "2026-02", reordered,
                 cols=["Item", "Identificador", "Importador", "FOB"])
        self.assertEqual(self.merge(), 0, self.out)
        frame = self.sheets()["AR_importDetalladas"]
        self.assertEqual(list(frame.columns)[:4], COLS)
        self.assertEqual(frame.iloc[3]["Identificador"], "B-001")

    def test_missing_file_is_an_error(self):
        i = self.add("AR", "importDetalladas", "2026-01", "2026-01", rows_for("A", 3))
        os.remove(os.path.join(self.dl, self.jobs[i]["file"]))
        self.assertEqual(self.merge(), 1)
        self.assertIn("job 0", self.out)

    def test_a_file_only_in_the_cwd_or_run_dir_is_not_picked_up(self):
        # download_dir relative = relative to RUN_DIR, never to the cwd; and the
        # run dir itself is not a fallback either.
        i = self.add("AR", "importDetalladas", "2026-01", "2026-01", rows_for("A", 3))
        name = self.jobs[i]["file"]
        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        os.replace(os.path.join(self.dl, name), os.path.join(other.name, name))
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(other.name)
        self.assertEqual(self.merge(), 1, self.out)
        self.assertIn("no encuentro", self.out)
        os.replace(os.path.join(other.name, name), os.path.join(self.dir, name))
        self.assertEqual(self.merge(), 1, self.out)
        self.assertIn("no encuentro", self.out)

    def test_html_instead_of_a_spreadsheet_is_an_error(self):
        i = self.add("AR", "importDetalladas", "2026-01", "2026-01", rows_for("A", 3))
        with open(os.path.join(self.dl, self.jobs[i]["file"]), "w") as fh:
            fh.write("<html><body>Sesion expirada</body></html>")
        self.assertEqual(self.merge(), 1)
        self.assertIn("HTML", self.out)


class NativeTypes(MergeBase):
    def test_numbers_and_dates_stay_numbers_and_dates(self):
        import datetime
        import openpyxl
        cols = ["Identificador", "Item", "Fecha", "NCM", "FOB"]
        for m, day in ((1, 5), (2, 9)):
            data = [["A-%d" % m, 1, datetime.datetime(2026, m, day), "08544200", 13250.81],
                    ["B-%d" % m, 1, datetime.datetime(2026, m, day + 1), "08544200", 554.21]]
            self.add("AR", "importDetalladas", "2026-%02d" % m, "2026-%02d" % m, data, cols=cols)
        self.assertEqual(self.merge(), 0, self.out)
        ws = openpyxl.load_workbook(os.path.join(self.dir, "consolidado.xlsx"))["AR_importDetalladas"]
        header = [c.value for c in ws[1]]
        row = {h: c for h, c in zip(header, ws[2])}
        self.assertEqual(row["FOB"].data_type, "n")
        self.assertEqual(row["FOB"].value, 13250.81)
        self.assertEqual(row["Item"].data_type, "n")
        self.assertTrue(row["Fecha"].is_date, row["Fecha"].value)
        self.assertEqual(row["Fecha"].value.date(), datetime.date(2026, 1, 5))
        # text codes keep their leading zeros
        self.assertEqual(row["NCM"].data_type, "s")
        self.assertEqual(row["NCM"].value, "08544200")
        self.assertEqual(ws.max_row, 5)

    def test_overlap_dedup_still_works_on_typed_cells(self):
        import datetime
        cols = ["Identificador", "Item", "Fecha", "FOB"]
        shared = [["S-1", 1, datetime.datetime(2026, 1, 16), 10.5]]
        self.add("AR", "importDetalladas", "2026-01-01", "2026-01-20",
                 [["A-1", 1, datetime.datetime(2026, 1, 2), 1.25]] + shared, cols=cols)
        self.add("AR", "importDetalladas", "2026-01-15", "2026-01-31",
                 shared + [["B-1", 1, datetime.datetime(2026, 1, 30), 2.0]], cols=cols)
        self.assertEqual(self.merge(), 0, self.out)
        self.assertEqual(len(self.sheets()["AR_importDetalladas"]), 3)


class Duplicates(MergeBase):
    def test_overlapping_segments_lose_their_shared_rows(self):
        shared = rows_for("S", 4)
        self.add("AR", "importDetalladas", "2026-01-01", "2026-01-20", rows_for("A", 3) + shared)
        self.add("AR", "importDetalladas", "2026-01-15", "2026-01-31", shared + rows_for("B", 2))
        self.assertEqual(self.merge(), 0, self.out)
        frame = self.sheets()["AR_importDetalladas"]
        self.assertEqual(len(frame), 9)
        self.assertEqual(int((frame["Identificador"].str.startswith("S-")).sum()), 4)
        self.assertIn("duplicad", self.out)

    def test_identical_rows_in_non_overlapping_segments_are_kept(self):
        same = rows_for("S", 3)
        self.add("AR", "importDetalladas", "2026-01", "2026-01", same)
        self.add("AR", "importDetalladas", "2026-02", "2026-02", same)
        self.assertEqual(self.merge(), 0, self.out)
        self.assertEqual(len(self.sheets()["AR_importDetalladas"]), 6)

    def test_repeated_rows_inside_one_file_are_kept(self):
        data = rows_for("A", 3)
        self.add("AR", "importDetalladas", "2026-01", "2026-01", data + data[:1])
        self.assertEqual(self.merge(), 0, self.out)
        self.assertEqual(len(self.sheets()["AR_importDetalladas"]), 4)


class NearEmpty(MergeBase):
    def split_run(self, sizes):
        self.add("AR", "importDetalladas", "2026-01", "2026-%02d" % len(sizes), status="split")
        for m, n in enumerate(sizes, 1):
            if n:
                self.add("AR", "importDetalladas", "2026-%02d" % m, "2026-%02d" % m,
                         rows_for("M%d" % m, n), split_from=0)
            else:
                self.add("AR", "importDetalladas", "2026-%02d" % m, "2026-%02d" % m,
                         status="skipped", split_from=0, note="sin datos para el periodo")

    def test_balanced_segments_raise_no_flag(self):
        self.split_run([40, 35, 50, 45])
        self.assertEqual(self.merge(), 0, self.out)

    def test_an_empty_month_among_full_ones_is_flagged(self):
        self.split_run([40, 0, 50, 45])
        self.assertEqual(self.merge(), merge_run.EXIT_FLAGGED, self.out)
        self.assertIn("job 2", self.out)
        self.assertIn("vac", self.out.lower())
        # the merge is still written: the flag asks for verification, not a redo
        self.assertEqual(len(self.sheets()["AR_importDetalladas"]), 135)

    def test_a_suspiciously_small_month_is_flagged(self):
        self.split_run([40, 2, 50, 45])
        self.assertEqual(self.merge(), merge_run.EXIT_FLAGGED, self.out)
        self.assertIn("pocas filas", self.out)

    def test_mostly_empty_split_says_to_run_the_whole_period_once(self):
        self.split_run([0, 0, 3, 0, 0])
        self.assertEqual(self.merge(), merge_run.EXIT_FLAGGED, self.out)
        self.assertIn("mayoría", self.out)
        self.assertIn("2026-01..2026-05", self.out)

    def test_all_segments_empty_is_a_refusal_not_a_flagged_merge(self):
        self.split_run([0, 0])
        self.assertEqual(self.merge(), merge_run.EXIT_REFUSED, self.out)
        self.assertIn("mayoría", self.out)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "consolidado.xlsx")))
        self.assertEqual(self.merge("--json"), merge_run.EXIT_REFUSED)
        self.assertFalse(json.loads(self.out)["ok"])

    def test_manifest_rows_that_differ_from_the_file_are_flagged(self):
        self.add("AR", "importDetalladas", "2026-01", "2026-01", rows_for("A", 3), rows=99)
        self.assertEqual(self.merge(), merge_run.EXIT_FLAGGED, self.out)
        self.assertIn("99", self.out)

    def test_json_summary(self):
        self.split_run([40, 0, 50])
        self.assertEqual(self.merge("--json"), merge_run.EXIT_FLAGGED)
        payload = json.loads(self.out)
        self.assertEqual(payload["groups"][0]["rows"], 90)
        flagged = [j["index"] for j in payload["jobs"] if j["flags"]]
        self.assertEqual(flagged, [2])


if __name__ == "__main__":
    unittest.main()
