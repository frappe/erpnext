---
{
	"_label": "Opening Accounts and Inventory"
}
---
Now ￼that you have completed most of the setup, its time to start moving in!

There are two important sets of data you need to enter before you start your operations.

- Opening Account balances.
- Opening Stock balances.

To setup your accounts and stock correctly you will need accurate data to work with. Make sure you have the data setup for this.

### Opening Accounts

We usually recommend that you start using accounting in a new financial year, but you could start midway too. To setup your accounts, you will need the following for the “day” you start using accounting in ERPNext:

Opening capital accounts - like your shareholder’s (or owner’) capital, loans, bank balances on that day.
List of outstanding sales and purchase invoices (Payables and Receivables).

#### Temporary Accounts

A nice way to simplify opening is to create temporary accounts for assets and liability just for opening. These accounts will become zero once all your old invoices are entered. The two accounts which you can create are (example):

- Temp Opening Liabilities
- Temp Opening Assets

#### The Opening Entry

In ERPNext Opening Accounts are setup by submitting a special Journal Entries (Journal Voucher).

Note: Make sure to set “Is Opening” as “Yes” in the More Info section.


> Setup > Opening Accounts and Stock > Opening Accounting Entries.



#### Step 1: Select Opening Entry in the Voucher Type section.

![Opening Entry](img/opening-entry.png)

<br>

#### Step 2: Complete Journal Entries on the Debit and Credit side. 


![Opening Entry](img/opening-entry-1.png)

<br>


#### Step 2: Select Yes in the "Is Opening " record under More Info.


![Opening Entry](img/opening-entry-2.png)



You can make two Opening Journal Vouchers:

- For all assets (excluding Accounts Receivables): This entry will contain all your assets except the amounts you are expecting from your Customers against outstanding Sales Invoices. You will have to update your receivables by making an individual entry for each Invoice (this is because, the system will help you track the invoices which are yet to be paid). Since all the entries in this voucher will be of type “Debit”, you can credit the sum of all these debits against the “Temp Opening Liabilities” account.
- For all liabilities: Similarly you need to pass a Journal Voucher for your Opening Liabilities (except for the bills you have to pay). This can be made against the “Temp Opening Assets” account.

After completing the accounting entries, the trial balance report will look like the one given below:


![Trial Balance](img/trial-balance-1.png)



#### Outstanding Invoices

After your Opening Journal Vouchers are made, you will need to enter each Sales Invoice and Purchase Invoice that is yet to be paid. 

Since you have already booked the income or expense on these invoices in the previous period, select the temp opening accounts in the “Income” and “Expense” accounts.

Note: Again make sure to set each invoice as “Is Opening”!

If you don’t care what items are in that invoice, just make a dummy item entry in the Invoice. Item code in the Invoice is not necessary, so it should not be such a problem.

Once all your invoices are entered, your “Temp Opening Assets” will be same as “Temp Opening Liabilities” and you can pass another “Is Opening” type of Journal Voucher and cancel them to zero!

