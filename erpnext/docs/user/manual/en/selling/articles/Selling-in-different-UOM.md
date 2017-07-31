# Selling In Different Uom

#Selling in Different Unit (UoM)
 
A sell price unit of measure (UOM) is the UOM with which you price items. You can have multiple sell price UOMs for any inventory item.  However, when Customer places, UoM for an item could change. 
 
For example an Item Pen is stocked in Nos, but sold in Box. Hence we will make Sales Order for Pen in Box.
 
###Step 1: In the Item master, under Unit of Measure section, you can list all the possible UoM of an item, with its UoM Conversion Factor. Update UoM Conversion Factors
In one Box, if you get 10 Nos. of Pen, UoM Conversion Factor would be 10.

<img class="screenshot" alt="Item Unit of Measure" src="{{docs_base_url}}/assets/img/selling/Item-UOM.png">


###Setp 2: In the Sale Order, you will find two UoM fields

-UoM
-Stock UoM

In both the fields, default UoM of an item will be fetched by default. You should edit UoM field, and select Sale UoM (Box in this case).  Updating Sales UoM is mainly for the reference of the Customer. In the print format, you will see item quantity in the Sales UoM.

<img class="screenshot" alt="Sale order Unit of Measure" src="{{docs_base_url}}/assets/img/selling/Sale-Order-UOM.png">
 
Based on the Qty and Conversion Factor, qty will be calculated in the Stock UoM of an item. If you sell just one Box, then Qty as per stock UoM will be set as 10.
 
 
###Stock Ledger Posting
 
Irrespective of the Sales UoM selected in the Sale Order, stock ledger posting will be done in the Default UoM of an item. Hence you should ensure that conversion factor is entered correctly while selling item in different UoM.

<img class="screenshot" alt="Stock report in UOM" src="{{docs_base_url}}/assets/img/selling/stock ledger for as STOCK-UOM.png">
