#Managing Batch wise Inventory

Set of items which has same properties and attributes can be group in a single Batch. For example, pharmaceuticals  items are batch, so that it's manufacturing and expiry date can be tracked together. 

To maintain batches against an Item you need to mention 'Has Batch No' as yes in the Item Master. 

<img alt="Batch Item" class="screenshot" src="{{docs_base_url}}/assets/img/articles/batchwise-stock-1.png">

You can create a new Batch from:

`Stock > Documents > Batch > New`

To learn more about batch, click [here.]({{docs_base_url}}/user/manual/en/stock/batch.html)

For the Batch item, updating Batch No. in the stock transactions (Purchase Receipt & Delivery Note) is mandatory.

#### Purchase Receipt

When creating Purchase Receipt, you should create new Batch, or select one of the existing Batch master. One Batch can be associated with one Batch Item.

<img alt="Batch in Purchase Receipt" class="screenshot" src="{{docs_base_url}}/assets/img/articles/batchwise-stock-2.png">

#### Delivery Note

Define Batch in Delivery Note Item table. If Batch item is added under Product Bundle, you can update it's Batch No. in the Packing List table sa well.

<img alt="Batch in Delivery Note" class="screenshot" src="{{docs_base_url}}/assets/img/articles/batchwise-stock-3.png">

#### Batch-wise Stock Balance Report

To check batch-wise stock balance report, go to:

Stock > Standard Reports > Batch-wise Balance History

<img alt="Batchwise Stock Balance" class="screenshot" src="{{docs_base_url}}/assets/img/articles/batchwise-stock-4.png">
