<h1>Opening Stock Balance Entry for the Serialized and Batch Item</h1>

<h1>Opening Stock Balance Entry for the Serialized and Batch Item</h1>

Items for which Serial No. and Batch No. is maintained, opening stock balance entry for them will be update via Stock Entry. [Click here to learn how serialized inventory is managed in ERPNext](https://erpnext.com/user-guide/stock/serialized-inventory).

Why Opening Balance entry for the Serialized and Batch Item cannot be updated via Stock Reconciliation?

In the ERPNext, stock level of a serialized items is derived based on the count of Serial Nos for that item. Hence, unless Serial Nos. are created for the serialized item, its stock level will not be updated. In the Stock Reconciliation Tool, you can only update opening quantity of an item, and not their Serial No. and Batch No.

Let's check steps for create opening stock balance entry for the Serialized and Batch item.

#### Step 1: New Stock Entry

`Stock > Stock Entry > New`

#### Step 2: Select Purpose

Stock Entry Purpose should be updated as `Material Receipt`.

#### Step 3: Update Posting Date

Posting Date should be date on which you wish to update opening balance for an item.

#### Step 4: Update Target Warehouse

Target Warehouse will be one in which opening balance of an item will be updated.

#### Step 5: Select Items

Select Items in the Stock Entry table.

#### Step 6: Update Opening Qty

For the serialized item, you should update as many Serial Nos as their Qty. If you have updated Prefix in the Item master, on the submission of Stock Entry Serial Nos. will be auto-created following that prefix.

![Item Serial No. Prefix]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-02-19 at 5.13.50 pm.png)

For a batch item, you should provide Batch ID in which opening balance will be updated. You should keep batch master ready, and updated it for the Batch Item. To create new Batch, go to:

`Stock > Setup > Batch > New`

[Click here to learn how Batchwise inventory is managed in ERPNext](https://erpnext.com/user-guide/stock/batchwise-inventory).

#### Step 7: Update Valuation Rate an Item

Valuation Rate is the mandatory field, where you should update `per unit value of item`. If you have unit of items having different valuation rates, they should be updated in a separate row, with different Valuation Rate.

#### Step 8: Difference Account

As per perpetual inventory valuation system, accounting entry is created for every stock entry. Accounting system followed in the ERPNext requires Total Debit in an entry matching with Total Credit. On the submission of Stock Entry, system Debits accounting ledger of a Warehouse by total value of items. To balance the same, we use Temporary Liability account in the Difference Account field. [Click here to learn more about use of Temporary Accounts in updating opening balance](https://erpnext.com/kb/accounts/updating-opening-balance-in-accounts-using-temporary-account).

![Difference Account]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-02-19 at 5.20.52 pm.png)

#### Step 9: Save and Submit Stock Entry

On submission of Stock Entry, stock ledger entry will be posted, and opening balance will be updated for the items on a given posting date.

If Serial Nos. for your items are set to be created based on prefix, then on submission of Stock Entry, Serial Nos. will be created as well.

![Serial No Creation]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-02-19 at 5.28.57 pm.png)

<!-- markdown -->