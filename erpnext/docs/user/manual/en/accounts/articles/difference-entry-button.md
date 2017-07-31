# Difference Entry Button

#Difference Entry

As per accounting standards, debit in a accounting entry must be equal to credit. If not, system does allow submission of accounting transaction, thereby stops ledger posting. In ERPNext, on saving accounting entry, system validates if debit and credit is tallying.

<img alt="Debit Credit Not Equal" class="screenshot" src="/docs/assets/img/articles/difference-entry-1.png">

To have entry balanced, you should one more row, select another account, and update different amount in it. Or you can add difference amount in one of the Account's row itself.

On clicking 'Make Difference Entry' button, new Row will be added under Journal Entry Accounts table, with difference amount. You can edit that row to select appropriate Account.

<img alt="Debit Credit Not Equal" class="screenshot" src="/docs/assets/img/articles/difference-entry-2.gif">

On selecting account under new row, debit and credit an entry will be tallying, and you should be able to submit Journal Entri correctly.

<!-- markdown -->