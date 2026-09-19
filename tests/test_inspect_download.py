import os
import tempfile
import unittest
from unittest import mock

import _bootstrap  # noqa: F401
import inspect_download


def write_xlsx(path, rows, header=("Identificador", "Item", "Valor")):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(list(header))
    for r in rows:
        ws.append(list(r))
    wb.save(path)


class InspectDownload(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def path(self, name="f.xlsx"):
        return os.path.join(self.tmp, name)

    def test_counts_records_not_rows(self):
        # 4 declarations, 3 line items each -> 12 rows, 4 records
        rows = []
        for d in range(4):
            for item in range(1, 4):
                rows.append(("DECL%03d" % d, item, 10))
        p = self.path()
        write_xlsx(p, rows)
        rc = inspect_download.main([p, "--json"])
        self.assertEqual(rc, 0)

    def test_empty_file_is_flagged(self):
        p = self.path("empty.xlsx")
        open(p, "wb").close()
        rc = inspect_download.main([p, "--json"])
        self.assertEqual(rc, 2)

    def test_html_login_page_is_not_data(self):
        p = self.path("login.xlsx")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("<!doctype html><html><body>Sesion expirada</body></html>")
        rc = inspect_download.main([p, "--json"])
        self.assertEqual(rc, 2)

    def test_truncation_exits_3(self):
        with mock.patch.object(inspect_download, "RECORD_CAP", 5):
            rows = [("DECL%03d" % d, 1, 10) for d in range(6)]  # 6 >= cap of 5
            p = self.path("big.xlsx")
            write_xlsx(p, rows)
            rc = inspect_download.main([p, "--json"])
        self.assertEqual(rc, 3)

    def test_records_from_item_numbering_when_id_missing(self):
        # Identificador all "No disponible" -> fall back to rows where Item == 1
        rows = []
        for d in range(3):
            for item in range(1, 5):
                rows.append(("No disponible", item, 7))
        p = self.path("noid.xlsx")
        write_xlsx(p, rows)
        rc = inspect_download.main([p, "--json"])
        self.assertEqual(rc, 0)


class CountRecords(unittest.TestCase):
    """The 30,000 cap counts customs records, not rows. Miscount it and a truncated
    file passes as complete."""

    def count(self, **cols):
        import pandas as pd
        return inspect_download.count_records(pd.DataFrame(cols))

    def test_no_disponible_falls_back_to_item_numbering(self):
        n, how = self.count(Identificador=["No disponible"] * 5,
                            Item=["1", "2", "3", "1", "2"])
        self.assertEqual(n, 2)
        self.assertIn("Item", how)

    def test_mexican_ordinal_strips_the_item_suffix(self):
        # MX glues the item onto the pedimento: 06255386-0001. Counted verbatim
        # that is one "record" per row, which defeats truncation detection.
        n, how = self.count(Ordinal=["06255386-0001", "06255386-0002",
                                     "06255386-0003", "06255387-0001"])
        self.assertEqual(n, 2)
        self.assertIn("suffix stripped", how)

    def test_plain_ordinal_is_left_alone(self):
        # CR, PA and Brasil cargas use Ordinal without a suffix.
        n, how = self.count(Ordinal=["1001", "1002", "1003"])
        self.assertEqual(n, 3)
        self.assertNotIn("suffix", how)

    def test_unknown_layout_says_unknown(self):
        self.assertEqual(self.count(Cualquiera=["x", "y"]), (None, None))


class RecordIntoManifest(unittest.TestCase):
    """--record picks the status from the file itself, so no count is retyped by
    hand (a real run once recorded 1 where the file held 16)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.run_dir = os.path.join(self.tmp, "run")
        os.makedirs(self.run_dir)
        job = {"country": "AR", "report": "importDetalladas",
               "date_from": "2026-01-01", "date_to": "2026-01-31", "filters": {},
               "status": "pending", "file": None, "rows": None, "records": None,
               "attempts": 0, "note": None, "updated_at": None}
        self.write_manifest({"jobs": [job], "download_dir": self.tmp})

    def write_manifest(self, m):
        import json
        with open(os.path.join(self.run_dir, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(m, fh)

    def job(self):
        import json
        with open(os.path.join(self.run_dir, "manifest.json"), encoding="utf-8") as fh:
            return json.load(fh)["jobs"][0]

    def record(self, path):
        import contextlib, io as _io
        with contextlib.redirect_stdout(_io.StringIO()):
            return inspect_download.main([path, "--record", self.run_dir, "--job", "0"])

    def test_real_data_is_done_with_both_counts(self):
        p = os.path.join(self.tmp, "ok.xlsx")
        write_xlsx(p, [("D1", 1, 5), ("D1", 2, 5), ("D2", 1, 5)])
        self.assertEqual(self.record(p), 0)
        j = self.job()
        self.assertEqual((j["status"], j["rows"], j["records"], j["file"]),
                         ("done", 3, 2, "ok.xlsx"))

    def test_empty_file_is_skipped_not_failed(self):
        p = os.path.join(self.tmp, "empty.xlsx")
        write_xlsx(p, [])
        self.record(p)
        self.assertEqual(self.job()["status"], "skipped")

    def test_login_page_is_failed(self):
        p = os.path.join(self.tmp, "login.xlsx")
        with open(p, "w") as fh:
            fh.write("<!DOCTYPE html><html>login</html>")
        self.record(p)
        j = self.job()
        self.assertEqual((j["status"], j["attempts"]), ("failed", 1))

    def test_truncated_is_failed_not_done(self):
        p = os.path.join(self.tmp, "big.xlsx")
        write_xlsx(p, [("D%d" % i, 1, 1) for i in range(6)])
        with mock.patch.object(inspect_download, "RECORD_CAP", 5):
            self.assertEqual(self.record(p), 3)
        self.assertEqual(self.job()["status"], "failed")

    def test_record_requires_a_job(self):
        with self.assertRaises(SystemExit):
            inspect_download.main([os.path.join(self.tmp, "x.xlsx"), "--record", self.run_dir])


if __name__ == "__main__":
    unittest.main()
