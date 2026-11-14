# Cash Basis Financial Reports

ERPNext provides two Cash Basis financial reports that complement the standard accrual-based reports:

- **Cash Basis Profit and Loss Statement**
- **Cash Basis Balance Sheet**

These reports recognise income and expenses only when cash is actually received or paid, rather than when invoices are raised.

---

## What is Cash Basis Accounting?

Under **accrual accounting** (the ERPNext default), revenue is recognised when a Sales Invoice is raised and expenses when a Purchase Invoice is posted — regardless of whether cash has changed hands.

Under **cash basis accounting**, revenue is recognised only when the customer pays, and expenses only when the supplier is paid. Unpaid invoices are excluded from the Profit & Loss Statement entirely.

| Situation | Accrual P&L | Cash Basis P&L |
|---|---|---|
| Invoice raised, not yet paid | Revenue recognised | No revenue |
| Invoice 60% paid | Full revenue | 60% of revenue |
| Invoice fully paid | Full revenue | Full revenue |

Cash basis accounting is commonly required for small businesses, sole traders, and in certain regulatory contexts.

---

## Cash Basis Profit and Loss Statement

**Path:** Accounts > Reports > Cash Basis Profit and Loss Statement

### How It Works

Income and Expense accounts are populated based on **when payment is received or made**, not when the invoice is posted.

1. **Payment Entry settlements** — When a Payment Entry is reconciled against a Sales or Purchase Invoice, the report creates a virtual GL entry dated at the payment date. The amount recognised is proportional to the payment:

   ```
   Recognised Amount = Invoice Line Amount × (Payment Allocated / Invoice Grand Total)
   ```

2. **Journal Entry settlements** — When a Journal Entry settles an invoice (via `against_voucher_type` / `against_voucher`), the same proportional recognition applies.

3. **Non-invoice transactions** — Journal Entries that are not linked to invoices (e.g. bank charges, opening entries) are passed through unchanged.

4. **Period Closing Vouchers** are excluded.

### Partial Payment Example

| Event | Date | Accrual P&L | Cash Basis P&L |
|---|---|---|---|
| Sales Invoice ₹10,000 raised | Jan 5 | ₹10,000 revenue in Jan | — |
| Payment ₹6,000 received | Feb 12 | — | ₹6,000 revenue in Feb |
| Payment ₹4,000 received | Mar 3 | — | ₹4,000 revenue in Mar |

### Supported Filters

| Filter | Description |
|---|---|
| Company | The company to report on |
| Fiscal Year / Date Range | Filter basis for the period |
| From / To Fiscal Year | Multi-year range |
| Period Start / End Date | Specific date range |
| Periodicity | Monthly, Quarterly, Half-Yearly, Yearly |
| Accumulated Values | Show running totals across periods |
| Cost Centre | Restrict to a cost centre hierarchy |
| Project | Restrict to a project |
| Finance Book | Filter by finance book |
| Include Default Book Entries | Include entries without a finance book |
| Show Zero Values | Show accounts with no activity |
| Selected View | Report / Growth / Margin view |

---

## Cash Basis Balance Sheet

**Path:** Accounts > Reports > Cash Basis Balance Sheet

### How It Works

The Cash Basis Balance Sheet adjusts Asset, Liability, and Equity account balances to reflect the cash-settled position.

**The key adjustment:** Accounts Receivable and Accounts Payable are scaled by the settlement ratio as of the report date.

- For a **Sales Invoice** fully collected: the AR entry is scaled to zero (cash has been received; AR disappears from assets).
- For a **Sales Invoice** 60% collected: AR is scaled to 40% of the original amount (only the uncollected portion remains as a receivable in the accrual sense, but under cash basis this isn't an asset yet — so the full AR is removed from the balance sheet).
- For an **unpaid Sales Invoice**: the invoice GL entries (both AR and Revenue) are zeroed out entirely.

This ensures the **Balance Sheet equation (Assets = Liabilities + Equity)** holds automatically at all times.

### Mathematical Guarantee

Consider a ₹100 Sales Invoice that is 60% collected:

| Account | Accrual | Cash Basis Adjustment | Cash Basis |
|---|---|---|---|
| Accounts Receivable | +₹100 | ×0.6 (60% uncollected scaled out) | +₹60 → net ₹0 after PE |
| Revenue | +₹100 | ×0.6 | +₹60 |
| Cash / Bank | +₹60 (from PE) | unchanged | +₹60 |

Net result: Assets (Cash ₹60) = Equity (Revenue ₹60). Equation holds.

### Supported Filters

Same as the Cash Basis P&L (see above). The Balance Sheet does not include the **Margin** view.

---

## Coexistence with Accrual Reports

The Cash Basis reports are entirely separate from the standard **Profit and Loss Statement** and **Balance Sheet** reports. They:

- Read from the same GL Entry table but apply different aggregation logic
- Do not modify any existing data
- Can be run simultaneously with accrual reports for comparison

---

## Accessing the Reports

Navigate to:

- **Accounts > Reports > Cash Basis Profit and Loss Statement**
- **Accounts > Reports > Cash Basis Balance Sheet**

Or use the search bar and type "Cash Basis".

---

## Limitations

- **Multi-currency exchange gains/losses** on payments are not separately attributed to periods in the cash basis view.
- **Opening balance entries** (`is_opening = Yes`) are not settlement-ratio adjusted.
- Reports may be slower on very large databases due to the settlement ratio calculation joining across Payment Entry, Journal Entry, and GL Entry tables.

---

## Related

- [Profit and Loss Statement](/erpnext/profit-and-loss-statement)
- [Balance Sheet](/erpnext/balance-sheet)
- [Accounting Reports](/erpnext/accounting-reports)
- [Payment Entry](/erpnext/payment-entry)
