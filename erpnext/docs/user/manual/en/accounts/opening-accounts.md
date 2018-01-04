# Updating Opening Balance in Accounts

If you are a new company you can start using ERPNext accounting module by going to chart of accounts. However, if you are migrating from a legacy accounting system like Tally or a Fox Pro based software

We recommend that you start using accounting in a new financial year, but you could start midway too. To setup your accounts, you will need the following for the “day” you start using accounting in ERPNext:

* Opening capital accounts - like your shareholder’s (or owner’) capital, loans, bank balances on that day.

* List of outstanding sales and purchase invoices (Payables and Receivables).

If you were using another accounting software before, firstly you should close financial statements in that software. The closing balance of the accounts should be updated as an opening balance in the ERPNext. Before starting to update opening balance, ensure that your [Chart of Accounts](/docs/user/manual/en/accounts/chart-of-accounts.html) has all the Accounts required.

> Opening entry is only for Balance Sheet accounts and not for the Accounts in the Profit and Loss statement.

  * For all assets (excluding Accounts Receivables): This entry will contain all your assets except the amounts you are expecting from your Customers against outstanding Sales Invoices. You will have to update your receivables by making an individual entry for each Invoice (this is because, the system will help you track the invoices which are yet to be paid). You can credit the sum of all these debits against the **Temporary Opening** account.

  * For all liabilities: Similarly you need to pass a Journal Entry for your Opening Liabilities (except for the bills you have to pay) against **Temporary Opening** account.

###Opening Entry

#### Step 1: New Journal Entry

To open new Journal Entry, go to:

`Explore > Accounts > Journal Entry`

#### Step 2: Entry Type

If Entry Type is selected as Opening Entry, all the Balance Sheet Accounts will be auto-fetched in the Journal Entry.

<img class="screenshot" alt="Opening Account" src="/docs/assets/img/accounts/opening-account-1.png">

#### Step 3: Posting Date

Select Posting Date on which Accounts Opening Balance will be updated.

#### Step 4: Enter Debit/Credit Value

For each Account, enter opening value in the Debit or Credit column. As per the double entry valuation system, Total Debit value in a entry must be equal to Total Credit value.

<img class="screenshot" alt="Opening Account" src="/docs/assets/img/accounts/opening-6.png">

####Step 5: Is Opening

Set field `Is Opening` as `Yes`.

<img class="screenshot" alt="Opening Account" src="/docs/assets/img/accounts/opening-3.png">

####Step 6: Save and Submit

After enter opening balance for each account, Save and Submit Journal Entry. To check if Opening Balance for an account is updated correctly, you can check Trial Balance report.

###Selecting Accounts Manually

If your Balance Sheet has many Accounts, then updating Account Opening balance from single Journal Entry can lead to performance issues. In such a scenario, you can multiple Journal Entries to update opening balance in all the Accounts.

If you are updating account opening balance in few accounts at a time, you can use **Temporary Opening** account for balancing purpose. In the standard chart of accounts, a Temporary Opening Account is auto-created under Assets.

<img class="screenshot" alt="Opening Account" src="/docs/assets/img/accounts/opening-7.png">

In the Journal Entry, manually select an Account for which opening balance is to be updated. For each Account, enter opening balance value in the Debit or Credit column, based on it's Account Type (Asset or Liability).

For example, if you want to update balance in bank accounts, create Journal Entry as following.

<img class="screenshot" alt="Opening Account" src="/docs/assets/img/accounts/opening-2.png">

Once all your invoices are entered, your **Temporary Opening** account will have a balance of zero!

###Trial Balance

After completing the accounting entries, the trial balance report will look like the one given below:

<img class="screenshot" alt="Opening Account" src="/docs/assets/img/accounts/opening-4.png">

###Stock Opening

To track stock balance in the Chart of Account, an Account is created for each Warehouse.

`Chart of Accounts > Assets > Current Asset > StocK Assets > (Warehouse Account)`

<img class="screenshot" alt="Opening Account" src="/docs/assets/img/accounts/opening-5.png">

To update stock opening balance, create [Stock Reconciliation entry](/docs/user/manual/en/stock/opening-stock.html). Based on the valuation of items's update in the Warehouse, balance will be updated in the Warehouse account.

###Fixed Asset Opening

Opening balance for the fixed asset account should be updated via Journal Entry. Assets which are not fully depreciated should be added in the [Asset master](/docs/user/manual/en/accounts/managing-fixed-assets.html). For adding Assets in your possession, ensure to check **Is Existing Asset** field.

### Outstanding Payables and Receivables

After opening Journal Entries are made, you will need to enter the Sales Invoice and Purchase Invoice that is yet to be paid.

Since you have already booked the income or expense on these invoices in the previous period, select **Temporary Opening** in the “Income” and “Expense” accounts.

> Note: Make sure to set each invoice as “Is Opening”!

If you don’t care what items are in that invoice, just make a dummy item entry in the Invoice. Item code in the Invoice is not necessary, so it should not be such a problem.

You can also do this quickly using the **Opening Invoice Creation Tool**

To use this tool, just type "Opening Invoice" in the search bar and select the **Opening Invoice Creation Tool**

Here, select the company and type of invoice (sales or purchase) and add a line item for each invoice you want to create.

<img class="screenshot" alt="Opening Invoice Creation Tool" src="/docs/assets/img/accounts/opening-invoice-creation-tool.png">

{next}
