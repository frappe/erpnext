# Bill Of Materials

At the heart of the Manufacturing system is the **Bill of Materials** (BOM).
The **BOM** is a list of all materials (either bought or made) and operations
that go into a finished product or sub-Item. In ERPNext, the component could
have its own BOM hence forming a tree of Items with multiple levels.

To make accurate Purchase Requests, you must always maintain correct BOMs.
To make a new BOM:

> Manufacturing > Bill of Materials > New BOM

<img class="screenshot" alt="Task" src="/docs/assets/img/manufacturing/bom.png">

* To add Operations select 'With Operation'. The Operations table shall appear.

<img class="screenshot" alt="Task" src="/docs/assets/img/manufacturing/bom-operations.png">

  * Select the Item for which you want to make the BOM.
  * Add the operations that you have to go through to make that particular Item in the “Operations” table. For each operation, you will be asked to enter a Workstation. You must create new Workstations as and when necessary.
  * Workstations are defined only for product costing and Production Order Operations scheduling purposes not inventory. 
  * Inventory is tracked in Warehouses not Workstations.

###Costing of a BOM

* The Costing section in BOM gives an approximate cost of producing the Item.

* Add the list of Items you require for each operation, with its quantity. This Item could be a purchased Item or a sub-assembly with its own BOM. If the row Item is a manufactured Item and has multiple BOMs, select the appropriate BOM. You can also define if a part of the Item goes into scrap.

<img class="screenshot" alt="Costing" src="/docs/assets/img/manufacturing/bom-costing.png">

* This cost can be updated on by using the 'Update Cost' button.

<img class="screenshot" alt="Update Cost" src="/docs/assets/img/manufacturing/bom-update-cost.png">

* User can select the currency in the BOM 
* System calculates the costing based on the price list currency

<img class="screenshot" alt="Update Cost" src="/docs/assets/img/manufacturing/price-list-based-currency-bom.png">

### Materials Required(exploded) 

This table lists down all the Material required for the Item to be Manufactured.
It also fetches sub-assemblies along with the quantity.

<img class="screenshot" alt="Exploded Section" src="/docs/assets/img/manufacturing/bom-exploded.png">

{next}
