# Tally Definition Language (TDL) Developer Reference Guide

## 1. What is TDL?

**TDL (Tally Definition Language)** is the action-driven, object-based language used to customize, extend, and build interfaces, reports, forms, and business logic in **TallyPrime** and **Tally.ERP 9**.

---

## 2. Core Hierarchy & Component Architecture

TDL follows a strict UI containment hierarchy:

$$\text{Report} \longrightarrow \text{Form} \longrightarrow \text{Part} \longrightarrow \text{Line} \longrightarrow \text{Field}$$

```text
[Report: MyReport]
   └── [Form: MyForm]
          └── [Part: MyPart]
                 └── [Line: MyLine]
                        └── [Field: MyField]
```

### Hierarchy Breakdown:
1. **Report**: Top-level interface entity. Manages data context (`Object: Company`, `Object: Ledger`, etc.) and titles.
2. **Form**: Defines the window dimensions, frames, and buttons (`Parts`, `Width`, `Height`, `Add: Button`).
3. **Part**: Defines layout sections (vertical/horizontal lines, headers, body, footers).
4. **Line**: A single row of input or display items (`Fields: Prompt, Value`).
5. **Field**: The atomic UI element (types: `Name Field`, `Amount Field`, `Logical Field`, `Date Field`, `Number Field`).

---

## 3. Modification vs. Creation Syntax

- **Creating a New Definition**:
  ```tdl
  [Report: MyNewReport]
      Form : MyNewForm
  ```
- **Modifying / Overriding an Existing Default Definition (`#`)**:
  ```tdl
  [#Menu: Gateway of Tally]
      Add : Key Item : "My Custom Tool" : M : Display : MyCustomReport

  [#Form: Voucher]
      Add : Button : MyVchHelperBtn
  ```

---

## 4. User Defined Fields (UDF)

Tally allows developers to attach custom data fields to default or custom objects:

```tdl
[System: UDF]
    ;; Range 20001 - 59999 is standard developer range
    MyVoucherTagUDF : String : 20001
    MyRateUDF       : Rate   : 20002
    MyFlagUDF       : Logical: 20003
```

To bind a UI field to a UDF:
```tdl
[Field: MyField]
    Use     : Name Field
    Storage : MyVoucherTagUDF
    Set as  : $MyVoucherTagUDF
```

---

## 5. Collections, Methods & Formulas

- **Collection**: Represents a set of objects (Ledgers, VoucherTypes, StockItems, or selected report rows):
  ```tdl
  [Collection: SundryCreditors]
      Type       : Ledger
      Child Of   : "Sundry Creditors"
      Belongs To : Yes
      Fetch      : Name, ClosingBalance, PartyGSTIN
  ```

- **Report Selected Rows**:
  ```tdl
  [Collection: MySelectedRows]
      Data Source : Report : Selected
      Client Only : Yes
  ```

- **System Formulas**:
  ```tdl
  [System: Formula]
      IsDebitNoteVT : $Parent = "Debit Note" OR $Name = "Debit Note"
  ```

- **Accessing Object Methods (`$` / `$$`)**:
  - `$LedgerName`: Field on current object
  - `$$IsEmpty:$FieldName`: Internal TDL function
  - `$$String:$DocumentDate`: String casting
  - `$$NumItems:MyCollection`: Collection size

---

## 6. Procedural Functions in TDL

Functions use numbered statement execution (`01 : ...`, `02 : ...`):

```tdl
[Function: CreateCustomVoucher]
    Parameter : pParty : String
    Parameter : pAmt   : Amount
    Variable  : vStatus: Logical

    01 : NEW OBJECT : Voucher
    02 : SET VALUE  : VoucherTypeName : "Journal"
    03 : SET VALUE  : Date            : $$CurrentDate

    ;; Insert Ledger Entry
    04 : INSERT COLLECTION OBJECT : AllLedgerEntries
    05 : SET VALUE : LedgerName : ##pParty
    06 : SET VALUE : Amount     : ##pAmt
    07 : SET TARGET : ..

    08 : CREATE TARGET
    09 : SET : vStatus : $$LastResult
    10 : RETURN : ##vStatus
```

---

## 7. Developer Mode (`/DevMode`) in TallyPrime

To inspect any default Report, Form, Part, Line, or Field name inside Tally:

1. Right-click TallyPrime desktop shortcut $\rightarrow$ **Properties**.
2. In **Target**, append ` /DevMode`:
   ```cmd
   "C:\Program Files\TallyPrime\tally.exe" /DevMode
   ```
3. Open TallyPrime and navigate to any report.
4. Hover over elements to see live tooltips with:
   - Report Name
   - Form Name
   - Line / Field / Table definitions
   - Object Methods & Data Source

---

## 8. Common TDL Errors & How to Fix Them

| Error Code | Meaning | Solution |
| :--- | :--- | :--- |
| `T0008` | `Could not find default definition of [#Form: ...]` | The form name is incorrect or changed in this Tally release. Verify with `/DevMode`. |
| `T0020` | `Bad formula / syntax error` | Check collection names with spaces (remove spaces or quote names). |
| `T0001` | `Duplicate definition found` | Ensure unique symbol names across loaded TDLs. |
| `T0014` | `Type mismatch` | Check variable casting (e.g. use `$$String:##numVar` for text concatenation). |
