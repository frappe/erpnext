Accounts module contains masters and transactions to manage a traditional
double entry accounting system.

Accounting heads are called "Accounts" and they can be groups in a tree like
"Chart of Accounts"

Entries are:

- Journal Entries
- Sales Invoice (Itemised)
- Purchase Invoice (Itemised)

All accounting entries are stored in the `General Ledger`

## Payment Ledger
Transactions on Receivable and Payable Account types will also be stored in `Payment Ledger`. This is so that payment reconciliation process only requires update on this ledger.

### Key Fields
| Field                | Description                      |
|----------------------|----------------------------------|
| `account_type`       | Receivable/Payable               |
| `account`            | Accounting head                  |
| `party`              | Party Name                       |
| `voucher_no`         | Voucher No                       |
| `against_voucher_no` | Linked voucher(secondary effect) |
| `amount`             | can be +ve/-ve                   |

### Design
`debit` and `credit` have been replaced with `account_type` and `amount`. `against_voucher_no` is populated for all entries. So, outstanding amount can be calculated by summing up amount only using `against_voucher_no`.

Ex:
1. Consider an invoice for ₹100 and a partial payment of ₹80 against that invoice. Payment Ledger will have following entries.

| voucher_no | against_voucher_no | amount |
|------------|--------------------|--------|
| SINV-01    | SINV-01            | 100    |
| PAY-01     | SINV-01            | -80    |


2. Reconcile a Credit Note against an invoice using a Journal Entry

An invoice for ₹100 partially reconciled against a credit of ₹70 using a Journal Entry. Payment Ledger will have the following entries.

| voucher_no | against_voucher_no | amount |
|------------|--------------------|--------|
| SINV-01    | SINV-01            | 100    |
|            |                    |        |
| CR-NOTE-01 | CR-NOTE-01         | -70    |
|            |                    |        |
| JE-01      | CR-NOTE-01         | +70    |
| JE-01      | SINV-01            | -70    |
