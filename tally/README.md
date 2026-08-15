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

## 1. Find the exact Form name (required, one-time)

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
3. Click **Import Configuration**, set a Default Purchase Ledger, save (`Ctrl+A`).
4. Select one or more rows with the **Spacebar**, click **Import Selected
   Vouchers**, and confirm the summary message reports the correct count and your
   configured ledger/voucher type.

## 4. Finish the importer

The button + configuration + selection wiring is complete and testable. The
per-row **voucher creation** block in **STEP 5** of the `.tdl` is a documented
skeleton: the source field names of the GSTR-2B rows (supplier GSTIN, invoice
number, date, taxable value, IGST/CGST/SGST, …) are internal and build-specific.
Hover each column in Developer Mode to read its field name, then complete the
`SET VALUE ...` lines marked `TODO`.

## Testing note

TDL executes only inside Tally (proprietary Windows software), which cannot run
on this Linux environment, so this add-on was authored and reviewed for correct
TDL structure but not executed here. Use the steps in section 3 to verify it in
your TallyPrime installation.
