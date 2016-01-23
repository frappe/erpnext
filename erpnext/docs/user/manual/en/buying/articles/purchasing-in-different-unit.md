#Purchasing in Different Unit (UoM)

Each item has stock unit of measument (UoM) associated to it. For example UoM of pen is nos. and sand stocked kgs. But item could be purchased in different UoM, like 1 set/box of pen, or one truck of sand. In ERPNex, you can create purchase transaction for an item having different UoM than item's stock UoM.

### Scenario:

Item `Pen` is stocked in Nos, but purchased in Box. Hence we will make Purchase Order for Pen in Box.

#### Step 1: Edit UoM in the Purchase Order

In the Purchase Order, you will find two UoM fied.

- UoM
- Stock UoM

In both the fields, default UoM of an item will be fetched by default. You should edit UoM field, and select Purchase UoM (Box in this case). Updating Purchase UoM is mainly for the reference of the supplier. In the print format, you will see item qty in the Purchase UoM.

<img alt="Item Purchase UoM" class="screenshot" src="{{docs_base_url}}/assets/img/articles/editing-uom-in-po.gif">

#### Step 2: Update UoM Conversion Factors

In one Box, if you get 20 Nos. of Pen, UoM Conversion Factor would be 20. 

<img alt="Item Conversion Factor" class="screenshot" src="{{docs_base_url}}/assets/img/articles/po-conversion-factor.png">

Based on the Qty and Conversion Factor, qty will be calculated in the Stock UoM of an item. If you purchase just one Box, then Qty in the stock UoM will be set as 20.

<img alt="Purchase Qty in Default UoM" class="screenshot" src="{{docs_base_url}}/assets/img/articles/po-qty-in-stock-uom.png">

### Stock Ledger Posting

Irrespective of the Purchase UoM selected, stock ledger posting will be done in the Default UoM of an item. Hence you should ensure that conversion factor is entered correctly while purchasing item in different UoM.

<img alt="Print Format in Purchase UoM" class="screenshot" src="{{docs_base_url}}/assets/img/articles/po-stock-uom-ledger.png">

### Set Conversion Factor in Item

In the Item master, under Purchase section, you can list all the possible purchase UoM of an item, with its UoM Conversion Factor.

<img alt="Purchase UoM master" class="screenshot" src="{{docs_base_url}}/assets/img/articles/item-purchase-uom-conversion.png">

<!-- markdown -->