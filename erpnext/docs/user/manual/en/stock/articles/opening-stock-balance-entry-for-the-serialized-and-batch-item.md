#Opening Stock Balance Entry for the Serialized and Batch Item

Items for which Serial No. and Batch No. is maintained, opening stock balance entry for them is update via Stock Entry. [Click here to learn how serialized inventory is managed in ERPNext]({{docs_base_url}}/user/manual/en/stock/serial-no.html).

**Question:** Why Opening Balance entry for the Serialized and Batch Item cannot be updated via Stock Reconciliation?

In the ERPNext, stock level of a serialized items is derived based on the count of Serial Nos for that item. Hence, unless Serial Nos. are created for the serialized item, its stock level is not be updated. In the Stock Reconciliation Tool, you can only update opening quantity of an item, but not their Serial No. and Batch No.

### Opening Balance for the Serialized Item

Following are the steps to create opening stock balance entry for the Serialized and Batch item.

#### Step 1: New Stock Entry

`Stock > Stock Entry > New`

#### Step 2: Select Purpose

Stock Entry Purpose should be updated as `Material Receipt`.

#### Step 3: Update Posting Date

Posting Date should be date on which you wish to update opening balance for an item.

#### Step 4: Update Target Warehouse

Target Warehouse will be one in which opening balance of an item will be updated.

#### Step 5: Select Items

Select Items for which opening balance is to be updated.

#### Step 6: Update Opening Qty

For the serialized item, update quantity as many Serial Nos are their.

For the serialized item, mention Serial Nos. equivalent to it's Qty. Or if Serial Nos. are configured to be created based on Prefix, then no need to mention Serial Nos. manually. Click [here]({{docs_base_url}}/user/manual/en/stock/articles/serial-no-naming.html) to learn more about Serial No. naming.

For a batch item, provide Batch ID in which opening balance will be updated. Keep batch master ready, and updated it for the Batch Item. To create new Batch, go to:

`Stock > Setup > Batch > New`

[Click here to learn how Batchwise inventory is managed in ERPNext.]({{docs_base_url}}/user/manual/en/stock/articles/managing-batch-wise-inventory.html)

#### Step 7: Update Valuation Rate an Item

Update valuation rate, which will be per unit value of item. If different units of the same items having different valuation rate, they should be updated in a separate row, with different Valuation Rates.

#### Step 8: Difference Account

As per perpetual inventory valuation system, accounting entry is created for every stock transaction. Double entry accounting system requires Total Debit matching with Total Credit in an entry. On the submission of Stock Entry, system debits Warehouse account by total value of items. To balance the same, we use Temporary Opening account as a Difference Account.

<img alt="Difference Account" class="screenshot" src="{{docs_base_url}}/assets/img/articles/difference-account-1.png">

#### Step 9: Save and Submit Stock Entry

On submission of Stock Entry, stock ledger posting will be posted, and opening balance will be updated for the items on a given Posting Date.


<!-- markdown -->