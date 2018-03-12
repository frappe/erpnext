#Manage Rejected Finished Goods Items

There could be manufactured Items which would not pass quality test, hence rejected.

Standard manufacturing process in ERPNext doesn't cover managing rejected items. Hence you should create finished goods entry for both accepted as well as rejected items. With this, you will have rejected items also received in the finished goods warehouse.

To move rejected items from the finished goods warehouse, you should create Material Transfer entry. Steps below to create Material Transfer entry.

####Step 1: New Stock Entry

`Stock > Documents > Stock Entry > New`

####Step 2: Purpose

Purpose = Material Transfer

####Step 3: Warehouse

Source Warehouse = Finished Goods warehouse
Target Warehouse = Rejected items warehouse

####Step 4: Items

Select item which failed quality test, and enter total rejected items as Qty.

####Step 5: Submit Stock Entry

On Saving and Submitting Stock Entry, stock of rejected items will be moved from Finished Goods Warehouse to Rejected Warehouse.


<!-- markdown -->