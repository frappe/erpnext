# Stock Entry Purpose

#Stock Entry Purpose

Stock Entry is a stock transaction, which can be used for multiple purposes. Let's learn about each Stock Entry Purpose below.

#### 1.Purpose: Material Issue

Material Issue entry create to issue item(s) from a warehouse. On submission of Material Issue, stock of item is deducated from the Source Warehouse. 

Material Issue is generally made for the low value consumable items like office stationary, product consumables etc. Also you can create Material Issue to reconcile serialized and batched item's stock.

<img alt="Material Issue" class="screenshot" src="/docs/assets/img/articles/stock-entry-issue.png">

#### 2.Purpose: Material Receipt

Material Receipt entry is created to inward stock of item(s) in a warehouse. This type of stock entry can be created for updating opening balance of serialized and batched item. Also items purchased without Purchase Order can be inwarded from Material Receipt entry.

For the stock valuation purpose, provided Item Valuation becomes a mandatory field in the Material Receipt entry.

<img alt="Material Receipt" class="screenshot" src="/docs/assets/img/articles/stock-entry-receipt.png">

#### 3.Purpose: Material Transfer

Material Transfer entry is created for the inter-warehouse Material Transfer.

<img alt="Material Transfer" class="screenshot" src="/docs/assets/img/articles/stock-entry-transfer.png">
 
#### 4.Purpose: Material Transfer for Manufacture 

In the manufacturing process, raw-materials are issued from the stores to the production department (generally WIP warehouse). This Material Transfer entry is created from Production Order. Items in this entry are fetched from the BOM of production Item, as selected in Production Order.

<img alt="Transfer for Manufacture" class="screenshot" src="/docs/assets/img/articles/stock-entry-manufacture-transfer.gif">

#### 4.Purpose: Manufacture

Manufacture is created from Production Order. In this entry, both raw-material item as well as production item are fetched from the BOM, selected in the Production Order. For the raw-material items, only Source Warehouse (generally WIP warehouse) is mentioned. For the production item, only target warehouse as mentioned in the Production Order is updated. On submission, stock of raw-material items are deducted from Source Warehouse, which indicates that raw-material items were consumed in the manufacturing process. Production Item is added to the Target Warehouse marking the completion of production cycle.

<img alt="Manufacture" class="screenshot" src="/docs/assets/img/articles/stock-entry-manufacture.gif">

#### 5.Purpose: Repack

Repack Entry is created when items purchases in bulk is repacked under smaller packs. ![Check this page to know more about Repack entry.](/docs/user/manual/en/stock/articles/repack-entry.html)

#### 6.Purpose: Subcontract

Subcontracting transaction involves company transfer raw-material items to the sub-contractors warehouse. This requires adding a warehouse for the sub-contractor as well. Sub-contract entry transfers stock from the companies warehouse to the sub-contractors warehouse.![Check this page to know more about Subcontracting](/docs/user/manual/en/manufacturing/subcontracting.html).

<img alt="Subcontract" class="screenshot" src="/docs/assets/img/articles/stock-entry-subcontract.gif">

<!-- markdown -->