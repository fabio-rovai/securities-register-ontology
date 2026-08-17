"""Offline unit tests: validators against known-answer identifiers, and the
foreign-content refinement against real specimen values from the harvest."""
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
from lei_util import (classify_lei, classify_isin, classify_cusip,
                      lei_checksum_ok)
from build_graph import refine_reason


class TestLEI(unittest.TestCase):
    def test_known_valid(self):
        # Apple, US Bancorp, GLEIF's own LEI
        for lei in ("HWUPKR0MPOU8FGXBT394", "N1GZ7BBF3NP8GI976H15",
                    "506700GE1G29325QX363"):
            self.assertEqual(classify_lei(lei)[0], "valid", lei)

    def test_known_invalid(self):
        self.assertEqual(classify_lei("HWUPKR0MPOU8FGXBT395")[0], "bad_checksum")
        # Voya N-PORT specimen: I->1 substitution breaks the check digits
        self.assertEqual(classify_lei("254900FK12RDASVD0175")[0], "bad_checksum")
        self.assertEqual(classify_lei("254900FKI2RDASVD0175")[0], "valid")

    def test_placeholder_and_empty(self):
        self.assertEqual(classify_lei("00000000000000000000")[0], "placeholder")
        self.assertEqual(classify_lei("N/A")[0], "empty")
        self.assertEqual(classify_lei("")[0], "empty")
        self.assertEqual(classify_lei(None)[0], "empty")

    def test_malformed(self):
        for v in ("000-16205", "549300JA4S68DHG0253", "13915242"):
            self.assertEqual(classify_lei(v)[0], "malformed", v)


class TestRefineReason(unittest.TestCase):
    def test_foreign_content(self):
        # real specimen values published in EDGAR's LEI field
        for v in ("(646) 508-0022", "424-231-9100", "33-4802710",
                  "DANGEROUS 7 SPV 2 LP", "QUANTIC VC, LLC",
                  "81-3-6214-3600"):
            self.assertEqual(refine_reason("malformed", v), "foreign_content", v)

    def test_plain_malformed(self):
        for v in ("13915242", "02009520", "549300JA4S68DHG0253"):
            self.assertEqual(refine_reason("malformed", v), "malformed", v)

    def test_na_token_is_placeholder(self):
        self.assertEqual(refine_reason("empty", "N/A"), "placeholder")


class TestISINCUSIP(unittest.TestCase):
    def test_isin(self):
        self.assertEqual(classify_isin("US0378331005")[0], "valid")   # Apple
        self.assertEqual(classify_isin("US0378331004")[0], "bad_checksum")
        self.assertEqual(classify_isin("XX12")[0], "malformed")

    def test_cusip(self):
        self.assertEqual(classify_cusip("037833100")[0], "valid")     # Apple
        self.assertEqual(classify_cusip("037833101")[0], "bad_checksum")
        self.assertEqual(classify_cusip("00000000")[0], "malformed")


class TestTurtleParses(unittest.TestCase):
    def test_artifacts_parse(self):
        import rdflib
        base = os.path.join(os.path.dirname(__file__), "..")
        for rel in ("ontology/securities-register.ttl", "ontology/schemes.ttl",
                    "shacl/layer1-structural.ttl", "shacl/layer2-conformance.ttl",
                    "shacl/layer3-crossregister.ttl"):
            g = rdflib.Graph()
            g.parse(os.path.join(base, rel), format="turtle")
            self.assertGreater(len(g), 5, rel)


if __name__ == "__main__":
    unittest.main()
