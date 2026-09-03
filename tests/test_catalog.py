import json
import os
import unittest

import _bootstrap  # noqa: F401
import _catalog

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "skills", "softrade-batch", "references", "catalog.json")

# The 25 ids frozen in docs/handoff-motor-consultas.md. Any change here must be
# matched in tools/build_catalog.py and the ChatGPT brief.
CANONICAL = {
    "import", "importDetalladas", "export", "exportDetalladas", "otrasOperaciones",
    "historicoImport", "historicoExport", "cargasIngresos", "cargasSalidas",
    "cargasMaritimasIngresos", "cargasMaritimasSalidas", "cargasHistoricoIngresos",
    "cargasHistoricoSalidas", "cargasTotalesIngresos", "cargasTotalesSalidas",
    "cargasMaritimas", "cargasAereas", "cargasTerrestres", "zonaFranca",
    "zonaLibreIngresos", "zonaLibreSalidas", "transitos", "importTotalizadas",
    "exportTotalizadas", "normativa",
}


class CatalogShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(CATALOG, encoding="utf-8") as fh:
            cls.cat = json.load(fh)

    def test_parses_and_has_sections(self):
        for key in ("meta", "report_types", "report_aliases", "countries"):
            self.assertIn(key, self.cat)

    def test_report_types_are_exactly_the_canonical_set(self):
        self.assertEqual(set(self.cat["report_types"]), CANONICAL)

    def test_78_countries_across_the_expected_regions(self):
        self.assertEqual(len(self.cat["countries"]), 78)
        from collections import Counter
        regions = Counter(c["region"] for c in self.cat["countries"].values())
        self.assertEqual(regions, Counter({
            "sudamerica": 10, "centroamerica": 8, "norteamerica": 3,
            "asia": 17, "africa": 9, "oceania": 2, "europa": 29,
        }))

    def test_every_country_report_is_a_known_report_type(self):
        for cc, c in self.cat["countries"].items():
            for rid in c["reports"]:
                self.assertIn(rid, CANONICAL, "%s/%s" % (cc, rid))

    def test_every_report_entry_has_the_required_shape(self):
        for cc, c in self.cat["countries"].items():
            for rid, e in c["reports"].items():
                where = "%s/%s" % (cc, rid)
                self.assertIn("cutoff", e, where)
                self.assertIn("columns_measured", e, where)
                self.assertIn("names", e, where)
                self.assertEqual(set(e["names"]), {"local", "counterparty"}, where)
                if e["cutoff"] is not None:
                    # must be a valid ISO date
                    _catalog.parse_iso(e["cutoff"])

    def test_aliases_all_resolve_to_a_canonical_id(self):
        for alias, rid in self.cat["report_aliases"].items():
            self.assertIn(rid, CANONICAL, alias)


class ResolveReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = _catalog.load()

    def test_free_text_and_snake_case(self):
        r = _catalog.resolve_report
        self.assertEqual(r(self.cat, "imports_detailed"), "importDetalladas")
        self.assertEqual(r(self.cat, "impo detalladas"), "importDetalladas")
        self.assertEqual(r(self.cat, "las expo"), "export")
        self.assertEqual(r(self.cat, "Cargas Totales"), "cargasTotalesIngresos")
        self.assertEqual(r(self.cat, "importDetalladas"), "importDetalladas")

    def test_unknown_report_raises(self):
        with self.assertRaises(_catalog.CatalogError):
            _catalog.resolve_report(self.cat, "flujos magicos")

    def test_report_not_offered_lists_alternatives(self):
        with self.assertRaises(_catalog.CatalogError) as ctx:
            _catalog.entry(self.cat, "cl", "importDetalladas")
        self.assertIn("no ofrece", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
