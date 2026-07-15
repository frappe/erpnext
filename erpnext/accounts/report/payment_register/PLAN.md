# Payment Register Report

> Status: implemented and tested (10/10 tests passing on `test_site`). This file records the design as built, including one correction made during testing (see "Deviations from initial design" below).

## Context

[GitHub issue #47847](https://github.com/frappe/erpnext/issues/47847) requests a centralized "Payment Register" report. Today, auditors and finance teams reviewing payment activity must switch between two separate list views — **Payment Entry** (which covers "Pay" and "Receive" transactions) and **Journal Entry** (which also carries payment-related transactions via voucher types like Bank Entry, Cash Entry, and Contra Entry) — applying scattered filters on each. There's no single place to see all payments for auditing and reconciliation.

This plan adds a new Script Report, **"Payment Register"**, sourced from **`GL Entry`** — the fully normalized ledger table that every accounting voucher already posts to — filtered down to entries against accounts of type **Bank** or **Cash**. This is a deliberate architectural choice made after reconsidering an initial design that queried Payment Entry and Journal Entry separately and hand-normalized rows: sourcing from GL Entry instead means the report automatically gets one row per account leg per voucher (no manual "which child row is the bank leg" logic), correct per-leg amounts in both account and company currency, and — since GL Entry's `voucher_subtype` field is already populated from Payment Entry's `payment_type` (Pay/Receive/Internal Transfer) and Journal Entry's `voucher_type` (Bank Entry/Cash Entry/Contra Entry/etc.) — it naturally captures every kind of payment-relevant transaction without doctype-specific branching. It also has the side effect of surfacing **any** voucher type that posts to a Bank/Cash account (POS Invoice instant payments, Purchase Invoice "is paid" entries, Loan disbursement/repayment, etc.), which was confirmed with the user as the desired broader scope — a more complete audit trail of actual cash movement than the issue's literal two-doctype framing.

## Files

```
erpnext/accounts/report/payment_register/
├── __init__.py
├── payment_register.json
├── payment_register.py
├── payment_register.js
└── test_payment_register.py
```

No existing files were modified.

## 1. `payment_register.json`

Script Report record:
- `report_type: "Script Report"`, `module: "Accounts"`, `is_standard: "Yes"`
- `ref_doctype: "Payment Entry"` (primary doctype for permission attachment/UX; the `.py` queries GL Entry directly)
- `roles: [{"role": "Accounts Manager"}, {"role": "Accounts User"}, {"role": "Auditor"}]` — matches Payment Entry/Journal Entry's own doctype permissions and the existing `Payment Ledger` report's role precedent
- `add_total_row: 1`
- empty `columns`/`filters` arrays (Script Report — defined in `.py`/`.js`)

## 2. Query design (`payment_register.py`) — GL Entry as the source

`execute(filters)` → `get_columns()` + `get_data(filters)`, where `get_data` builds and runs one Query Builder query against `GL Entry`, joined to `Account` (for the Bank/Cash type filter) and left-joined to `Payment Entry` and `Journal Entry` (only to backfill the handful of fields that live on those doctypes but not on GL Entry — see below). No separate PE/JE fetches, no Python-level concatenation.

```python
gle = frappe.qb.DocType("GL Entry")
acc = frappe.qb.DocType("Account")
pe = frappe.qb.DocType("Payment Entry")
je = frappe.qb.DocType("Journal Entry")

query = (
    frappe.qb.from_(gle)
    .inner_join(acc).on(gle.account == acc.name)
    .left_join(pe).on((gle.voucher_type == "Payment Entry") & (gle.voucher_no == pe.name))
    .left_join(je).on((gle.voucher_type == "Journal Entry") & (gle.voucher_no == je.name))
    .select(
        gle.name, gle.posting_date, gle.company,
        gle.account, gle.account_currency,
        Coalesce(gle.party_type, pe.party_type).as_("party_type"),
        Coalesce(gle.party, pe.party).as_("party"),
        gle.debit, gle.credit,
        gle.debit_in_account_currency, gle.credit_in_account_currency,
        gle.against, gle.against_voucher_type, gle.against_voucher,
        gle.voucher_type, gle.voucher_no, gle.voucher_subtype,
        gle.cost_center, gle.project, gle.remarks,
        Coalesce(pe.mode_of_payment, je.mode_of_payment).as_("mode_of_payment"),
        Coalesce(pe.reference_no, je.cheque_no).as_("reference_no"),
        Coalesce(pe.reference_date, je.cheque_date).as_("reference_date"),
        Coalesce(pe.clearance_date, je.clearance_date).as_("clearance_date"),
    )
    .where(gle.is_cancelled == 0)
    .where(gle.is_opening == "No")
    .where(acc.account_type.isin(["Bank", "Cash"]))
)
```

Filters applied on top: `gle.company == filters.company`, `gle.posting_date[from_date:to_date]`, `party_type`/`party` (matched against **both** `gle.*` and `pe.*` — see deviation below), `gle.cost_center`, `gle.account.isin(filters.account)` (further narrowing within Bank/Cash accounts), `gle.voucher_type.isin(filters.voucher_type)` (optional), and reference_no/mode_of_payment filters applied against the pre-coalesce `pe.*`/`je.*` fields directly (e.g. `(pe.reference_no.like(...) | je.cheque_no.like(...))`) since filtering on an aliased `Coalesce` expression isn't reliable in pypika. Standard accounting-dimension filters (`filters.get(dimension)`, from `get_accounting_dimensions()`) are applied directly against `gle.<dimension>` fields — this improves on a PE/JE-query design, since custom accounting dimensions are added directly to GL Entry itself, so dimension filtering works uniformly for every voucher type instead of only at the Payment Entry parent level.

**Why the LEFT JOINs to Payment Entry/Journal Entry specifically**: `mode_of_payment`, `reference_no`/`cheque_no`, `reference_date`/`cheque_date`, and `clearance_date` don't exist on GL Entry — they're specific to how Payment Entry and Journal Entry record bank reconciliation details. These four columns are blank for GL Entry rows sourced from other doctypes (POS Invoice, Purchase Invoice, Loan Entry, etc.) — documented as an acceptable known limitation rather than attempting per-doctype joins for every possible voucher type.

**`is_cancelled == 0`**: this schema version keeps cancelled GL Entries with an `is_cancelled` flag rather than deleting them, so this filter is required (confirmed by reading `gl_entry.json`).

**`is_opening == "No"`**: excludes opening-balance journal entries, which aren't real payment transactions.

## 3. Deviation from initial design: Party Type / Party needed a Payment Entry fallback

The original plan sourced `party_type`/`party` straight from `GL Entry`. **Testing showed this is wrong for Payment Entry rows.** `PaymentEntryGLComposer.add_bank_gl_entries` (in `payment_entry/services/gl_composer.py`) builds the Bank/Cash-leg GL Entry **without** `party_type`/`party` — those fields are only set on the AR/AP-leg GL Entry (`add_party_gl_entries`), which this report never selects (it's not a Bank/Cash account). Since the report is restricted to Bank/Cash rows, every standard Payment Entry row would have had a blank Party column and the `party`/`party_type` filters would have silently returned zero rows for legitimate matches.

**Fix**: select/filter `Coalesce(gle.party_type, pe.party_type)` and `Coalesce(gle.party, pe.party)` instead of the bare `gle.*` fields. Payment Entry always carries its own party at the parent-document level regardless of which leg GL Entry records, so this backfills correctly. This does **not** help Journal Entry rows — `Journal Entry` has no parent-level party field (party lives only on the `Journal Entry Account` child row), so a JE's Bank/Cash leg still shows blank Party unless that specific child row happens to carry one directly. Documented as a known limitation alongside the other JE-sourced blank-field cases.

## 4. Columns (`payment_register.py`)

- **Posting Date**
- **Voucher Type** (Link → DocType) — from `gle.voucher_type`, e.g. "Payment Entry", "Journal Entry", "POS Invoice", "Purchase Invoice"
- **Voucher No** (Dynamic Link, options=`voucher_type`) — from `gle.voucher_no`
- **Voucher Subtype** (Data) — from `gle.voucher_subtype` directly: "Pay"/"Receive"/"Internal Transfer" for Payment Entry rows, "Bank Entry"/"Cash Entry"/"Contra Entry"/etc. for Journal Entry rows, blank/doctype-dependent for others
- **Direction** (Data: "Pay"/"Receive") — derived uniformly from sign, in Python: `"Receive"` if `debit_in_account_currency` is set, else `"Pay"`. Applies identically regardless of source doctype — computed once, generically, rather than per-doctype
- **Party Type**, **Party** (Dynamic Link) — see deviation above
- **Account** (Link → Account) — the Bank/Cash account leg this row represents (`gle.account`)
- **Against** (Data) — `gle.against`, a human-readable summary of the counter account(s)/party
- **Against Voucher Type** (Link → DocType), **Against Voucher No** (Dynamic Link) — what the payment settles
- **Amount** (Currency, options=`account_currency`) — `debit_in_account_currency` if set else `credit_in_account_currency`
- **Currency** (`account_currency`)
- **Amount (Company Currency)** (Currency) — `debit` if set else `credit`, for cross-currency total-row summing
- **Mode of Payment**, **Reference No**, **Reference Date**, **Clearance Date** — from the LEFT JOIN coalesce (blank for non-PE/JE voucher types)
- **Cost Center**, **Project**, **Company**, **Remarks**

## 5. Filters (`payment_register.js`)

- **Company** (Link, required, default = user default company)
- **From Date** / **To Date** (Date, both required; default = last 1 month → today)
- **Party Type** (Link → Party Type) + **Party** (MultiSelectList, options keyed off `party_type`)
- **Account** (MultiSelectList → Account, link-query scoped to `account_type in (Bank, Cash)`)
- **Voucher Type** (MultiSelectList → DocType, default empty = all)
- **Mode of Payment** (Link) — applies only where populated (PE/JE-sourced rows)
- **Reference No** (Data) — applies only where populated (PE/JE-sourced rows)
- **Cost Center** (Link)
- Accounting dimensions appended via `erpnext.utils.add_dimensions("Payment Register", 8)`

## 6. Permissions

Roles: `Accounts Manager`, `Accounts User`, `Auditor` — confirmed against both Payment Entry's and Journal Entry's own doctype permissions and the Payment Ledger report's role precedent. Verified on `test_site`: `frappe.get_doc("Report", "Payment Register").roles` returns exactly these three.

## 7. Edge cases

| Edge case | Handling |
|---|---|
| Internal Transfer PE / Contra JE (both legs touch Bank/Cash accounts) | Naturally yields 2 GL Entry rows, one per account — each independently shows correct Direction/Amount for its own leg. No special-casing needed. |
| Multi-currency | `Amount`/`Currency` reflect the account-currency leg; `Amount (Company Currency)` is always comparable/summable. |
| Cancelled vouchers | Excluded via `is_cancelled == 0`. |
| Opening balance entries | Excluded via `is_opening == "No"`. |
| Non-PE/JE voucher types (POS Invoice, Purchase Invoice instant payment, Loan Entry, etc.) | Fully included per confirmed broader scope; `Mode of Payment`/`Reference No`/`Reference Date`/`Clearance Date` are blank for these — documented limitation. |
| Payment Entry Party Type/Party | Backfilled via `Coalesce(gle.*, pe.*)` — see Deviation section above. |
| Journal Entry Party Type/Party | Still blank unless the specific bank-leg child row carries a party directly — documented limitation, not fixed (JE has no parent-level party field to fall back to). |
| Accounting dimensions | Filtered directly against `GL Entry` fields — works uniformly for every voucher type. |

## 8. Testing (`test_payment_register.py`) — all 10 passing

1. `test_payment_entry_pay_and_receive` — Pay-type and Receive-type Payment Entry surface with correct amount/account/direction/voucher_subtype, including reference_no.
2. `test_internal_transfer_surfaces_two_rows` — Internal Transfer PE surfaces as 2 rows (one per leg), correct direction each.
3. `test_bank_entry_journal_entry_surfaces_one_row` — Bank Entry JE (1 bank leg + 1 non-bank leg) surfaces as exactly 1 row.
4. `test_contra_entry_journal_entry_surfaces_two_rows` — Contra Entry JE surfaces as 2 rows.
5. `test_plain_journal_entry_gated_by_account_type_not_voucher_type` — a plain "Journal Entry" that doesn't touch Bank/Cash is excluded; one that does (bank interest) is included — confirms account_type, not voucher_type label, gates inclusion.
6. `test_purchase_invoice_instant_payment_surfaces_with_blank_reference` — Purchase Invoice `is_paid` instant payment surfaces, with `mode_of_payment`/`reference_no` blank.
7. `test_cancelled_and_opening_entries_excluded` — cancelled JE and an opening-balance JE are both excluded.
8. `test_filters_narrow_results` — party type/party, account, voucher_type, and reference_no filters each correctly narrow results (cost_center exercised too).
9. `test_date_range_excludes_out_of_range_postings` — date range filter excludes/includes correctly.
10. `test_multi_currency_payment_entry` — multi-currency PE's amount/currency/base_amount are correct.

Run with: `bench --site test_site run-tests --module erpnext.accounts.report.payment_register.test_payment_register`

## 9. Manual verification performed

- `bench --site test_site migrate` — confirmed the Report record and its 3 roles sync correctly into the DB.
- `test_site` had zero pre-existing GL Entries, so a small set of real submitted documents (a Receive PE, a Pay PE, a Contra Entry JE) was created directly on `test_site`, `execute()` was run against them, and all rows/directions/amounts/party info were confirmed correct (including the Coalesce fix surfacing Customer/Supplier party on the PE rows). Those documents were cancelled afterward to leave the site clean; the cancelled rows remaining in GL Entry but correctly excluded by the report is itself further live confirmation of the `is_cancelled` filter.
- Did not do a literal browser/desk-UI screenshot check — no browser automation tool was available in this environment, and the JS filters just wire into the same `execute()` already verified above.
