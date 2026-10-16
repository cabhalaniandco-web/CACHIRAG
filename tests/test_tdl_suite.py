"""
Unit tests for CA CHIRAG TDL Suite and Tally Integration Tools
"""

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from tools.tdl_validator import TDLValidator, validate_all_tdl
from tools.tally_xml_bridge import TallyXMLBridge


class TestTDLSuite(unittest.TestCase):
    def setUp(self):
        self.tally_dir = Path("/workspace/tally")
        self.tdl_files = list(self.tally_dir.glob("*.tdl"))

    def test_tdl_files_exist(self):
        self.assertGreater(len(self.tdl_files), 0, "No TDL files found in tally/")
        expected_files = [
            "GSTR2B_Portal_ImportButtons.tdl",
            "CA_Audit_Utilities.tdl",
            "Custom_Gateway_Menu.tdl",
            "Voucher_Auto_Post.tdl",
            "CA_Tally_Suite.tdl",
        ]
        for fname in expected_files:
            target = self.tally_dir / fname
            self.assertTrue(target.exists(), f"Expected TDL file missing: {fname}")

    def test_all_tdl_files_syntax_valid(self):
        self.assertTrue(validate_all_tdl(self.tally_dir), "TDL validation failed")

    def test_gstr2b_tdl_structure(self):
        gstr2b_file = self.tally_dir / "GSTR2B_Portal_ImportButtons.tdl"
        validator = TDLValidator(gstr2b_file)
        valid, errors, _ = validator.validate()
        self.assertTrue(valid, f"GSTR2B TDL invalid: {errors}")
        self.assertIn("GSTR2B Import Config", validator.defined_symbols["Report"])
        self.assertIn("GSTR2B Import Config", validator.defined_symbols["Form"])
        self.assertIn("GSTR2B Import Selected Vouchers", validator.defined_symbols["Function"])

    def test_ca_audit_utilities_structure(self):
        ca_audit_file = self.tally_dir / "CA_Audit_Utilities.tdl"
        validator = TDLValidator(ca_audit_file)
        valid, errors, _ = validator.validate()
        self.assertTrue(valid, f"CA Audit TDL invalid: {errors}")
        self.assertIn("CA ApplyAutoRoundOff", validator.defined_symbols["Function"])

    def test_custom_gateway_menu_structure(self):
        menu_file = self.tally_dir / "Custom_Gateway_Menu.tdl"
        validator = TDLValidator(menu_file)
        valid, errors, _ = validator.validate()
        self.assertTrue(valid, f"Menu TDL invalid: {errors}")
        self.assertIn("CA Tools Menu", validator.defined_symbols["Menu"])


class TestTallyXMLBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = TallyXMLBridge(company_name="Chirag & Co CA")

    def test_format_date_variations(self):
        self.assertEqual(self.bridge.format_tally_date("2026-10-15"), "20261015")
        self.assertEqual(self.bridge.format_tally_date("15/10/2026"), "20261015")

    def test_generate_purchase_voucher_xml(self):
        xml_str = self.bridge.generate_purchase_voucher_xml(
            date_val="2026-10-15",
            voucher_number="PURC/001",
            party_name="Vendor ABC",
            purchase_ledger="GST Purchase 18%",
            taxable_amount=1000.0,
            cgst_amount=90.0,
            sgst_amount=90.0,
            igst_amount=0.0,
        )
        # Parse XML to validate well-formedness
        root = ET.fromstring(xml_str)
        self.assertEqual(root.tag, "ENVELOPE")
        voucher = root.find(".//VOUCHER")
        self.assertIsNotNone(voucher)
        self.assertEqual(voucher.attrib.get("VCHTYPE"), "Purchase")

        # Verify ledger entries balance
        entries = voucher.findall("ALLLEDGERENTRIES.LIST")
        self.assertEqual(len(entries), 4)  # Party, Purchase, CGST, SGST

        amounts = [float(e.find("AMOUNT").text) for e in entries]
        # Sum of amounts in Tally format should equal 0 (Cr positive + Dr negative = 0)
        self.assertAlmostEqual(sum(amounts), 0.0, places=2)

    def test_generate_journal_voucher_xml(self):
        xml_str = self.bridge.generate_journal_voucher_xml(
            date_val="2026-10-15",
            voucher_number="JRN/001",
            debit_ledger="Audit Fees Expense",
            credit_ledger="CA Bhalani & Co",
            amount=50000.0,
            narration="Provision for statutory audit fees",
        )
        root = ET.fromstring(xml_str)
        voucher = root.find(".//VOUCHER")
        self.assertIsNotNone(voucher)
        self.assertEqual(voucher.attrib.get("VCHTYPE"), "Journal")

        entries = voucher.findall("ALLLEDGERENTRIES.LIST")
        self.assertEqual(len(entries), 2)
        amounts = [float(e.find("AMOUNT").text) for e in entries]
        self.assertAlmostEqual(sum(amounts), 0.0, places=2)


if __name__ == "__main__":
    unittest.main()
