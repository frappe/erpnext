<h1>Updating Opening Balance in Accounts using Temporary Account</h1>

For updating opening balances in the Accounts, you will need to use temporary adjustment accounts. In the Chart of Account, two adjustment accounts will be created by default.

1. Temporary Account (Assets)
2. Temporary Account (Liabilities)

Since ERPNext is a double entry accounting system, it requires balancing on debit side with credit side in an accounting entry. When start working on fresh ERPNext account, you will have to update opening balance in your Balance Sheet accounts. You can update opening balance in account(s), and use Temporary Account for balancing purpose.

Let's consider a scenario of updating opening balance in an Account using temporary account.

#### Identifying Accounts to Update Opening Balance

Say we have following customer's ledger, and have receivable from them. This receivable should be updated as opening balance in their account.

1. Comtek Solutions
1. Walky Tele Solution

Also we can update opening balance on Bank and Cash account.

1. Bank of Baroda
1. Cash

All these accounts are located on the Current Asset side, hence will have Debit balance.

#### Identifying Temporary Account

To update debit balance in them, we will have to select Credit account for balancing it. Out of the temporary accounts available, we can use `Temporary Account (Liabilities)`.

##### Opening Balance Entry

For Current Asset account, their current balance will be updated on the Debit side. The total value of Debit will be entered as Credit Balance for the Temporary Account (Liability).

![Debit Opening Balance]({{docs_base_url}}/assets/img/articles/$SGrab_431.png)

Same way, you will update opening balance for the liability account. Since Liability accounts will have credit balance, you will have to select Temporary Account (Asset), which is a Debit account for balancing purpose.

After you have updated opening balance in all the Asset and Liability account, you will find that balance in the temporary account will be equal. If balance in temporary accounts is not equal, it must be because opening balance is not updated in some account, or other account was used for balancing purpose.

Since temporary account were used only for balancing purpose, it shall not have any balance in it. To nullify balance in these accounts, you should create a Journal Voucher which will set balance as zero in these account.

![Temporary Account Nullified]({{docs_base_url}}/assets/img/articles/$SGrab_432.png)

<!-- markdown -->