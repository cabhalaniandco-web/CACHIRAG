#!/usr/bin/env python3
"""Behaviour tests for tally/GSTR2B_Portal_ImportButtons.tdl.

The functions in the add-on are executed straight out of the .tdl file by
tools/tdl_sim.py against a mock company, so these assertions describe what
TallyPrime is being asked to post: which rate-wise purchase ledger each GST
slab selects, that every generated voucher balances, how round off is applied,
and which rows are skipped instead of posted.

Run: python3 tools/test_gstr2b_import.py
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tdl_sim import (  # noqa: E402
    Company,
    Interpreter,
    ledger_entries,
    to_number,
    voucher_balance,
)

ADDON = Path(__file__).resolve().parent.parent / "tally" / "GSTR2B_Portal_ImportButtons.tdl"

CONFIG = {
    "GSTR2BVchTypeUDF": "Purchase",
    "GSTR2BDrNoteUDF": "Not Applicable",
    "GSTR2BCrNoteUDF": "Not Applicable",
    "GSTR2BPerWiseUDF": False,
    "GSTR2BExemptUDF": "PURCHASE EXEMPT",
    "GSTR2BPurc3UDF": "GST PURCHASE 3%",
    "GSTR2BPurc5UDF": "GST PURCHASE 5%",
    "GSTR2BPurc12UDF": "GST PURCHASE 12%",
    "GSTR2BPurc18UDF": "GST PURCHASE 18%",
    "GSTR2BPurc28UDF": "GST PURCHASE 28%",
    "GSTR2BCGSTUDF": "INPUT CGST",
    "GSTR2BSGSTUDF": "INPUT SGST",
    "GSTR2BIGSTUDF": "INPUT IGST",
    "GSTR2BCessUDF": "INPUT CESS",
    "GSTR2BUseROUDF": False,
    "GSTR2BROLedUDF": "ROUND OFF",
    "GSTR2BDryRunUDF": False,
    "GSTR2BMakePtyUDF": False,
    "GSTR2BPtyGrpUDF": "Not Applicable",
}

LEDGERS = [
    "PURCHASE EXEMPT",
    "GST PURCHASE 3%",
    "GST PURCHASE 5%",
    "GST PURCHASE 12%",
    "GST PURCHASE 18%",
    "GST PURCHASE 28%",
    "INPUT CGST",
    "INPUT SGST",
    "INPUT IGST",
    "INPUT CESS",
    "ROUND OFF",
    "Sanghavi ND HP Gas Agency",
]

INVOICE_DATE = datetime.date(2025, 12, 29)


class Checks:
    def __init__(self) -> None:
        self.passed = 0
        self.failures: list[str] = []

    def check(self, label: str, actual: object, expected: object) -> None:
        if actual == expected:
            self.passed += 1
        else:
            self.failures.append(f"{label}: expected {expected!r}, got {actual!r}")

    def check_in(self, label: str, needle: str, haystack: str) -> None:
        if needle in haystack:
            self.passed += 1
        else:
            self.failures.append(f"{label}: {needle!r} not found in {haystack!r}")

    def posted(self, label: str, company: Company) -> bool:
        """Guard the assertions that read a voucher that must have been created."""
        if company.vouchers:
            return True
        self.failures.append(f"{label}: no voucher was created, remaining checks skipped")
        return False


def new_company(**overrides: object) -> Company:
    company = Company(config=dict(CONFIG) | overrides)
    for name in LEDGERS:
        company.add_ledger(name)
    return company


def post(
    company: Company,
    *,
    party: str = "Sanghavi ND HP Gas Agency",
    doc_no: str = "GST/2526/1188",
    doc_date: datetime.date | str = INVOICE_DATE,
    taxable: float = 10000,
    cgst: float = 0,
    sgst: float = 0,
    igst: float = 0,
    cess: float = 0,
) -> str:
    interpreter = Interpreter(ADDON, company)
    return interpreter.call(
        "GSTR2BPostVoucher",
        ["Purchase", party, doc_no, doc_date, taxable, cgst, sgst, igst, cess],
    )


def entry_for(company: Company, ledger: str) -> dict[str, object] | None:
    for entry in ledger_entries(company.vouchers[-1]):
        if str(entry.get("LedgerName", "")).lower() == ledger.lower():
            return entry
    return None


def test_config_helpers(checks: Checks) -> None:
    interpreter = Interpreter(ADDON, new_company())
    checks.check(
        "'Not Applicable' is treated as unset",
        interpreter.call("GSTR2BCleanCfg", ["Not Applicable"]),
        "",
    )
    checks.check("blank config stays blank", interpreter.call("GSTR2BCleanCfg", [""]), "")
    checks.check(
        "a real selection is kept",
        interpreter.call("GSTR2BCleanCfg", ["GST PURCHASE 18%"]),
        "GST PURCHASE 18%",
    )
    checks.check(
        "an existing ledger is found",
        interpreter.call("GSTR2BLedgerExists", ["INPUT CGST"]),
        True,
    )
    checks.check(
        "a missing ledger is reported",
        interpreter.call("GSTR2BLedgerExists", ["NO SUCH LEDGER"]),
        False,
    )


def test_intrastate_invoice(checks: Checks) -> None:
    company = new_company()
    result = post(company, taxable=10000, cgst=900, sgst=900)

    checks.check("intrastate 18% posts", result, "OK")
    checks.check("one voucher is created", len(company.vouchers), 1)
    if not checks.posted("intrastate 18%", company):
        return

    voucher = company.vouchers[0]
    checks.check("voucher type comes from the config", voucher.values["VoucherTypeName"], "Purchase")
    checks.check("voucher number is the Doc No.", voucher.values["VoucherNumber"], "GST/2526/1188")
    checks.check("voucher date is the Doc Date", voucher.values["Date"], INVOICE_DATE)
    checks.check("the reference is the Doc No.", voucher.values["Reference"], "GST/2526/1188")
    checks.check(
        "the party is on the voucher",
        voucher.values["PartyLedgerName"],
        "Sanghavi ND HP Gas Agency",
    )
    checks.check("it posts in accounting voucher view", voucher.values["Persisted View"], "AccountingVoucherView")

    checks.check("four ledger entries", len(ledger_entries(voucher)), 4)
    checks.check("the voucher balances", voucher_balance(voucher), 0.0)
    checks.check(
        "the 18% purchase ledger is debited with the taxable value",
        to_number(entry_for(company, "GST PURCHASE 18%")["Amount"]),  # type: ignore[index]
        -10000.0,
    )
    checks.check("CGST is debited", to_number(entry_for(company, "INPUT CGST")["Amount"]), -900.0)  # type: ignore[index]
    checks.check("SGST is debited", to_number(entry_for(company, "INPUT SGST")["Amount"]), -900.0)  # type: ignore[index]
    checks.check("no IGST entry on an intrastate invoice", entry_for(company, "INPUT IGST"), None)
    checks.check(
        "the party is credited with the invoice total",
        to_number(entry_for(company, "Sanghavi ND HP Gas Agency")["Amount"]),  # type: ignore[index]
        11800.0,
    )
    checks.check(
        "the debit entries are marked deemed positive",
        entry_for(company, "GST PURCHASE 18%")["IsDeemedPositive"],  # type: ignore[index]
        True,
    )
    checks.check(
        "the party credit is not deemed positive",
        entry_for(company, "Sanghavi ND HP Gas Agency")["IsDeemedPositive"],  # type: ignore[index]
        False,
    )


def test_interstate_invoice(checks: Checks) -> None:
    company = new_company()
    checks.check("interstate 5% posts", post(company, taxable=20000, igst=1000), "OK")
    if not checks.posted("interstate 5%", company):
        return
    checks.check(
        "the 5% purchase ledger is picked from the IGST rate",
        to_number(entry_for(company, "GST PURCHASE 5%")["Amount"]),  # type: ignore[index]
        -20000.0,
    )
    checks.check("IGST is debited", to_number(entry_for(company, "INPUT IGST")["Amount"]), -1000.0)  # type: ignore[index]
    checks.check("no CGST on an interstate invoice", entry_for(company, "INPUT CGST"), None)
    checks.check("the interstate voucher balances", voucher_balance(company.vouchers[0]), 0.0)


def test_rate_slabs(checks: Checks) -> None:
    slabs = [
        (3, "GST PURCHASE 3%"),
        (5, "GST PURCHASE 5%"),
        (12, "GST PURCHASE 12%"),
        (18, "GST PURCHASE 18%"),
        (28, "GST PURCHASE 28%"),
    ]
    for rate, expected_ledger in slabs:
        taxable = 10000.0
        tax = taxable * rate / 100
        company = new_company()
        post(company, taxable=taxable, cgst=tax / 2, sgst=tax / 2)
        if not checks.posted(f"{rate}% intrastate", company):
            continue
        entry = ledger_entries(company.vouchers[0])[0]
        checks.check(f"{rate}% intrastate maps to its ledger", entry["LedgerName"], expected_ledger)

        company = new_company()
        post(company, taxable=taxable, igst=tax)
        if not checks.posted(f"{rate}% interstate", company):
            continue
        entry = ledger_entries(company.vouchers[0])[0]
        checks.check(f"{rate}% interstate maps to its ledger", entry["LedgerName"], expected_ledger)

    # Paise-level rounding on the portal figures must not fall out of the slab.
    company = new_company()
    post(company, taxable=1234.56, cgst=111.11, sgst=111.11)
    if not checks.posted("18% with rounded paise", company):
        return
    checks.check(
        "an 18% invoice with rounded paise stays on the 18% ledger",
        ledger_entries(company.vouchers[0])[0]["LedgerName"],
        "GST PURCHASE 18%",
    )


def test_exempt_invoice(checks: Checks) -> None:
    company = new_company()
    checks.check("a tax free invoice posts", post(company, taxable=5000), "OK")
    if not checks.posted("tax free invoice", company):
        return
    checks.check(
        "it uses the exempted purchase ledger",
        ledger_entries(company.vouchers[0])[0]["LedgerName"],
        "PURCHASE EXEMPT",
    )
    checks.check("it has only two entries", len(ledger_entries(company.vouchers[0])), 2)
    checks.check("the exempt voucher balances", voucher_balance(company.vouchers[0]), 0.0)


def test_cess(checks: Checks) -> None:
    company = new_company()
    checks.check("an invoice with CESS posts", post(company, taxable=10000, igst=2800, cess=400), "OK")
    if not checks.posted("invoice with CESS", company):
        return
    checks.check("CESS is debited", to_number(entry_for(company, "INPUT CESS")["Amount"]), -400.0)  # type: ignore[index]
    checks.check(
        "the party credit includes CESS",
        to_number(entry_for(company, "Sanghavi ND HP Gas Agency")["Amount"]),  # type: ignore[index]
        13200.0,
    )
    checks.check("the CESS voucher balances", voucher_balance(company.vouchers[0]), 0.0)


def test_round_off(checks: Checks) -> None:
    company = new_company(GSTR2BUseROUDF=True)
    checks.check(
        "an invoice with paise posts with round off on",
        post(company, taxable=9999.66, cgst=899.97, sgst=899.97),
        "OK",
    )
    if not checks.posted("invoice with round off", company):
        return
    party = to_number(entry_for(company, "Sanghavi ND HP Gas Agency")["Amount"])  # type: ignore[index]
    round_off = to_number(entry_for(company, "ROUND OFF")["Amount"])  # type: ignore[index]
    checks.check("the party is credited with a whole rupee total", round(party, 2), 11800.0)
    checks.check("the difference goes to the round off ledger", round(round_off, 2), -0.4)
    checks.check("the rounded voucher balances", voucher_balance(company.vouchers[0]), 0.0)

    company = new_company()
    post(company, taxable=9999.66, cgst=899.97, sgst=899.97)
    if not checks.posted("invoice without round off", company):
        return
    checks.check("no round off entry when the option is off", entry_for(company, "ROUND OFF"), None)
    checks.check(
        "the party gets the exact total when round off is off",
        round(to_number(entry_for(company, "Sanghavi ND HP Gas Agency")["Amount"]), 2),  # type: ignore[index]
        11799.6,
    )


def test_bill_wise_party(checks: Checks) -> None:
    company = new_company()
    company.add_ledger("BILLWISE SUPPLIER", IsBillWiseOn=True)
    post(company, party="BILLWISE SUPPLIER", taxable=10000, cgst=900, sgst=900)
    if not checks.posted("bill-wise party", company):
        return
    entry = entry_for(company, "BILLWISE SUPPLIER")
    allocations = entry["_children"].get("BillAllocations", []) if entry else []  # type: ignore[union-attr]
    checks.check("a bill-wise party gets one bill allocation", len(allocations), 1)
    if allocations:
        checks.check("the bill is the Doc No.", allocations[0].values["Name"], "GST/2526/1188")
        checks.check("it is a new reference", allocations[0].values["BillType"], "NewRef")
        checks.check("the bill carries the invoice total", to_number(allocations[0].values["Amount"]), 11800.0)

    company = new_company()
    post(company, taxable=10000, cgst=900, sgst=900)
    if not checks.posted("party without bill-wise", company):
        return
    entry = entry_for(company, "Sanghavi ND HP Gas Agency")
    checks.check(
        "a party without bill-wise gets no allocation",
        entry["_children"].get("BillAllocations", []) if entry else None,  # type: ignore[union-attr]
        [],
    )


def test_missing_party(checks: Checks) -> None:
    company = new_company()
    result = post(company, party="BRAND NEW SUPPLIER", taxable=10000, cgst=900, sgst=900)
    checks.check_in("a missing party is skipped by default", "SKIP: ledger 'BRAND NEW SUPPLIER'", result)
    checks.check("nothing is posted for a missing party", len(company.vouchers), 0)

    company = new_company(GSTR2BMakePtyUDF=True)
    result = post(company, party="BRAND NEW SUPPLIER", taxable=10000, cgst=900, sgst=900)
    checks.check("the party is created on request", result, "OK")
    created = company.ledger("BRAND NEW SUPPLIER")
    checks.check("the new party falls back to Sundry Creditors", created["Parent"] if created else None, "Sundry Creditors")
    checks.check("the voucher is posted after creating the party", len(company.vouchers), 1)

    company = new_company(GSTR2BMakePtyUDF=True, GSTR2BPtyGrpUDF="Creditors GST")
    post(company, party="BRAND NEW SUPPLIER", taxable=10000, cgst=900, sgst=900)
    created = company.ledger("BRAND NEW SUPPLIER")
    checks.check(
        "the configured group is used when set",
        created["Parent"] if created else None,
        "Creditors GST",
    )


def test_skipped_rows(checks: Checks) -> None:
    cases = [
        ("a blank party", {"party": ""}, "SKIP: party name is blank"),
        ("a blank Doc No.", {"doc_no": ""}, "SKIP: Doc No. is blank"),
        ("a blank Doc Date", {"doc_date": ""}, "SKIP: Doc Date is blank"),
        ("an all-zero row", {"taxable": 0}, "SKIP: no taxable value or tax"),
        (
            "a credit note row",
            {"taxable": -10000, "cgst": -900, "sgst": -900},
            "SKIP: negative amounts (credit/debit note)",
        ),
    ]
    for label, overrides, expected in cases:
        company = new_company()
        result = post(company, **overrides)  # type: ignore[arg-type]
        checks.check_in(f"{label} is skipped", expected, result)
        checks.check(f"nothing is posted for {label}", len(company.vouchers), 0)

    company = new_company(GSTR2BPurc18UDF="Not Applicable")
    result = post(company, taxable=10000, cgst=900, sgst=900)
    checks.check_in("an unmapped slab is skipped", "SKIP: no purchase ledger mapped for 18% GST", result)

    company = new_company(GSTR2BPurc18UDF="DELETED LEDGER")
    result = post(company, taxable=10000, cgst=900, sgst=900)
    checks.check_in("a deleted purchase ledger is skipped", "SKIP: purchase ledger 'DELETED LEDGER'", result)

    company = new_company(GSTR2BIGSTUDF="Not Applicable")
    result = post(company, taxable=10000, igst=1800)
    checks.check_in("IGST without a mapped ledger is skipped", "SKIP: IGST on the invoice", result)

    company = new_company(GSTR2BCessUDF="Not Applicable")
    result = post(company, taxable=10000, igst=1800, cess=100)
    checks.check_in("CESS without a mapped ledger is skipped", "SKIP: CESS on the invoice", result)


def test_row_reading(checks: Checks) -> None:
    """The STEP 5 fallback chains must read a row whatever method it exposes."""
    interpreter = Interpreter(ADDON, new_company())

    first_choice = {
        "PartyLedgerName": "Sanghavi ND HP Gas Agency",
        "DocumentNo": "GST/2526/1188",
        "DocumentDate": INVOICE_DATE,
        "TaxableAmount": 15388,
        "CGSTAmount": 1384.92,
        "SGSTAmount": 1384.92,
    }
    later_choice = {
        "TradeName": "Sanghavi ND HP Gas Agency",
        "InvoiceNo": "GST/2526/1188",
        "InvoiceDate": INVOICE_DATE,
        "AssessableValue": 15388,
        "IntegratedTaxAmount": 2769.84,
        "CessTaxAmount": 100,
    }

    for label, row in (("the first candidate", first_choice), ("a later candidate", later_choice)):
        read = {
            name: interpreter.evaluate(interpreter.formulas[f"gstr2brow{name.lower()}"], {}, row)
            for name in ("Party", "DocNo", "DocDate", "Taxable", "CGST", "SGST", "IGST", "Cess")
        }
        checks.check(f"the party is read from {label}", read["Party"], "Sanghavi ND HP Gas Agency")
        checks.check(f"the doc no. is read from {label}", read["DocNo"], "GST/2526/1188")
        checks.check(f"the doc date is read from {label}", read["DocDate"], INVOICE_DATE)
        checks.check(f"the taxable value is read from {label}", read["Taxable"], 15388)

    checks.check("a row with no matching method reads as blank", interpreter.evaluate(
        interpreter.formulas["gstr2browparty"], {}, {"SomethingElse": "x"}
    ), None)


def test_import_button(checks: Checks) -> None:
    """End to end: the button's function over a selection of portal rows."""
    rows = [
        {
            "PartyLedgerName": "Sanghavi ND HP Gas Agency",
            "DocumentNo": "GST/2526/1188",
            "DocumentDate": INVOICE_DATE,
            "TaxableAmount": 10000,
            "CGSTAmount": 900,
            "SGSTAmount": 900,
        },
        {
            "PartyLedgerName": "Sanghavi ND HP Gas Agency",
            "DocumentNo": "GST/2526/1189",
            "DocumentDate": INVOICE_DATE,
            "TaxableAmount": 20000,
            "IGSTAmount": 1000,
        },
        {
            "PartyLedgerName": "UNKNOWN SUPPLIER",
            "DocumentNo": "GST/2526/1190",
            "DocumentDate": INVOICE_DATE,
            "TaxableAmount": 1000,
            "IGSTAmount": 50,
        },
    ]

    company = new_company()
    interpreter = Interpreter(ADDON, company)
    interpreter.collections["gstr2bselectedrows"] = []
    interpreter.call("GSTR2B Import Selected Vouchers", [])
    checks.check_in("an empty selection is reported", "No rows selected", company.messages[-1][1])
    checks.check("an empty selection posts nothing", len(company.vouchers), 0)

    company = new_company(GSTR2BVchTypeUDF="Not Applicable")
    interpreter = Interpreter(ADDON, company)
    interpreter.collections["gstr2bselectedrows"] = rows
    interpreter.call("GSTR2B Import Selected Vouchers", [])
    checks.check_in(
        "an unconfigured voucher type is reported",
        "Please set the Purchase Voucher Type first",
        company.messages[-1][1],
    )
    checks.check("nothing is posted without a voucher type", len(company.vouchers), 0)

    company = new_company(GSTR2BDryRunUDF=True)
    interpreter = Interpreter(ADDON, company)
    interpreter.collections["gstr2bselectedrows"] = rows
    interpreter.call("GSTR2B Import Selected Vouchers", [])
    preview = company.messages[-1][1]
    checks.check_in("a dry run says nothing was created", "DRY RUN - no voucher was created", preview)
    checks.check_in("a dry run lists the row values", "GST/2526/1188", preview)
    checks.check_in("a dry run shows the taxable value", "10000", preview)
    checks.check("a dry run posts nothing", len(company.vouchers), 0)

    company = new_company()
    interpreter = Interpreter(ADDON, company)
    interpreter.collections["gstr2bselectedrows"] = rows
    interpreter.call("GSTR2B Import Selected Vouchers", [])
    summary = company.messages[-1][1]
    checks.check("the two valid rows are posted", len(company.vouchers), 2)
    checks.check_in("the summary counts what was created", "2 purchase voucher(s) created", summary)
    checks.check_in("the summary counts what was skipped", "1 row(s) skipped", summary)
    checks.check_in("the summary names the skipped invoice", "GST/2526/1190", summary)
    checks.check("every posted voucher balances", [voucher_balance(v) for v in company.vouchers], [0.0, 0.0])
    checks.check(
        "each voucher keeps its own invoice number",
        [voucher.values["VoucherNumber"] for voucher in company.vouchers],
        ["GST/2526/1188", "GST/2526/1189"],
    )
    return summary


def main() -> int:
    checks = Checks()
    test_config_helpers(checks)
    test_intrastate_invoice(checks)
    test_interstate_invoice(checks)
    test_rate_slabs(checks)
    test_exempt_invoice(checks)
    test_cess(checks)
    test_round_off(checks)
    test_bill_wise_party(checks)
    test_missing_party(checks)
    test_skipped_rows(checks)
    test_row_reading(checks)
    summary = test_import_button(checks)

    print(f"{checks.passed} check(s) passed, {len(checks.failures)} failed")
    if checks.failures:
        print()
        for failure in checks.failures:
            print(f"FAIL: {failure}")
        return 1

    print("\nImport summary produced by the add-on for the sample selection:")
    print(f"  {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
