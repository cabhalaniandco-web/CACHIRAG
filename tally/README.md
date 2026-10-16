# Tally Definition Language (TDL) Suite for TallyPrime

This directory contains modular, production-ready TDL (Tally Definition Language) add-ons designed for Chartered Accountants, tax consultants, and accounting teams using **TallyPrime** or **Tally.ERP 9**.

---

## 📁 Included TDL Files

| File | Description | Key Shortcuts |
| :--- | :--- | :--- |
| **`CA_Tally_Suite.tdl`** | **Master Bundle File** — Includes all modules below with a single load entry. | — |
| **`GSTR2B_Portal_ImportButtons.tdl`** | Adds custom **Import Configuration** and **Import Selected Vouchers** buttons to GSTR-2B Reconciliation. | `Alt+C` (Config), `Alt+V` (Import) |
| **`CA_Audit_Utilities.tdl`** | Negative cash balance warning, party GSTIN/PAN auto-display in voucher entry, auto round-off helper, and previous balance on invoices. | On screen / Validation |
| **`Custom_Gateway_Menu.tdl`** | Adds a dedicated **"CA Audit & GST Tools"** menu directly onto the Gateway of Tally. | `A` on Gateway of Tally |
| **`Voucher_Auto_Post.tdl`** | Reusable programmatic TDL functions for automated Purchase, Journal, and Ledger creation. | Function calls |

---

## 🚀 How to Load TDLs into TallyPrime

### Method 1: Load the Master Suite (Recommended)

1. Open **TallyPrime**.
2. Press **`F1` (Help)** $\rightarrow$ **TDL & Add-On** (or press `Ctrl+Alt+T`).
3. Press **`F4` (Manage Local TDLs)**.
4. Set **`Load selected TDL files on startup`** to **`Yes`**.
5. Under **File Path / File Name**, provide the full path to `CA_Tally_Suite.tdl` (e.g. `C:\TallyTDL\CA_Tally_Suite.tdl`).
6. Press **`Ctrl+A`** to save and restart TallyPrime.

### Method 2: Load Individual Modules

Follow the same steps above, but select the specific `.tdl` file (e.g. `GSTR2B_Portal_ImportButtons.tdl`).

---

## 🔍 Module Details

### 1. GSTR-2B Portal Import & Reconciliation (`GSTR2B_Portal_ImportButtons.tdl`)

Path in Tally:
`Gateway of Tally → Display More Reports (D) → Statutory Reports (S) → GST Reports (G) → GSTR-2B Reconciliation (2) → Available Only on Portal`

- **Import Configuration (`Alt+C`)**:
  - Lets you configure Purchase Voucher Type, Debit/Credit Note Voucher Type, Percent-Wise Tax Entry.
  - Configure rate-wise purchase accounts (3%, 5%, 12%, 18%, 28%, Exempted).
  - Configure single GST duty accounts (CGST, SGST, IGST, CESS) and Round-Off.
  - Stored permanently in **Company UDFs** (20001–20016), persisting across sessions.
- **Import Selected Vouchers (`Alt+V`)**:
  - Select one or more rows in the portal list using the **Spacebar**.
  - Click or press `Alt+V` to preview selected invoices and trigger import.

### 2. CA Audit Utilities (`CA_Audit_Utilities.tdl`)

- **Negative Cash Warning**: Alerts the user when recording a Payment / Expense voucher if the selected Cash ledger closing balance goes negative.
- **Party GSTIN & PAN Display**: Automatically shows the party's registered GSTIN (in Blue) and PAN (in Dark Green) right inside the voucher entry screen when a party ledger is selected.
- **Auto Round-Off Helper**: Calculates paise fractions to round voucher totals to the nearest rupee.
- **Previous Balance on Invoices**: Prints the customer's previous outstanding closing balance on the invoice printout.

### 3. Custom Gateway Menu (`Custom_Gateway_Menu.tdl`)

Adds a top-level menu item on the **Gateway of Tally**:
- `A` $\rightarrow$ **CA Audit & GST Tools**:
  - `R` $\rightarrow$ GSTR-2B Reconciliation
  - `G` $\rightarrow$ GSTR-3B Summary Report
  - `1` $\rightarrow$ GSTR-1 Return View
  - `C` $\rightarrow$ Cash & Bank Summary / Audit
  - `T` $\rightarrow$ Trial Balance
  - `O` $\rightarrow$ Outstanding Receivables
  - `I` $\rightarrow$ GSTR-2B Import Configuration

---

## 🛠️ Python Development Tools

Located in `/workspace/tools/`:

- **`tdl_validator.py`**: Lints and validates `.tdl` files for syntax, bracket pairing, and section definitions.
  ```bash
  python3 tools/tdl_validator.py tally
  ```
- **`tally_xml_bridge.py`**: Generates Tally-compatible XML vouchers (Purchase, Journal) and can send them directly to Tally's HTTP port (default `9000`).
  ```bash
  python3 tools/tally_xml_bridge.py
  ```
