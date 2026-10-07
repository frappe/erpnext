# Shareholding in Accounting (Phase 1)

The working shareholding workflow lives in ERPNext's **Accounts** module and
appears under Share Management in the Accounting workspace.

Create a Company, Shareholder, and company-specific Share Class. Submitting a
Share Transaction creates any required Share Folio and immutable Share Ledger
Entries. The Shareholder form shows its current positions directly from these
ledger entries. Share Ledger and Equity Position reports show history and
holdings for a selected date; they do not maintain a second editable balance.

Supported transactions are Issue, Transfer, Buyback, Retirement, and Reissue.
Numbered ranges and whole-quantity holdings are supported. Company-specific
Equity Accounting Settings choose default accounts. Transactions affecting the
company create a draft Journal Entry; the General Ledger updates only when
that Journal Entry is submitted. An ordinary shareholder-to-shareholder
Transfer creates no company accounting entry.

Phase 2 workflows (corporate actions, dividends, awards, convertibles,
settlements, and depository comparisons) are outside this active module. If
Clearing accounting is selected, finance records the actual payment with a
separate Journal Entry; Phase 1 does not automate that payment or bank matching.

ERPNext's existing Shareholder, Share Type, Share Transfer, and Share Balance
records are part of Accounts. The migration patch maps existing shareholder
names and folio numbers into the new identity and Share Folio structure where
possible. It captures the old identifiers in a staging table before the DocType
schema changes so they remain auditable. It does not invent tax IDs,
share-class rights, face values, or ledger movements for old transfers. The
older Share Transfer and Share Balance forms remain available for historical
review until a separate data conversion has been approved and verified.
