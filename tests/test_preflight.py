import datetime as dt
import unittest

import _bootstrap  # noqa: F401
import _catalog
import preflight

TODAY = dt.date(2026, 9, 3)  # fixed so vitality checks do not drift


def verdict(country, report, by_company=False, date_from=None, date_to=None):
    cat = _catalog.load()
    return preflight.evaluate(cat, country, report, by_company,
                              date_from, date_to, today=TODAY)


class Verdicts(unittest.TestCase):
    def test_ar_import_detalladas_by_company_is_ok(self):
        r = verdict("ar", "impo detalladas", by_company=True)
        self.assertEqual(r["verdict"], "OK")
        self.assertEqual(r["company_side"], "Importador")
        self.assertEqual(r["report"], "importDetalladas")

    def test_ec_import_is_ok_and_names_counterparty(self):
        r = verdict("ec", "importaciones", by_company=True)
        self.assertEqual(r["verdict"], "OK")
        self.assertEqual(r["company_side"], "Importador")

    def test_ar_export_by_company_is_impossible(self):
        r = verdict("ar", "las expo", by_company=True)
        self.assertEqual(r["verdict"], "IMPOSSIBLE")
        self.assertTrue(any("no publica el exportador" in m for m in r["messages_es"]))

    def test_ar_export_detalladas_by_company_is_impossible_no_disponible(self):
        r = verdict("ar", "exportDetalladas", by_company=True)
        self.assertEqual(r["verdict"], "IMPOSSIBLE")
        self.assertTrue(any("No disponible" in m for m in r["messages_es"]))

    def test_cl_import_detalladas_does_not_exist(self):
        r = verdict("cl", "importaciones detalladas")
        self.assertEqual(r["verdict"], "IMPOSSIBLE")

    def test_mx_import_2026_is_impossible_frozen(self):
        r = verdict("mx", "importaciones", date_from="2026-01", date_to="2026-06")
        self.assertEqual(r["verdict"], "IMPOSSIBLE")

    def test_mx_cargas_totales_is_ok(self):
        r = verdict("mx", "cargas totales", by_company=True)
        self.assertEqual(r["verdict"], "OK")
        self.assertEqual(r["report"], "cargasTotalesIngresos")

    def test_py_by_company_warns_probable(self):
        r = verdict("py", "importaciones", by_company=True)
        self.assertEqual(r["verdict"], "WARN")
        self.assertTrue(any("Probable" in m for m in r["messages_es"]))

    def test_ni_import_by_company_warns_unknown_form(self):
        r = verdict("ni", "importaciones", by_company=True)
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["company_side"], "unknown")

    def test_eu_block_warns_euros(self):
        r = verdict("de", "importaciones")
        self.assertEqual(r["verdict"], "WARN")
        self.assertTrue(any("EUROS" in m for m in r["messages_es"]))

    def test_normativa_is_impossible(self):
        r = verdict("uy", "normativa")
        self.assertEqual(r["verdict"], "IMPOSSIBLE")

    def test_daily_country_warns_current_month(self):
        r = verdict("uy", "importaciones")
        self.assertEqual(r["verdict"], "WARN")
        self.assertTrue(any("casi a diario" in m for m in r["messages_es"]))

    def test_range_past_cutoff_reports_effective_to(self):
        r = verdict("ar", "importaciones", date_from="2026-01", date_to="2026-12")
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["effective_to"], "07/2026")

    def test_exit_code_mapping(self):
        self.assertEqual(preflight._EXIT["OK"], 0)
        self.assertEqual(preflight._EXIT["WARN"], 1)
        self.assertEqual(preflight._EXIT["IMPOSSIBLE"], 2)


if __name__ == "__main__":
    unittest.main()
