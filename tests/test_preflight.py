import contextlib
import copy
import datetime as dt
import io
import json
import os
import tempfile
import unittest
from unittest import mock

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

    def test_mx_cargas_totales_by_company_is_usable_with_caveat(self):
        # Alive and names both sides, but whether those are the real trading
        # parties or bill-of-lading consignees is not confirmed yet.
        r = verdict("mx", "cargas totales", by_company=True)
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["report"], "cargasTotalesIngresos")
        self.assertTrue(any("no está confirmado" in m for m in r["messages_es"]))

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


class SecondSurvey(unittest.TestCase):
    # Entries re-read on 2026-09-18 carry their own `surveyed` date.

    def test_entry_uses_its_own_survey_date(self):
        r = verdict("ec", "export", date_from="2026-10", date_to="2026-10")
        self.assertTrue(any("2026-09-18" in m for m in r["messages_es"]), r)

    def test_frozen_historic_is_impossible(self):
        r = verdict("br", "cargasHistoricoIngresos", date_from="2026-01", date_to="2026-03")
        self.assertEqual(r["verdict"], "IMPOSSIBLE")

    def test_anonymous_historic_refuses_company(self):
        r = verdict("bo", "historicoImport", by_company=True)
        self.assertEqual(r["verdict"], "IMPOSSIBLE")


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


class ManifestNames(unittest.TestCase):
    """Bill-of-lading consignees can be forwarders, carriers or 'TO ORDER'."""

    def test_by_company_on_cargas_warns_about_forwarders(self):
        r = verdict("br", "cargas maritimas ingresos", by_company=True)
        self.assertTrue(any("forwarder" in m for m in r["messages_es"]))
        self.assertTrue(any("Notify" in m for m in r["messages_es"]))

    def test_customs_report_gets_no_manifest_warning(self):
        r = verdict("ec", "importaciones", by_company=True)
        self.assertFalse(any("manifiestos" in m for m in r["messages_es"]))

    def test_no_warning_when_not_asking_about_companies(self):
        r = verdict("br", "cargas maritimas ingresos")
        self.assertFalse(any("manifiestos" in m for m in r["messages_es"]))

    def test_export_cargas_gets_no_real_importer_warning(self):
        # On Salidas the user filters by the Shipper, the exporter side: a
        # sentence about "el importador real" talks about the wrong party.
        r = verdict("br", "cargasMaritimasSalidas", by_company=True)
        self.assertFalse(any("importador real" in m for m in r["messages_es"]), r)
        self.assertFalse(any("manifiestos" in m for m in r["messages_es"]), r)

    def test_mx_export_cargas_gets_no_real_importer_warning(self):
        r = verdict("mx", "cargasTotalesSalidas", by_company=True)
        self.assertFalse(any("importador real" in m for m in r["messages_es"]), r)

    def test_catalog_saying_real_importer_silences_the_warning(self):
        # BR Histórico Ingresos: the catalog note says the consignee "funciona
        # como importador real"; preflight must not contradict it.
        r = verdict("br", "cargasHistoricoIngresos", by_company=True)
        self.assertFalse(any("manifiestos" in m for m in r["messages_es"]), r)
        self.assertTrue(any("funciona como importador real" in m for m in r["messages_es"]))

    def test_rule_follows_the_catalog_note_not_the_country(self):
        cat = copy.deepcopy(_catalog.load())
        e = cat["countries"]["EC"]["reports"]["cargasIngresos"]
        before = preflight.evaluate(cat, "ec", "cargasIngresos", True, today=TODAY)
        self.assertTrue(any("manifiestos" in m for m in before["messages_es"]))
        e["note"] = "en la muestra el consignatario funciona como importador real"
        after = preflight.evaluate(cat, "ec", "cargasIngresos", True, today=TODAY)
        self.assertFalse(any("manifiestos" in m for m in after["messages_es"]), after)

    def test_negated_note_keeps_the_warning(self):
        cat = copy.deepcopy(_catalog.load())
        e = cat["countries"]["EC"]["reports"]["cargasIngresos"]
        e["note"] = "el consignatario no es el importador real en 1 de cada 3 filas"
        r = preflight.evaluate(cat, "ec", "cargasIngresos", True, today=TODAY)
        self.assertTrue(any("manifiestos" in m for m in r["messages_es"]), r)


def run_main(argv):
    """preflight.main with today pinned; returns (exit, stdout, stderr)."""
    real = preflight.evaluate

    def pinned(*a, **kw):
        kw.setdefault("today", TODAY)
        return real(*a, **kw)

    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(preflight, "evaluate", pinned), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = preflight.main(argv)
        except SystemExit as ex:  # argparse
            code = ex.code
    return code, out.getvalue(), err.getvalue()


class Cli(unittest.TestCase):
    def test_ok_exits_0_with_human_output(self):
        code, out, _ = run_main(["--country", "ar", "--report", "impo detalladas",
                                 "--by-company"])
        self.assertEqual(code, 0, out)
        self.assertIn("veredicto     OK", out)
        self.assertIn("consulta      AR / importDetalladas  (impo detalladas)", out)
        self.assertIn("por empresa   OK: filtro Importador", out)

    def test_warn_exits_1(self):
        code, out, _ = run_main(["--country", "de", "--report", "importaciones"])
        self.assertEqual(code, 1, out)
        self.assertIn("veredicto     WARN", out)
        self.assertIn("EUROS", out)

    def test_impossible_exits_2(self):
        code, out, _ = run_main(["--country", "cl", "--report", "importaciones detalladas"])
        self.assertEqual(code, 2, out)
        self.assertIn("veredicto     IMPOSSIBLE", out)
        self.assertIn("consulta      ? / ?", out)

    def test_by_company_on_anonymous_report_exits_2(self):
        code, out, _ = run_main(["--country", "ar", "--report", "las expo", "--by-company"])
        self.assertEqual(code, 2, out)
        self.assertIn("no publica el exportador", out)

    def test_malformed_date_exits_2_not_a_traceback(self):
        code, out, _ = run_main(["--country", "ar", "--report", "importaciones",
                                 "--from", "2026"])
        self.assertEqual(code, 2, out)

    def test_json_output_is_parseable_and_matches_exit(self):
        code, out, _ = run_main(["--country", "de", "--report", "importaciones", "--json"])
        data = json.loads(out)
        self.assertEqual(data["verdict"], "WARN")
        self.assertEqual(code, preflight._EXIT[data["verdict"]])
        self.assertEqual(data["country"], "DE")

    def test_missing_catalog_exits_2(self):
        with tempfile.TemporaryDirectory() as d:
            code, out, err = run_main(["--country", "ar", "--report", "importaciones",
                                       "--catalog", os.path.join(d, "nope.json")])
        self.assertEqual(code, 2)
        self.assertIn("catalog.json", err)
        self.assertEqual(out, "")

    def test_malformed_catalog_exits_2_not_1(self):
        # A JSON traceback exits 1, which a caller would read as WARN.
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "catalog.json")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("{ no es json")
            code, out, err = run_main(["--country", "ar", "--report", "importaciones",
                                       "--catalog", p])
        self.assertEqual(code, 2)
        self.assertTrue(err.strip())

    def _run_with_catalog_text(self, text):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "catalog.json")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
            return run_main(["--country", "ar", "--report", "importaciones",
                             "--catalog", p])

    def test_valid_json_wrong_shape_catalog_exits_2_not_1(self):
        # Valid JSON but not a catalog: a KeyError/TypeError would exit 1 (WARN).
        for text in ("{}", "[]", '{"countries": [], "report_types": {}, "meta": {}}'):
            with self.subTest(text=text):
                code, out, err = self._run_with_catalog_text(text)
                self.assertEqual(code, 2, err)
                self.assertEqual(out, "")
                self.assertIn("no puedo leer el catálogo", err)

    def test_broken_entry_inside_catalog_exits_2_not_1(self):
        cat = copy.deepcopy(_catalog.load())
        cat["countries"]["AR"] = {}
        code, out, err = self._run_with_catalog_text(json.dumps(cat))
        self.assertEqual(code, 2, err)
        self.assertEqual(out, "")
        self.assertIn("no puedo leer el catálogo", err)

    def test_catalog_path_is_a_directory_exits_2(self):
        with tempfile.TemporaryDirectory() as d:
            code, _, err = run_main(["--country", "ar", "--report", "importaciones",
                                     "--catalog", d])
        self.assertEqual(code, 2)
        self.assertTrue(err.strip())

    def test_missing_required_args_exits_2(self):
        code, _, err = run_main(["--country", "ar"])
        self.assertEqual(code, 2)
        self.assertIn("--report", err)


if __name__ == "__main__":
    unittest.main()
