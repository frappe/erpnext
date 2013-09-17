---
{
	"_label": "Production Order"
}
---
Production Order (also called as Work Order) is a document that is given to the manufacturing shop floor by the Production Planner as a signal to produce a certain quantity of a certain Item. Production Order also helps to generate the material requirements (Stock Entry) for the Item to be produced from its **Bill of Materials**. 

The **Production Order** is generated directly from the **Production Planning Tool** based on Sales Orders. You can also create a direct Production Order by:

> Manufacturing > Production Order > New Production Order


![Production Order](img/production-order.png)



- Select the Item to be produced (must have a Bill of Materials).
- Select the BOM
- Select Quantities
- Select Warehouses. WIP (Work-in-Progress) is where your Items will be transferred when you begin production and FG (Finished Goods) where you store finished Items before they are shipped.
- Select if you want to consider sub-assemblies (sub-Items that have their own BOM) as stock items or you want to explode the entire BOM when you make Stock Entries for this Item. What it means is that if you also maintain stock of your sub assemblies then you should set this as “No” and in your Stock Entires, it will also list the sub-assembly Item (not is sub-components).

and “Submit” the Production Order.

Once you “Submit”, you will see two more buttons:

![Production Order](img/production-order-2.png)


1. Transfer Raw Material: This will create a Stock Entry with all the Items required to complete this Production Order to be added to the WIP Warehouse. (this will add sub-Items with BOM as one Item or explode their children based on your setting above). 
1. Update Finished Goods: This will create a Stock Entry that will deduct all the sub-Items from the WIP Warehouse and add them to the Finished Goods Warehouse.

> Tip: You can also partially complete a Production Order by updating the Finished Goods stock creating a Stock Entry.

When you Update Finished Goods to the Finished Goods Warehouse, the “Produced Quantity” will be updated in the Production Order.

