<h1>Manage Rejected Finished Goods Items</h1>

<h1>Manage Rejected Finished Goods Items</h1>

There could be manufactured Items which would not pass quality test, and would be rejected.

Standard manufacturing process in ERPNext doesn't cover managing rejected items separately. Hence you should create finished goods entry for both accepted as well as rejected items. With this, you will have rejected items also received in the finished goods warehouse.

To move rejected items from the finished goods warehouse, you should create Material Transfer entry. Steps below to create Material Transfer entry.

####New Stock Entry

`Stock > Stock Entry > New`

####Entry Purpose

Purpose = Material Transfer

####Warehouse

Source Warehouse = Finished Goods warehouse
Target Warehouse = Rejected items warehouse

####Items

Select item which failed quality test, and enter total rejected items as Qty.

####Submit Stock Entry

On Saving and Submitting Stock Entry, stock of rejected items will be moved from Finished Goods Warehouse to Rejected Warehouse.

<!-- markdown -->