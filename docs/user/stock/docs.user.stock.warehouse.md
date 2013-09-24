---
{
	"_label": "Warehouse"
}
---

A warehouse is a commercial building for storage of goods. Warehouses are used by manufacturers, importers, exporters, wholesalers, transport businesses, customs, etc. They are usually large plain buildings in industrial areas of cities,towns, and villages. They usually have loading docks to load and unload goods from trucks.

To go to Warehouse, click on Stock and go to Warehouse under Masters.


> Stock > Warehouse > New Warehouse



![Warehouse](img/warehouse.png)




In ERPNext, every Warehouse must belong to a specific company, to maintain company wise stock balance. The Warehouses are saved with their respective company’s abbreviations. This facilitates in identifying which Warehouse belongs to which company, at a glance.

You can include user restrictions for these Warehouses. In case you do not wish a particular user to operate on a particular Warehouse, you can refrain the user from accessing that Warehouse.

### Merge Warehouse

In day to day transactions, duplicate entries are done by mistake, resulting in duplicate Warehouses. Duplicate records can be merged into a single Warehouse. Enter the correct Warehouse and click on the Merge button. The system will replace all the links of wrong Warehouse with the correct Warehouse, in all transactions. Also, the available quantity (actual qty, reserved qty, ordered qty etc) of all items in the duplicate warehouse will be transferred to the correct warehouse. Once merging is done, delete the duplicate Warehouse.

> Note: ERPNext system maintains stock balance for every distinct combination of Item and Warehouse. Thus you can get stock balance for any specific Item in a particular Warehouse on any particular date.