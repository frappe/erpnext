# Period Closing Voucher

At the end of every year or (quarterly or maybe even monthly), after completing auditing, you can close your books of accounts. This means that you make all your special entries like:

  * Depreciation
  * Change in value of Assets
  * Defer taxes and liabilities
  * Update bad debts

etc. and book your Profit or Loss.

By doing this, your balance in your Income and Expense Accounts become zero. You start a new Fiscal Year (or period) with a balanced Balance Sheet and fresh Profit and Loss account.

In ERPNext after making all the special entries via Journal Entry for the current fiscal year, you should set all your Income and Expense accounts to zero via:

> Accounts > Tools > Period Closing Voucher

**Posting Date** will be when this entry should be executed. If your Fiscal Year ends on 31st December, then that date should be selected as Posting Date in the Period Closing Voucher.

**Transaction Date** will be Period Closing Voucher's creation date.

**Closing Fiscal Year** will be an year for which you are closing your financial statement.

<img class="screenshot" alt="Period Closing Voucher" src="{{docs_base_url}}/assets/img/accounts/period-closing-voucher.png">

This voucher will transfer Profit or Loss (availed from P&L statment) to Closing Account Head. You should select a liability account like Reserves and Surplus, or Capital Fund account as Closing Account.

The Period Closing Voucher will make accounting entries (GL Entry) making all your Income and Expense Accounts zero and transferring Profit/Loss balance to the Closing Account.

<div class=well>If accounting entries are made in a closing fiscal year, even after Period Closing Voucher was created for that Fiscal Year, you should create another Period Closing Voucher. Later voucher will only transfer the pending P&L balance into Closing Account Head.</div>

{next}
