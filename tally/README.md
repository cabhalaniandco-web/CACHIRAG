# GSTR-2B "Available Only on Portal" — import buttons (TDL)

`GSTR2B_Portal_ImportButtons.tdl` is a TallyPrime add-on that puts two buttons in
the right-hand button bar of the GSTR-2B Reconciliation voucher list:

- **Import Configuration** (`Alt+C`) — the mapping screen: voucher types,
  rate-wise purchase ledgers, single CGST/SGST/IGST/CESS ledgers, round off, and
  how to treat a party that does not exist yet. Saved on the company with
  `Ctrl+A`, so it survives a restart.
- **Import Selected Vouchers** (`Alt+V`) — creates one purchase voucher per row
  selected with the Spacebar.

Path in Tally: `Gateway of Tally → Display More Reports → Statutory Reports →
GST Reports → GSTR-2B Reconciliation → Available Only on Portal`.

## What a row becomes

For every selected row the add-on posts, in the voucher type chosen in the
configuration:

| Entry | Ledger | Amount |
| --- | --- | --- |
| Dr | the rate-wise purchase ledger for the invoice's GST slab | Taxable Value |
| Dr | CGST and SGST, or IGST | the tax on the row |
| Dr | CESS, when the row carries it | CESS |
| Dr/Cr | the round off ledger, when round off is enabled | the paise difference |
| Cr | the party from *Particulars* | invoice total |

Voucher No. and the voucher's reference come from **Doc No.**, the voucher date
from **Doc Date**. The GST slab is derived from the tax on the row
(`tax ÷ taxable value`) and matched to the 3 / 5 / 12 / 18 / 28% bands, so paise
rounding on the portal figures cannot push an invoice out of its slab. A row
with a taxable value and no tax uses the **Purchase Exempted Ledger**. Parties
with bill-wise details enabled get a `New Reference` for the Doc No.

Only purchase invoices are posted. A row with negative amounts (a credit or
debit note on the portal) is skipped: it needs the Dr./Cr. Note voucher type,
which the configuration already stores but the importer does not use yet.

A row is **skipped, never half-posted**. The summary message names every skipped
row with its reason — a blank column, a ledger that is not mapped, a slab with
no ledger, or a party that does not exist while *Create Missing Party Ledger* is
`No`.

## Install

TallyPrime: `F1 (Help) → TDL & Add-On → F4 (Manage Local TDLs)` → set *Load
selected TDL files on startup* = **Yes**, add the full path to
`GSTR2B_Portal_ImportButtons.tdl`, accept, and restart TallyPrime.

## First run: dry run first

1. Open the GSTR-2B Reconciliation → *Available Only on Portal* view and confirm
   **Import Configuration** and **Import Selected Vouchers** are in the right
   button bar.
2. `Alt+C`, fill in the mapping, set **Dry Run (Preview Only)** = `Yes`, save with
   `Ctrl+A`. Anything that does not apply can be left as **Not Applicable** — the
   add-on keeps that choice and never substitutes a default.
3. Select a couple of rows with the Spacebar and press `Alt+V`. The preview lists
   what was read from each row: Party, Doc No, Doc Date, Taxable, CGST, SGST,
   IGST, CESS.
4. If every column is right, set **Dry Run** = `No` and import. The summary
   reports how many vouchers were created and why any row was skipped.
5. Check the result in `Display More Reports → Account Books → Purchase Register`.

### If a column reads blank in the dry run

The drill-down rows are internal Tally objects and their method names are not
published, so **STEP 5** of the `.tdl` reads each value through a chain of
candidate methods and takes the first that returns something. A column that
comes out blank means none of the candidates matched this TallyPrime build. Find
the real name with Developer Mode and add it to that chain:

1. Close TallyPrime, right-click the shortcut → **Properties**, and append
   ` /DevMode` to **Target**, e.g. `"C:\Program Files\TallyPrime\tally.exe" /DevMode`.
2. Reopen the *Available Only on Portal* list and hover the column. The tooltip
   shows the field name behind it.
3. Add the corresponding method to the front of the matching `GSTR2BRow...`
   formula in STEP 5.

## Form name

STEP 1 attaches the buttons to the form **`GSTR Recon DrillDown`**, confirmed via
Developer Mode on the "Available Only on Portal" voucher list. That DrillDown
form is shared by the reconciliation voucher lists, so the buttons also appear on
the other drill-down voucher screens.

`[#Form: <name>]` *modifies an existing* form, so if a future release renames it
Tally aborts the load with `T0008: Could not find the default TDL definition of
Form: GSTR Recon DrillDown`. Re-confirm the name the same way — hover an **empty
area** of the list, not a field — and update STEP 1.

## Checks that run outside Tally

TDL only executes inside Tally, which is Windows-only proprietary software and
cannot run in this repository's CI. Two checks therefore run against the `.tdl`
source itself:

```bash
python3 tools/test_tdl_lint.py        # structural checks + the linter's own tests
python3 tools/test_gstr2b_import.py   # executes the add-on's functions
```

`tools/tdl_lint.py` resolves every Part/Line/Field/Button/Form/Report/Collection/
Function reference, every `Storage` target and `$...UDF` method, every
`@@formula`, and checks that function step numbers ascend and that IF/ELSE/ENDIF,
WALK, and INSERT COLLECTION OBJECT are balanced — the mistakes Tally reports as
a load abort or a "Bad formula".

`tools/tdl_sim.py` parses the real `.tdl` and runs its functions against an
in-memory stand-in for Tally's object model, so the accounting behaviour is
asserted directly from the shipped file: slab-to-ledger mapping, debits equal to
credits, round off, bill allocation, and every skip reason.

Neither replaces running the add-on in TallyPrime. Use the dry run above for
that.
