Batch inventory feature in ERPNext allows you to group multiple units of an item, 
and assign them a unique value/number/tag called Batch No.

The practice of stocking based on batch is mainly followed in the pharmaceutical industry. 
Medicines/drugs produced in a particular batched is assigned a unique id. 
This helps them updating and tracking manufacturing and expiry date for all the units produced under specific batch.

> Note: To set item as a batch item, "Has Batch No" field should be updated as Yes in the Item master.

On every stock transaction (Purchase Receipt, Delivery Note, POS Invoice) made for batch item, 
you should provide item's Batch No. 

To create new Batch No. master for an item, go to:

> Stock > Setup > Batch > New

Batch master is created before creation of Purchase Receipt. 
Hence eveytime there is Purchase Receipt or Production entry being made for a batch item, 
you will first create its Batch No, and then select it in Purcase order or Production Entry.

<img class="screenshot" alt="batch" src="{{docs_base_url}}/assets/img/stock/batch.png">

> Note: In stock transactions, Batch IDs will be filtered based on Item Code, Warehouse, 
Batch Expiry Date (compared with Posting date of a transaction) and Actual Qty in Warehouse. 
While searching for Batch ID  without value in Warehouse field, then Actual Qty filter won't be applied.

{next}
