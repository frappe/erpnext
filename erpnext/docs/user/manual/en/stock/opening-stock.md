# Opening Stock

<p class="lead"> Opening Stock is the Stock quantity in the beginning of every accounting year of an organisation. The closing Stock with the prior accounting year becomes the opening Stock with the existing accounting year.</p>

Opening Stock can be done for serialized Items as well as non-serialized Items.To update opening stock for non-serialized Item, you should perform Stock Reconciliation. For serialised Item, you can make Stock Entry of type Material Receipt.

> Stock > Stock Reconciliation > New Stock Reconciliation

In both cases, you should enter "Difference/Expense Account" as **Temporary Opening** account. On submission of the document, system will debit Warehouse account which is an asset account and credit difference/expense account. Before making these entries, make sure you have enabled "Perpetual Inventory" by checking Stock Settings page.

If you are not making opening Stock Entry, you can select "Stock Adjustment" account in Difference/Expense Account field which is an expense account.

To understand Opening Stock for serialized Items visit [Stock Reconciliation](/docs/user/manual/en/setting-up/stock-reconciliation-for-non-serialized-item.html)

{next}
