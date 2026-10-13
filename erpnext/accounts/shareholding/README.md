# Shareholding in Accounting

Create a Company, Shareholder, and reusable Share Class. A Share Class defines
ordinary or preference shares and records voting and dividend terms. These
terms do not automate votes or dividend payments in V1.

Share Transaction supports Issue, Transfer, Buyback, Retirement, and Reissue
using numbered share ranges. Submitting creates the company membership
(Share Folio), then writes immutable Share Ledger Entries. A Transfer writes
both sides of the ownership movement. Cancellation writes reversal entries
and keeps the original history.

Accounting transaction reversals follow ERPNext's immutable ledger setting.
With immutable accounting enabled, cancellation takes effect on the cancellation
date. Otherwise, ownership reversals use the original posting date to match
the General Ledger. Ordinary Transfer reversals retain their cancellation date.

Share Ledger and Equity Position show history and holdings for a selected
date. The Shareholder form also shows a read-only Current Share Balance child
table. Transactions rebuild this table from the ledger. Users cannot change
its quantities by saving the Shareholder. A user must have access to every
company linked to a Shareholder to read that global record.
Document sharing is disabled for Shareholders because it bypasses company
restrictions. A patch removes existing Shareholder document shares. Use roles
and company permissions to grant access instead.

Equity Accounting Settings stores the default accounts for each company.
Issue, Buyback, Retirement, and Reissue prepare a draft Journal Entry.
Finance reviews its settlement account and submits it to update the General
Ledger. Equity amounts and accounts must match the transaction. An ordinary
Transfer creates no company journal. Journals are never submitted automatically.

The Accounting workspace includes shareholding counts, shortcuts, and reports.
All DocTypes and reports remain in Accounts. V1 does not include a separate
Equity module, corporate actions, or automated bank reconciliation.

## Existing data

Share Type and Share Transfer remain readable. New records, edits, cancellation,
and journal generation through those legacy DocTypes are blocked.

Pre-migration patches snapshot legacy identities and Share Balance rows.
Post-migration patches create folios and replay submitted Share Transfers.
Map each old Share Type using the Legacy Share Type field on Share Class.
The backfill validates complete share ranges and compares ending ownership
against the saved balances. It never reposts historical accounting or guesses
face values, tax IDs, or share rights.

Incomplete mappings or mismatched balances block reports and new transactions for affected
companies. After correcting the data and mappings, run:

```sh
bench --site <site> execute erpnext.patches.v17_0.backfill_legacy_share_transfers.run_backfill
```

Legacy Purchase removes shares from circulation. It is not mapped to a treasury
Buyback. Cancelled legacy transfers are not replayed because their cancellation
dates are unknown. Historical face values remain unknown until independently
verified. Unreconciled history requires review and an approved opening balance.
