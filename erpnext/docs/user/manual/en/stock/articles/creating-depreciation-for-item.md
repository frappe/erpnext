# Creating Depreciation For Item

#Depreciation Entry

**Question:** A Fixed Asset Item has been purchased and stored in a warehouse. How to create a depreciation for a Fixed Asset Item?

**Answer:**You can post asset depreciation entry for the fixed asset item via [Stock Reconciliation]({{docs_base_url}}/user/manual/en/stock/opening-stock.html) Entry.

####Step 1:

In the Attachment file, fill in the appropriate columns;

- **Item Code** whose value is to be depreciated.
- **Warehouse** in which item is stored.
- **Qty (Quantity)** Leave this column blank.
- **Valuation Rate** will be item's value after depreciation.

<img alt="reorder level" class="screenshot" src="{{docs_base_url}}/assets/img/articles/fixed-asset-dep-1.gif">

After updating Valuation Rate for an item, come back to Stock Reconciliation and upload save .csv file.

####Step 2:

Select Expense account for depreciation in **Difference Account**. Value booked in the depreciation account will be the difference of old and next valuation rate of the fixed asset item, which will be actually the depreciation amount.

<img alt="reorder level" class="screenshot" src="{{docs_base_url}}/assets/img/articles/fixed-asset-dep-2.png">

####Stock Reconciliation Help Video

<iframe width="660" height="371" src="https://www.youtube.com/embed/0yPgrtfeCTs" frameborder="0" allowfullscreen></iframe>
