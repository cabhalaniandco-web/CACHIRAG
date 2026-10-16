#!/usr/bin/env python3
"""
Tally XML Bridge & Voucher Generator
Generates Tally-compliant XML envelopes to import Masters and Vouchers
into TallyPrime / Tally.ERP 9 via direct XML file import or HTTP (port 9000).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error


class TallyXMLBridge:
    def __init__(self, company_name: Optional[str] = None):
        self.company_name = company_name

    @staticmethod
    def format_tally_date(d: date | str) -> str:
        """Formats date as YYYYMMDD required by Tally XML."""
        if isinstance(d, date):
            return d.strftime("%Y%m%d")
        # If string like YYYY-MM-DD or DD/MM/YYYY
        clean = d.replace("-", "").replace("/", "")
        if len(clean) == 8:
            # Assuming YYYYMMDD or DDMMYYYY
            if int(clean[:4]) > 1900:  # YYYYMMDD
                return clean
            else:  # DDMMYYYY -> YYYYMMDD
                return clean[4:] + clean[2:4] + clean[:2]
        return clean

    def create_envelope(self) -> ET.Element:
        envelope = ET.Element("ENVELOPE")
        header = ET.SubElement(envelope, "HEADER")
        tally_request = ET.SubElement(header, "TALLYREQUEST")
        tally_request.text = "Import Data"
        return envelope

    def generate_purchase_voucher_xml(
        self,
        date_val: date | str,
        voucher_number: str,
        party_name: str,
        purchase_ledger: str,
        taxable_amount: float,
        cgst_amount: float = 0.0,
        sgst_amount: float = 0.0,
        igst_amount: float = 0.0,
        cgst_ledger: str = "CGST",
        sgst_ledger: str = "SGST",
        igst_ledger: str = "IGST",
        narration: str = "",
    ) -> str:
        """Generates Tally XML for a Purchase Voucher with GST taxes."""
        envelope = self.create_envelope()
        body = ET.SubElement(envelope, "BODY")
        import_data = ET.SubElement(body, "IMPORTDATA")
        req_desc = ET.SubElement(import_data, "REQUESTDESC")
        report_name = ET.SubElement(req_desc, "REPORTNAME")
        report_name.text = "Vouchers"

        if self.company_name:
            static_vars = ET.SubElement(req_desc, "STATICVARIABLES")
            sv_company = ET.SubElement(static_vars, "SVCURRENTCOMPANY")
            sv_company.text = self.company_name

        req_data = ET.SubElement(import_data, "REQUESTDATA")
        tally_msg = ET.SubElement(req_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})

        voucher = ET.SubElement(
            tally_msg,
            "VOUCHER",
            {"VCHTYPE": "Purchase", "ACTION": "Create", "OBJVIEW": "Accounting Voucher View"},
        )

        dt_str = self.format_tally_date(date_val)
        ET.SubElement(voucher, "DATE").text = dt_str
        ET.SubElement(voucher, "EFFECTIVEDATE").text = dt_str
        ET.SubElement(voucher, "VOUCHERTYPENAME").text = "Purchase"
        ET.SubElement(voucher, "VOUCHERNUMBER").text = voucher_number
        ET.SubElement(voucher, "REFERENCE").text = voucher_number
        ET.SubElement(voucher, "PARTYLEDGERNAME").text = party_name
        ET.SubElement(voucher, "NARRATION").text = narration or f"GSTR-2B Purchase Inv {voucher_number}"
        ET.SubElement(voucher, "PERSISTEDVIEW").text = "Accounting Voucher View"

        total_amount = taxable_amount + cgst_amount + sgst_amount + igst_amount

        # 1. Supplier / Party (Credit Entry -> Positive in Tally's amount convention for Cr on purchase)
        cr_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(cr_entry, "LEDGERNAME").text = party_name
        ET.SubElement(cr_entry, "ISDEEMEDPOSITIVE").text = "No"
        ET.SubElement(cr_entry, "AMOUNT").text = f"{total_amount:.2f}"

        # 2. Purchase Ledger (Debit Entry -> Negative in Tally)
        dr_purc = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(dr_purc, "LEDGERNAME").text = purchase_ledger
        ET.SubElement(dr_purc, "ISDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(dr_purc, "AMOUNT").text = f"{-taxable_amount:.2f}"

        # 3. CGST (Debit Entry)
        if cgst_amount > 0:
            dr_cgst = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
            ET.SubElement(dr_cgst, "LEDGERNAME").text = cgst_ledger
            ET.SubElement(dr_cgst, "ISDEEMEDPOSITIVE").text = "Yes"
            ET.SubElement(dr_cgst, "AMOUNT").text = f"{-cgst_amount:.2f}"

        # 4. SGST (Debit Entry)
        if sgst_amount > 0:
            dr_sgst = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
            ET.SubElement(dr_sgst, "LEDGERNAME").text = sgst_ledger
            ET.SubElement(dr_sgst, "ISDEEMEDPOSITIVE").text = "Yes"
            ET.SubElement(dr_sgst, "AMOUNT").text = f"{-sgst_amount:.2f}"

        # 5. IGST (Debit Entry)
        if igst_amount > 0:
            dr_igst = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
            ET.SubElement(dr_igst, "LEDGERNAME").text = igst_ledger
            ET.SubElement(dr_igst, "ISDEEMEDPOSITIVE").text = "Yes"
            ET.SubElement(dr_igst, "AMOUNT").text = f"{-igst_amount:.2f}"

        return ET.tostring(envelope, encoding="utf-8", xml_declaration=True).decode("utf-8")

    def generate_journal_voucher_xml(
        self,
        date_val: date | str,
        voucher_number: str,
        debit_ledger: str,
        credit_ledger: str,
        amount: float,
        narration: str = "",
    ) -> str:
        """Generates Tally XML for a simple Journal Voucher."""
        envelope = self.create_envelope()
        body = ET.SubElement(envelope, "BODY")
        import_data = ET.SubElement(body, "IMPORTDATA")
        req_desc = ET.SubElement(import_data, "REQUESTDESC")
        ET.SubElement(req_desc, "REPORTNAME").text = "Vouchers"

        req_data = ET.SubElement(import_data, "REQUESTDATA")
        tally_msg = ET.SubElement(req_data, "TALLYMESSAGE")
        voucher = ET.SubElement(
            tally_msg,
            "VOUCHER",
            {"VCHTYPE": "Journal", "ACTION": "Create"},
        )

        dt_str = self.format_tally_date(date_val)
        ET.SubElement(voucher, "DATE").text = dt_str
        ET.SubElement(voucher, "VOUCHERTYPENAME").text = "Journal"
        ET.SubElement(voucher, "VOUCHERNUMBER").text = voucher_number
        ET.SubElement(voucher, "NARRATION").text = narration

        # Debit Entry (Negative amount in Tally)
        dr_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(dr_entry, "LEDGERNAME").text = debit_ledger
        ET.SubElement(dr_entry, "ISDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(dr_entry, "AMOUNT").text = f"{-amount:.2f}"

        # Credit Entry (Positive amount in Tally)
        cr_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(cr_entry, "LEDGERNAME").text = credit_ledger
        ET.SubElement(cr_entry, "ISDEEMEDPOSITIVE").text = "No"
        ET.SubElement(cr_entry, "AMOUNT").text = f"{amount:.2f}"

        return ET.tostring(envelope, encoding="utf-8", xml_declaration=True).decode("utf-8")

    def post_to_tally_http(self, xml_payload: str, tally_url: str = "http://localhost:9000") -> str:
        """Sends XML payload to running Tally instance on HTTP port."""
        req = urllib.request.Request(
            tally_url,
            data=xml_payload.encode("utf-8"),
            headers={"Content-Type": "text/xml;charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.read().decode("utf-8")
        except urllib.error.URLError as e:
            return f"Error connecting to Tally at {tally_url}: {e}"


if __name__ == "__main__":
    bridge = TallyXMLBridge(company_name="Sample CA Client Ltd")
    xml_output = bridge.generate_purchase_voucher_xml(
        date_val="2026-10-15",
        voucher_number="INV/2026/001",
        party_name="M/S Tech Suppliers Pvt Ltd",
        purchase_ledger="GST Purchase 18%",
        taxable_amount=10000.0,
        cgst_amount=900.0,
        sgst_amount=900.0,
        narration="Test Purchase Voucher from GSTR-2B",
    )
    print("Sample Generated Tally XML Voucher:")
    print(xml_output)
