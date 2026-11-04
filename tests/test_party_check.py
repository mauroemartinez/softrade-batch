import contextlib
import io
import json
import os
import tempfile
import unittest

import _bootstrap  # noqa: F401
import party_check


class Classify(unittest.TestCase):
    def test_to_order_variants(self):
        for n in ("TO ORDER", "TO THE ORDER OF BANCO X", "A LA ORDEN", "Al orden de Banco Y"):
            self.assertEqual(party_check.classify(n), "to_order", n)

    def test_known_logistics_brands(self):
        for n in ("KUEHNE + NAGEL LTDA", "DHL GLOBAL FORWARDING", "Maersk Line",
                  "MSC MEDITERRANEAN SHIPPING CO", "EXPEDITORS INTERNATIONAL"):
            self.assertEqual(party_check.classify(n), "logistics", n)

    def test_logistics_words_are_only_a_heuristic_bucket(self):
        self.assertEqual(party_check.classify("ANDES CARGO SRL"), "generic")
        self.assertEqual(party_check.classify("FREIGHT SOLUTIONS SA"), "generic")
        self.assertEqual(party_check.classify("CRAFT MULTIMODAL LTDA"), "generic")
        self.assertEqual(party_check.classify("ATB SUPPLYCHAIN S.A."), "generic")

    def test_ordinary_company_stays_a_company(self):
        for n in ("ACEROS DEL SUR SA", "Mi Empresa Argentina S.A.", "ZIMMERMANN GMBH"):
            self.assertEqual(party_check.classify(n), "company", n)

    def test_ambiguous_brand_words_need_shipping_context(self):
        # EVERGREEN, AGILITY, MSC and ZIM are also ordinary company words; alone
        # they must not turn a real importer into a "logistics" row.
        for n in ("EVERGREEN PACKAGING SA", "AGILITY FITNESS SRL", "MSC SOFTWARE CORP",
                  "ZIM ALIMENTOS LTDA"):
            self.assertEqual(party_check.classify(n), "company", n)
        for n in ("EVERGREEN MARINE CORP", "EVERGREEN LINE", "AGILITY LOGISTICS",
                  "MSC CHILE S.A.", "ZIM INTEGRATED SHIPPING SERVICES"):
            self.assertIn(party_check.classify(n), ("logistics", "generic"), n)
        self.assertEqual(party_check.classify("EVERGREEN MARINE CORP"), "logistics")
        self.assertEqual(party_check.classify("ZIM INTEGRATED SHIPPING SERVICES"), "logistics")
        # Brand wins over GENERIC; "GLOBAL INTEGRATED" has no generic word, so only
        # the AGILITY brand pattern can make it "logistics".
        self.assertEqual(party_check.classify("AGILITY LOGISTICS"), "logistics")
        self.assertEqual(party_check.classify("AGILITY GLOBAL INTEGRATED"), "logistics")

    def test_bare_transport_is_a_logistics_word(self):
        self.assertEqual(party_check.classify("ANDINA TRANSPORT SA"), "generic")
        self.assertEqual(party_check.classify("TRANSPORTES DEL PLATA SRL"), "generic")


class Analyse(unittest.TestCase):
    def test_shares_per_party_column(self):
        import pandas as pd
        frame = pd.DataFrame({
            "Consignatario": ["TO ORDER", "DHL EXPRESS", "ACME SA", "ACME SA", "No disponible"],
            "Shipper": ["CHINA WIRE CO"] * 5,
            "Fecha": ["2026-08-01"] * 5,
        })
        r = party_check.analyse(frame)
        self.assertEqual(set(r), {"Consignatario", "Shipper"})
        c = r["Consignatario"]
        self.assertEqual(c["rows_named"], 4)      # "No disponible" is not a name
        self.assertEqual(c["share_pct"]["to_order"], 25.0)
        self.assertEqual(c["share_pct"]["logistics"], 25.0)
        self.assertEqual(c["share_pct"]["company"], 50.0)
        self.assertEqual(c["top"][0], {"name": "ACME SA", "rows": 2, "kind": "company"})

    def test_free_zone_operador_is_a_party_column(self):
        # CR Zona Franca names only the Operador; PA Zona Libre, Operador + Proveedor.
        import pandas as pd
        frame = pd.DataFrame({"Operador": ["ACME ZF SA"], "Proveedor": ["CHINA WIRE CO"]})
        self.assertEqual(set(party_check.analyse(frame)), {"Operador", "Proveedor"})

    def test_column_names_match_regardless_of_case_accents_and_spaces(self):
        import pandas as pd
        names = ["CONSIGNATARIO ", "Probable  Importador", "Operadór", "Remitente\t"]
        frame = pd.DataFrame({c: ["ACME SA"] for c in names + ["Fecha"]})
        self.assertEqual(set(party_check.analyse(frame)), set(names))


class Cli(unittest.TestCase):
    """main() on a real .xlsx written by pandas, as the skill runs it."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name

    def xlsx(self, columns, name="cargas.xlsx"):
        import pandas as pd
        path = os.path.join(self.dir, name)
        pd.DataFrame(columns).to_excel(path, index=False)
        return path

    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = party_check.main(list(argv))
        return code, out.getvalue()

    def sample(self):
        return self.xlsx({
            "Consignatario": ["TO ORDER", "DHL EXPRESS", "ACME SA", "ACME SA"],
            "Shipper": ["CHINA WIRE CO"] * 4,
            "Notify": ["No disponible"] * 4,
            "Fecha": ["2026-08-01"] * 4,
        })

    def test_text_report_lists_shares_and_names(self):
        code, out = self.run_main(self.sample())
        self.assertEqual(code, 0)
        self.assertIn("Consignatario", out)
        self.assertIn("TO ORDER 25.0%", out)
        self.assertIn("ACME SA", out)
        self.assertIn("DHL EXPRESS  <- logistics", out)
        self.assertRegex(out, r"Notify\s+no names")

    def test_no_names_hides_every_company_name(self):
        code, out = self.run_main(self.sample(), "--no-names")
        self.assertEqual(code, 0)
        self.assertIn("TO ORDER 25.0%", out)
        for n in ("ACME SA", "DHL EXPRESS", "CHINA WIRE CO"):
            self.assertNotIn(n, out)

    def test_json_output(self):
        code, out = self.run_main(self.sample(), "--json")
        self.assertEqual(code, 0)
        r = json.loads(out)
        self.assertEqual(set(r), {"Consignatario", "Shipper", "Notify"})
        self.assertEqual(r["Notify"], {"rows_named": 0})
        self.assertEqual(r["Consignatario"]["share_pct"]["logistics"], 25.0)
        self.assertEqual(r["Shipper"]["top"],
                         [{"name": "CHINA WIRE CO", "rows": 4, "kind": "company"}])

    def test_json_with_no_names_drops_the_top_lists(self):
        code, out = self.run_main(self.sample(), "--json", "--no-names")
        self.assertEqual(code, 0)
        r = json.loads(out)
        self.assertTrue(all("top" not in v for v in r.values()))
        self.assertNotIn("ACME SA", out)

    def test_file_without_party_columns(self):
        path = self.xlsx({"Fecha": ["2026-08-01"], "FOB": ["10"]}, name="totales.xlsx")
        code, out = self.run_main(path)
        self.assertEqual(code, 0)
        self.assertIn("no party columns found", out)
        code, out = self.run_main(path, "--json")
        self.assertEqual((code, json.loads(out)), (0, {}))

    def test_missing_file_exits_with_error(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_main(os.path.join(self.dir, "nope.xlsx"))
        self.assertNotIn(cm.exception.code, (0, None))
        self.assertIn("no such file", str(cm.exception.code))


if __name__ == "__main__":
    unittest.main()
