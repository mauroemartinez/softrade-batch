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


if __name__ == "__main__":
    unittest.main()
