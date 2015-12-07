Now that you have completed most of the setup, its time to start moving in!

There are two important sets of data you need to enter before you start your
operations.

  * Opening Account balances.
  * Opening Stock balances.

To setup your accounts and stock correctly you will need accurate data to work
with. Make sure you have the data setup for this.

### Opening Accounts

We usually recommend that you start using accounting in a new financial year,
but you could start midway too. To setup your accounts, you will need the
following for the “day” you start using accounting in ERPNext:

Opening capital accounts - like your shareholder’s (or owner’) capital, loans,
bank balances on that day. List of outstanding sales and purchase invoices
(Payables and Receivables).

Based on Voucher Type

You can select accounts based on the voucher type. In such a scenario, your balance sheet should be balanced.

<img class="screenshot" alt="Opening Account" src="{{docs_base_url}}/assets/img/accounts/opening-account-1.png">

 Also, note that if there are more than 300 ledgers, the system will crash. Thus to avoid such a situation, you can open accounts by using temporary accounts.

#### Temporary Accounts

A nice way to simplify opening is to use a temporary account
just for opening. These accounts will become zero once all your old
invoices and opening balances of bank, debt stock etc are entered.
In the standard chart of accounts, a **Temperory Opening** account is created under
assets

#### The Opening Entry

In ERPNext Opening Accounts are setup by submitting a special Journal Entries
(Journal Entry).

Note: Make sure to set “Is Opening” as “Yes” in the More Info section.

> Setup > Opening Accounts and Stock > Opening Accounting Entries.

Complete Journal Entries on the Debit and Credit side.

![Opening Entry]({{docs_base_url}}/assets/old_images/erpnext/opening-entry-1.png)

 To update opening balance is to make Journal Entry for an individual/group of accounts.

For example, if you want to update balance in three bank accounts, then make Journal Entrys in this manner.

![Opening Temp Entry]({{docs_base_url}}/assets/old_images/erpnext/image-temp-opening.png)


![Opening Entry]({{docs_base_url}}/assets/old_images/erpnext/opening-entry-2.png)

Temporary Asset and Liability account is used for balancing purpose. When you update opening balance in Liability Account, you can use Temporary Asset Account for balancing.

This way, you can update opening balance in Asset and Liability accounts.

You can make two Opening Journal Entrys:

  * For all assets (excluding Accounts Receivables): This entry will contain all your assets except the amounts you are expecting from your Customers against outstanding Sales Invoices. You will have to update your receivables by making an individual entry for each Invoice (this is because, the system will help you track the invoices which are yet to be paid). You can credit the sum of all these debits against the **Temperory Opening** account.
  * For all liabilities: Similarly you need to pass a Journal Entry for your Opening Liabilities (except for the bills you have to pay) against **Temperory Opening** account.
  * In this method you can update opening balance of specific balancesheet accounts and not for all.
  * Opening entry is only for balance sheet accounts and not for expense or Income accounts.

After completing the accounting entries, the trial balance report will look
like the one given below:


![Trial Balance]({{docs_base_url}}/assets/old_images/erpnext/trial-balance-1.png)

#### Outstanding Invoices

After your Opening Journal Entrys are made, you will need to enter each
Sales Invoice and Purchase Invoice that is yet to be paid.

Since you have already booked the income or expense on these invoices in the
previous period, select the temp opening account **Temporary Opening** in the “Income” and
“Expense” accounts.

> Note: Make sure to set each invoice as “Is Opening”!

If you don’t care what items are in that invoice, just make a dummy item entry
in the Invoice. Item code in the Invoice is not necessary, so it should not be
such a problem.

Once all your invoices are entered, your **Temperory Opening** account will have a balance of zero!

{next}
