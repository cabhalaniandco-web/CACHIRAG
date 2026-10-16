# GSTR-2B "Available only on Portal" — custom import buttons (TDL)

`GSTR2B_Portal_ImportButtons.tdl` adds two buttons to the right-hand button bar
of the **GSTR-2B Reconciliation** report in TallyPrime:

- **Import Configuration** (`Alt+C`) — opens a small screen to set the purchase
  voucher type, the default purchase ledger, and whether to auto-create missing
  masters.
- **Import Selected Vouchers** (`Alt+V`) — creates purchase vouchers from the
  rows you select (Spacebar) in the *Available only on Portal* section.

Path in Tally: `Gateway of Tally → Display More Reports → Statutory Reports →
GST Reports → GSTR-2B Reconciliation → Available only on Portal`.

## 1. Form name

STEP 1 in the `.tdl` is already set to **`GSTR Recon DrillDown`**, the internal
form of the GSTR-2B Reconciliation "Available Only on Portal" voucher list
(confirmed via Developer Mode). Because this DrillDown form is shared by the
reconciliation voucher lists, the two buttons will also appear on the other
drill-down voucher screens (e.g. mismatches, available only in books). If a
future TallyPrime release renames the form and you get
`T0008: Could not find the default TDL definition of Form: GSTR Recon DrillDown`,
re-confirm the name with Developer Mode as below and update STEP 1.

### How to re-confirm the Form name (Developer Mode)

TDL attaches buttons to a report by its internal **Form name**, which Tally does
not publish and which can change between releases. Confirm it on your build using
Developer Mode:

1. Close TallyPrime.
2. Right-click the TallyPrime shortcut → **Properties**.
3. In **Target**, append ` /DevMode`, e.g.
   `"C:\Program Files\TallyPrime\tally.exe" /DevMode`
4. Apply and open TallyPrime.
5. Open the GSTR-2B Reconciliation → *Available only on Portal* view.
6. Hover the mouse over an **empty area** (not on a field). The tooltip shows the
   current Report/Form name.
7. Put that name in the `[#Form: ...]` line marked **STEP 1** in the `.tdl` file
   and remove the leading `;;` from those three lines to activate them.

> **Important:** `[#Form: <name>]` *modifies an existing* form. If `<name>` is not
> a real form, Tally aborts loading with `T0008: Could not find the default TDL
> definition of Form: <name>`. That's why **STEP 1 ships commented out** — the
> file loads with no error, but the buttons only appear after you fill in the
> real name and uncomment those three lines.

## 2. Load the TDL

TallyPrime: `F1 (Help) → TDL & Add-On → F4 (Manage Local TDLs)` → set
*Load selected TDL files on startup* = **Yes**, add the full path to
`GSTR2B_Portal_ImportButtons.tdl`, accept, and restart TallyPrime.

## 3. Verify

1. Open the GSTR-2B Reconciliation → *Available only on Portal* view.
2. Confirm **Import Configuration** and **Import Selected Vouchers** appear in the
   right button bar (and respond to `Alt+C` / `Alt+V`).
3. Click **Import Configuration** (`Alt+C`), set at least the Purchase Voucher
   Type and the rate-wise purchase ledgers plus CGST/SGST/IGST ledgers, save
   (`Ctrl+A`).
4. Select one or more rows with the **Spacebar**, click **Import Selected
   Vouchers** (`Alt+V`). A confirmation box previews the first 5 rows; choose
   **Yes** to post.
5. A summary reports how many vouchers were created and how many rows were
   skipped. Verify a created voucher in Day Book.

## 4. How the importer posts vouchers

For each selected row, STEP 5 of the `.tdl`:

1. Reads party, document number/date, taxable value, and CGST/SGST/IGST/CESS
   amounts from the row.
2. Computes the effective GST % (total GST ÷ taxable value) and picks the
   rate-wise purchase ledger: below 0.5% → Purchase Exempted Ledger; ~3%,
   ~5%, ~12%, ~18%, ~28% → the matching configured ledger. Band cut-offs sit
   midway between slabs so small rounding differences in the portal data still
   match.
3. Creates a voucher of the configured Purchase Voucher Type:
   Cr Party (invoice total), Dr rate-wise purchase ledger (taxable value),
   Dr IGST **or** Dr CGST + SGST, Dr CESS when present, and a Round Off
   entry for the rounding difference when *Use Round Off* is enabled.
4. Skips (and counts in the summary) rows with a missing party, a
   non-positive taxable value, a GST % that matches no configured ledger, or
   tax amounts whose GST ledger is not configured — a skipped row never posts
   a half-built voucher.

### Row method names are build-specific

The row values are read with the methods `$PartyLedgerName`, `$DocumentNo`,
`$DocumentDate`, `$TaxableAmount`, `$CGSTAmount`, `$SGSTAmount`, `$IGSTAmount`,
and `$CessAmount`. These are internal names of the GSTR-2B reconciliation
report and can differ between TallyPrime releases. If the confirmation preview
shows blank values, hover the matching column in Developer Mode to read the
real field/method name and update the `SET : v... : $...` lines at the top of
the WALK in STEP 5.

## Testing note

TDL executes only inside Tally (proprietary Windows software), which cannot run
on this Linux environment, so this add-on was authored and reviewed for correct
TDL structure but not executed here. Use the steps in section 3 to verify it in
your TallyPrime installation.
