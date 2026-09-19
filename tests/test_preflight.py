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


class Dates(unittest.TestCase):
    def test_malformed_date_is_impossible_not_a_crash(self):
        # A traceback exits 1, which a caller would read as WARN.
        r = verdict("ar", "importaciones", date_from="2026")
        self.assertEqual(r["verdict"], "IMPOSSIBLE")

    def test_reversed_range_is_impossible(self):
        r = verdict("ar", "importaciones", date_from="2026-07", date_to="2026-01")
        self.assertEqual(r["verdict"], "IMPOSSIBLE")

    def test_live_base_past_the_snapshot_warns_instead_of_refusing(self):
        # The catalog is a snapshot; EC loads almost daily. Asking for a month
        # after the stored cutoff must send the user to the form, not refuse.
        r = verdict("ec", "importaciones", date_from="2026-09", date_to="2026-09")
        self.assertEqual(r["verdict"], "WARN")
        self.assertTrue(any("precargado" in m for m in r["messages_es"]))

    def test_frozen_base_past_its_cutoff_is_still_impossible(self):
        r = verdict("mx", "importaciones", date_from="2026-01", date_to="2026-01")
        self.assertEqual(r["verdict"], "IMPOSSIBLE")

    def test_daily_warning_ignores_a_range_that_never_reaches_the_last_month(self):
        r = verdict("uy", "importaciones", date_from="2025-01", date_to="2025-06")
        self.assertFalse(any("casi a diario" in m for m in r["messages_es"]))


class Europe(unittest.TestCase):
    def test_spain_own_import_report_gets_no_procedencia_warning(self):
        # España's own Importaciones carries the real País de Origen.
        r = verdict("es", "importaciones")
        self.assertFalse(any("Procedencia" in m for m in r["messages_es"]))

    def test_spain_totalizadas_is_eu_standard(self):
        r = verdict("es", "importaciones totalizadas")
        self.assertTrue(any("EUROS" in m for m in r["messages_es"]))

    def test_eu_warning_is_said_once(self):
        r = verdict("de", "importaciones")
        self.assertEqual(sum("EUROS" in m.upper() and "FOB" in m for m in r["messages_es"]), 1)


if __name__ == "__main__":
    unittest.main()
