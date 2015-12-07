<h1>How to Nullify Balance From Temporary Accounts? </h1>

There are two separate temporary accounts in Chart of Accounts. One is Temporary Account (Assets) and other one is Temporary Account (Liabilities). These accounts are available under Application of Funds and Source of Funds in Chart of Accounts respectively.

These temporary accounts only used to update opening balances. [Click here to learn about update Opening balances](https://erpnext.com/kb/accounts/updating-opening-balance-in-accounts-using-temporary-account)

After completing all opening entries against these temporary accounts balances for both accounts will updated. And Debit balance of Temporary Account (Assets) will became equal to Credit balance of Temporary Account (Liabilities).

Since temporary account were used only for balancing purpose, it shall not have any balance in it.
To nullify balance in these accounts, you should create a new Journal Voucher, where will you update  balances against these accounts. To create new Journal Entry go to `Accounts &gt; Documents &gt; Journal Entry

![Journal Entry]({{docs_base_url}}/assets/img/articles/$SGrab_432.png)

On submit of this journal entry, balances of these temporary accounts will be set to Zero.

<!-- markdown -->