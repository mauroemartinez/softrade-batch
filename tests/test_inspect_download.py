import os
import shutil
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


def write_truncated_xlsx(path):
    """A real workbook cut in half, as a download interrupted mid-transfer."""
    full = path + ".full"
    write_xlsx(full, [("D%d" % i, 1, 5) for i in range(50)])
    with open(full, "rb") as fh:
        data = fh.read()
    os.remove(full)
    with open(path, "wb") as fh:
        fh.write(data[: len(data) // 2])


class InspectDownload(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

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

    def test_corrupt_xlsx_exits_2_without_traceback(self):
        # A download cut short is a zip with no central directory. It must end as
        # "unreadable" (exit 2), not as an openpyxl/zipfile traceback.
        import contextlib, io as _io
        p = self.path("half.xlsx")
        write_truncated_xlsx(p)
        out = _io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = inspect_download.main([p, "--json"])
        self.assertEqual(rc, 2)
        self.assertIn("UNREADABLE", out.getvalue())

    def test_no_key_column_falls_back_to_rows(self):
        # No identifier and no Item: rows are the only count there is. At the cap
        # the file may be truncated, so it must not pass as complete.
        import contextlib, io as _io
        p = self.path("nokey.xlsx")
        write_xlsx(p, [("x%d" % i, 1) for i in range(6)], header=("Cualquiera", "Valor"))
        out = _io.StringIO()
        with mock.patch.object(inspect_download, "RECORD_CAP", 5),                 contextlib.redirect_stdout(out):
            rc = inspect_download.main([p])
        self.assertEqual(rc, 3)
        self.assertIn("by ROWS", out.getvalue())

    def test_no_key_column_json_flags_rows_basis(self):
        import contextlib, io as _io, json
        p = self.path("nokey.xlsx")
        write_xlsx(p, [("x%d" % i, 1) for i in range(6)], header=("Cualquiera", "Valor"))
        out = _io.StringIO()
        with mock.patch.object(inspect_download, "RECORD_CAP", 5),                 contextlib.redirect_stdout(out):
            rc = inspect_download.main([p, "--json"])
        self.assertEqual(rc, 3)
        data = json.loads(out.getvalue())
        self.assertIsNone(data["records"])
        self.assertTrue(data["truncated"])
        self.assertIn("rows", data["truncation_basis"])

    def test_no_key_column_under_cap_is_fine(self):
        # Rows >= records always, so fewer rows than the cap cannot be truncated.
        import contextlib, io as _io
        p = self.path("nokey.xlsx")
        write_xlsx(p, [("x%d" % i, 1) for i in range(4)], header=("Cualquiera", "Valor"))
        with mock.patch.object(inspect_download, "RECORD_CAP", 5),                 contextlib.redirect_stdout(_io.StringIO()):
            self.assertEqual(inspect_download.main([p]), 0)


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
        self.addCleanup(shutil.rmtree, self.tmp, True)
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

    def test_corrupt_xlsx_is_failed_with_a_reason(self):
        p = os.path.join(self.tmp, "half.xlsx")
        write_truncated_xlsx(p)
        self.assertEqual(self.record(p), 2)
        j = self.job()
        self.assertEqual((j["status"], j["attempts"], j["file"]), ("failed", 1, "half.xlsx"))
        self.assertIn("unreadable", j["note"])

    def test_no_key_column_at_cap_is_failed_by_rows(self):
        p = os.path.join(self.tmp, "nokey.xlsx")
        write_xlsx(p, [("x%d" % i, 1) for i in range(6)], header=("Cualquiera", "Valor"))
        with mock.patch.object(inspect_download, "RECORD_CAP", 5):
            self.assertEqual(self.record(p), 3)
        j = self.job()
        self.assertEqual((j["status"], j["rows"], j["records"]), ("failed", 6, None))
        self.assertIn("rows", j["note"])

    def test_missing_dependency_leaves_the_manifest_alone(self):
        # Without pandas/openpyxl a good file is not "unreadable": it must not be
        # marked failed (and re-downloaded) for an environment problem.
        import sys
        p = os.path.join(self.tmp, "ok.xlsx")
        write_xlsx(p, [("D1", 1, 5)])
        before = self.job()
        for module in ("pandas", "openpyxl"):
            with self.subTest(missing=module), mock.patch.dict(sys.modules, {module: None}):
                with self.assertRaises(SystemExit) as cm:
                    self.record(p)
                self.assertIn("missing dependency", str(cm.exception.code))
                self.assertEqual(self.job(), before)

    def test_record_requires_a_job(self):
        with self.assertRaises(SystemExit):
            inspect_download.main([os.path.join(self.tmp, "x.xlsx"), "--record", self.run_dir])


def run_main(argv):
    """main() with its stdout captured: (exit code, printed text)."""
    import contextlib, io as _io
    out = _io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = inspect_download.main(argv)
    return rc, out.getvalue()


class TextInputs(unittest.TestCase):
    """read_table also takes .csv/.txt, decoded as UTF-16/UTF-32 when a BOM says
    so, else UTF-8 (BOM dropped) or cp1252; NUL bytes without a BOM are refused.
    Of `,` `;` tab and `|` it keeps the separator that gives the header's
    column count on the most lines (ties in that order). Anything else is refused
    with SystemExit."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def write(self, name, text, encoding="utf-8"):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding=encoding, newline="") as fh:
            fh.write(text)
        return p

    def assertReads(self, p, columns, rows, records):
        frame = inspect_download.read_table(p)
        self.assertEqual(list(frame.columns), columns)
        self.assertEqual(len(frame), rows)
        self.assertEqual(inspect_download.count_records(frame)[0], records)

    def test_each_supported_separator(self):
        cols = ["Identificador", "Item", "Valor"]
        for name, sep in (("coma.csv", ","), ("punto_y_coma.csv", ";"),
                          ("tab.txt", "\t"), ("pipe.txt", "|"), ("coma.txt", ",")):
            with self.subTest(file=name):
                body = sep.join(cols) + "\n" + "\n".join(
                    sep.join(r) for r in (("D1", "1", "5"), ("D1", "2", "5"), ("D2", "1", "5"))) + "\n"
                self.assertReads(self.write(name, body), cols, 3, 2)

    def test_semicolon_file_with_decimal_commas(self):
        # The Spanish-locale CSV: `;` between fields, `,` inside numbers. Trying
        # `,` first must not split the values apart.
        p = self.write("es.csv", "Identificador;Item;Valor\nD1;1;5,5\nD1;2;7,25\nD2;1;3\n")
        frame = inspect_download.read_table(p)
        self.assertEqual(list(frame.columns), ["Identificador", "Item", "Valor"])
        self.assertEqual(list(frame["Valor"]), ["5,5", "7,25", "3"])

    def test_utf8_bom_does_not_hide_the_identifier(self):
        # Excel's "CSV UTF-8" starts with a BOM; glued to the first header it
        # would hide Identificador and drop the count back to rows.
        p = self.write("bom.csv", "﻿Identificador;Item\nD1;1\nD1;2\nD2;1\n")
        self.assertReads(p, ["Identificador", "Item"], 3, 2)

    def test_single_column_file_still_reads(self):
        p = self.write("one.csv", "Valor\n1\n2\n")
        self.assertReads(p, ["Valor"], 2, None)

    def test_csv_end_to_end_records_into_the_manifest(self):
        import json
        run_dir = os.path.join(self.tmp, "run")
        os.makedirs(run_dir)
        with open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump({"jobs": [{"status": "pending", "attempts": 0}]}, fh)
        p = self.write("ok.txt", "Identificador\tItem\tValor\nD1\t1\t5\nD1\t2\t5\nD2\t1\t5\n")
        rc, _ = run_main([p, "--record", run_dir, "--job", "0"])
        self.assertEqual(rc, 0)
        with open(os.path.join(run_dir, "manifest.json"), encoding="utf-8") as fh:
            job = json.load(fh)["jobs"][0]
        self.assertEqual((job["status"], job["rows"], job["records"], job["file"]),
                         ("done", 3, 2, "ok.txt"))

    def test_cp1252_csv_is_read_not_called_corrupt(self):
        # Excel on a Spanish Windows saves "CSV" as cp1252: it must read, not be
        # reported UNREADABLE ("download again"), which no re-download fixes.
        p = self.write("latin.csv", "Identificador;Item;Descripción\nD1;1;Café\nD2;1;Té\n",
                       encoding="cp1252")
        self.assertReads(p, ["Identificador", "Item", "Descripción"], 2, 2)

    def test_utf16_text_is_read_not_turned_into_nul_columns(self):
        # Excel's "Texto Unicode (*.txt)" is tab-separated UTF-16 with a BOM.
        # cp1252 decodes those bytes without error, so it must not get them.
        for encoding in ("utf-16", "utf-16-be", "utf-32"):
            with self.subTest(encoding=encoding):
                body = "Identificador\tItem\tValor\nD1\t1\t5\nD1\t2\t5\nD2\t1\t5\n"
                if encoding == "utf-16-be":
                    body = "﻿" + body  # the codec adds no BOM on its own
                p = self.write("unicode-%s.txt" % encoding, body, encoding=encoding)
                self.assertReads(p, ["Identificador", "Item", "Valor"], 3, 2)

    def test_nul_bytes_without_a_bom_are_unreadable_not_done(self):
        # UTF-16 without a BOM (or any binary) must not reach cp1252 and come out
        # as "done" with garbage columns.
        p = os.path.join(self.tmp, "nobom.txt")
        with open(p, "wb") as fh:
            fh.write("Identificador\tItem\nD1\t1\n".encode("utf-16-le"))
        rc, out = run_main([p])
        self.assertEqual(rc, 2, out)
        self.assertIn("UNREADABLE", out)

    def test_comma_in_a_header_does_not_hijack_the_split(self):
        # A `;` file whose header carries one comma (and whose rows carry none):
        # `;` splits every line the same way, `,` only the header.
        p = self.write("hdr.csv", "Identificador;Item;Valor FOB, USD\nD1;1;5\nD2;1;6\n")
        self.assertReads(p, ["Identificador", "Item", "Valor FOB, USD"], 2, 2)

    def test_company_named_login_is_not_an_html_page(self):
        # The first bytes of a CSV are data: an importer such as "LOGINTER S.A."
        # must not make a good file "NOT DATA". Only markup or whole error
        # phrases mark an error page.
        p = self.write("ok.csv", "Identificador;Item;Importador\nD1;1;LOGINTER S.A.\nD2;1;ACME\n")
        rc, out = run_main([p])
        self.assertEqual(rc, 0, out)

    def test_unsupported_extension_exits_and_leaves_the_manifest_alone(self):
        import json
        run_dir = os.path.join(self.tmp, "run")
        os.makedirs(run_dir)
        manifest = os.path.join(run_dir, "manifest.json")
        with open(manifest, "w", encoding="utf-8") as fh:
            json.dump({"jobs": [{"status": "pending", "attempts": 0}]}, fh)
        with open(manifest, encoding="utf-8") as fh:
            before = fh.read()
        p = self.write("export.json", '{"rows": []}')
        for argv in ([p], [p, "--json"], [p, "--record", run_dir, "--job", "0"]):
            with self.subTest(argv=argv[1:]):
                with self.assertRaises(SystemExit) as cm:
                    run_main(argv)
                self.assertIn("unsupported extension: .json", str(cm.exception.code))
        with open(manifest, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), before)


class NearCapNote(unittest.TestCase):
    """Over 90% of the cap the file is complete but the next period may not be:
    main() prints a NOTE and still records done / exits 0."""

    CAP = 20  # NOTE when counted > 18, truncated at >= 20

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        patcher = mock.patch.object(inspect_download, "RECORD_CAP", self.CAP)
        patcher.start()
        self.addCleanup(patcher.stop)

    def inspect(self, rows, header=("Identificador", "Item", "Valor")):
        p = os.path.join(self.tmp, "f.xlsx")
        write_xlsx(p, rows, header=header)
        return run_main([p])

    def test_by_records(self):
        # 19 declarations x 2 items: 38 rows, which alone would be "truncated";
        # the 19 records are what is compared, and they are only near the cap.
        rows = [("D%02d" % d, i, 1) for d in range(19) for i in (1, 2)]
        rc, out = self.inspect(rows)
        self.assertEqual(rc, 0)
        self.assertIn("NOTE: 19 records is close to the 20 cap", out)
        self.assertNotIn("TRUNCATED", out)

    def test_by_rows_without_a_record_key(self):
        rc, out = self.inspect([("x%d" % i, 1) for i in range(19)], header=("Cualquiera", "Valor"))
        self.assertEqual(rc, 0)
        self.assertIn("NOTE: 19 rows (counted by rows, no record key) is close to the 20 cap", out)

    def test_exactly_ninety_percent_has_no_note(self):
        for header, rows in ((("Identificador", "Item", "Valor"), [("D%02d" % d, 1, 1) for d in range(18)]),
                             (("Cualquiera", "Valor"), [("x%d" % i, 1) for i in range(18)])):
            with self.subTest(header=header[0]):
                rc, out = self.inspect(rows, header=header)
                self.assertEqual(rc, 0)
                self.assertNotIn("NOTE", out)


if __name__ == "__main__":
    unittest.main()
