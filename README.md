# CA CHIRAG — Tally TDL Suite & Automation Toolkit

A suite of modular **Tally Definition Language (TDL)** add-ons, audit utilities, and XML integration bridges designed for Chartered Accountants, tax consultants, and finance professionals using **TallyPrime** and **Tally.ERP 9**.

---

## 📦 What's Inside

### 1. TDL Add-Ons (`/tally`)
- **`CA_Tally_Suite.tdl`**: Master bundle file containing all modules.
- **`GSTR2B_Portal_ImportButtons.tdl`**: Custom GSTR-2B portal reconciliation buttons (`Import Configuration` via `Alt+C` and `Import Selected Vouchers` via `Alt+V`).
- **`CA_Audit_Utilities.tdl`**: Negative cash balance alert, party GSTIN/PAN live display in voucher entry, invoice previous balance display, and auto round-off helper.
- **`Custom_Gateway_Menu.tdl`**: Direct shortcut menu for CA audit and statutory reports from the Gateway of Tally.
- **`Voucher_Auto_Post.tdl`**: Reusable TDL functions for programmatic voucher creation and master validation.

### 2. Developer Tools (`/tools`)
- **`tdl_validator.py`**: Syntax and structural linter for `.tdl` files.
- **`tally_xml_bridge.py`**: Python engine for generating Tally XML envelopes and posting vouchers directly via HTTP (port `9000`).

### 3. Developer Guide & Documentation
- [TDL Developer Reference Guide](tally/TDL_DEVELOPER_GUIDE.md): Syntax, UI hierarchy (`Report > Form > Part > Line > Field`), collections, UDFs, and `/DevMode` debugging.
- [Tally Module Readme](tally/README.md): Step-by-step loading and configuration guide for TallyPrime.

---

## 🚀 Quick Start

### Loading into TallyPrime
1. Open **TallyPrime** $\rightarrow$ press **`F1` (Help)** $\rightarrow$ **TDL & Add-On** $\rightarrow$ press **`F4` (Manage Local TDLs)**.
2. Set **`Load selected TDL files on startup`** to **`Yes`**.
3. Add the file path to `tally/CA_Tally_Suite.tdl` (or individual `.tdl` files).
4. Save with **`Ctrl+A`** and restart TallyPrime.

### Validating TDLs locally
```bash
python3 tools/tdl_validator.py tally
```

### Running Automated Tests
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```
