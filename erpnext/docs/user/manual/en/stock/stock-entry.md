A Stock Entry is a simple document that lets you record Item movement from a
Warehouse, to a Warehouse and between Warehouses.

To make a Stock Entry you have to go to:

> Stock > Stock Entry > New

<img class="screenshot" alt="Stock Entry" src="{{docs_base_url}}/assets/img/stock/stock-entry.png">

Stock Entries can be made for the following purposes:

* Material Issue - If the material is being issued. (Outgoing Material)
* Material Receipt - If the material is being received. (Incoming Material)
* Material Transfer - If the material is being moved from one warehouse to another.
* Material Transfer for Manufacturing - If the material being transfered is for Manufacturing Process.
* Manufacture - If the Material is being received from a Manufacturing/Production Operation.
* Repack - If the Original item/items is being repacked into new item/items.
* Subcontract - If the Material is being issued for a sub-contract activity.

In the Stock Entry you have to update the Items table with all your
transactions. For each row, you must enter a “Source Warehouse” or a “Target
Warehouse” or both (if you are recording a movement).

**Additional Costs:**

If the stock entry is an incoming entry i.e any item is receiving at a target warehouse, you can add related additional costs (like Shipping Charges, Customs Duty, Operating Costs etc) associated with the process. The additional costs will be considered to calculate valuation rate of the items.

To add additional costs, enter the description and amount of the cost in the Additional Costs table.

<img class="screenshot" alt="Stock Entry Additional Costs" src="{{docs_base_url}}/assets/img/stock/additional-costs-table.png">

The added additional costs will be distributed among the receiving items (where the target warehouse mentioned) proportionately based on Basic Amount of the items. And the distributed additional cost will be added to the basic rate of the item, to calculate valuation rate.

<img class="screenshot" alt="Stock Entry Item Valuation Rate" src="{{docs_base_url}}/assets/img/stock/stock-entry-item-valuation-rate.png">

If perpetual inventory system is enabled, additional costs will be booked in "Expense Included In Valuation" account.

<img class="screenshot" alt="Additional Costs General Ledger" src="{{docs_base_url}}/assets/img/stock/additional-costs-general-ledger.png">


> **Note:** To update Stock from a spreadsheet, see [Stock Reconciliation]({{doc_base_url}}/user/manual/en/setting-up/stock-reconciliation-for-non-serialized-item.html).

{next}
