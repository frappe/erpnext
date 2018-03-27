# Work Order

<img class="screenshot" alt="Work Order" src="{{docs_base_url}}/assets/img/manufacturing/manufacturing-flow.png">
A Work Order is a document that is given to
the manufacturing shop floor by the Production Planner as a signal to produce
a certain quantity of a certain Item. The Work Order also helps to generate
the material requirements (Stock Entry) for the Item to be produced from its
**Bill of Materials**.

The **Work Order** is generated from the **Production Planning
Tool** based on Sales Orders. You can also create a direct Work Order
by:

> Manufacturing > Documents > Work Order > New

<img class="screenshot" alt="Work Order" src="{{docs_base_url}}/assets/img/manufacturing/work-order.png">

<div class-"embed-container">
  <iframe src="https://www.youtube.com/embed/yv_KAIlHrO4?rel=0" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen>
  </iframe>
</div>

### Creating Work Orders

  * Select the Item to be produced.
  * The default BOM for that item will be fetched by the system. You can also change BOM.
  * Enter the Qty to manufacture.
  * If the selected BOM has operartion mentioned in it, the system shall fetch all operations from BOM.
  * Mention the Planned Start Date (an Estimated Date at which you want the Production to begin.)
  * Select Warehouses:
    * Source Warehouses: The warehouse where you store your raw materials. Each required item can have separate source warehouse. Group warehouse also can be selected as source warehouse. On submission of Work Order, the raw mateirals will be reserved in these warehouses for production usage.
    * Work-in-Progress Warehouse: The warehouse where your Items will be transferred when you begin production. Group Warehouse can also be selected as Work-in-Progress warehouse.
    * Target Warehouse: The warehouse where you store finished Items before they are shipped.
	* Scrap Warehouse: Scrap Items will be stored in this warehouse.
  * Required Items: All the required items (raw materials) will be fetched from BOM and populated in this table. Here you can also change the default source warehouse for any item. And during the production, you can track transferred raw materials from this table.

> Note : You can save a Work Order without selecting the warehouses, but warehouses are mandatory for submitting a Work Order

###Reassigning Workstation/Duration for Operations

* By default the system fetchs workstation and duration for Work Order Operations from the selected BOM.

<img class="screenshot" alt="PO Opeartions" src="{{docs_base_url}}/assets/img/manufacturing/PO-operations.png">

* If you wish to reassign the workstation for a particular opeeration in the Work Order, you can do so before submitting the Work Order.

<img class="screenshot" alt="PO reassigning Operations" src="{{docs_base_url}}/assets/img/manufacturing/PO-reassigning-operations.png">

* Select the respective operation, and change its workstation.
* You can also change the Operating Time for that operation

### Capacity Planning in Work Order

* When a Work Order is submitted, based on the Planned Start Date and the availability of the workstations, system schedules all operations for the Work Order (if Work Order has operations specified).
* Drafts of Time Logs are also created based on the scheduled operations.

### Transfering Materials for Manufacturing

* Once you have submitted your Work Order, you need to Transfer the Raw Materials to initiate the Manufacturing Process.
* This will create a Stock Entry with all the Items required to complete this Work Order to be added to the WIP Warehouse. (this will add sub-Items with BOM as one Item or explode their children based on your setting above).

* Click on 'Start'.

<img class="screenshot" alt="Transfer Materials" src="{{docs_base_url}}/assets/img/manufacturing/PO-material-transfer.png">

* Mention the quantity of materials to be transfered.

<img class="screenshot" alt="Material Transfer Qty" src="{{docs_base_url}}/assets/img/manufacturing/PO-material-transfer-qty.png">

* Submit the Stock Entry

<img class="screenshot" alt="Stock Entry for PO" src="{{docs_base_url}}/assets/img/manufacturing/PO-SE-for-material-transfer.png">

* Material Transfered for Manufacturing will be updated in the Work Order based on the Stock Entry.

<img class="screenshot" alt="Stock Entry for PO" src="{{docs_base_url}}/assets/img/manufacturing/PO-material-transfer-updated.png">

#### Material Transfer through Stock Entry
Use cases for this option are:
* If material transfer is done in bulk and/or is not required to be tracked against a particular Work Order
* If the responsibility for Material Transfer and Production Entry lies with two separate users

If this is the case, you can select the Skip Material Transfer check box, which will allow you to make the “Manufacture” Stock Entry directly by clicking on the ‘Finish’ button.

### Making Time Logs

* Progress in the Work Order can be tracked using [Timesheet](/docs/user/manual/en/projects/timesheet/timesheet-against-work-order.html)
* Timesheet's time slots are created against Work Order Operations.
* Drafts of Timesheet are created based on the scheduled operations when an Work Order is Submitted.
* To create more Timesheets against an operation click 'Make Timesheet' button.

<img class="screenshot" alt="Make timesheet against PO" src="{{docs_base_url}}/assets/img/manufacturing/PO-operations-make-ts.png">

###Updating Finished Goods

* Once you are done with the Work Order you need to update the Finished Goods.
* This will create a Stock Entry that will deduct all the sub-Items from the WIP Warehouse and add them to the Finished Goods Warehouse.
* Click on 'Finish'.

<img class="screenshot" alt="Update Finished Goods" src="{{docs_base_url}}/assets/img/manufacturing/PO-FG-update.png">

* Mention the quantity of materials to be transfered.

<img class="screenshot" alt="Update Finished Goods Qty" src="{{docs_base_url}}/assets/img/manufacturing/PO-FG-update-qty.png">

 > Tip : You can also partially complete a Work Order by updating the Finished Goods stock creating a Stock Entry.
 
### Stopping a Work Order

* When you stop a Work Order its status is changed to Stop indicating that all production process against that Work Order is to be ceased.
* To stop the Work Order click on the 'Stop' Button

  1. On Submitting the Work Order, the system will reserve a slot for each of the Work Order Operations serially after the planned start date based on the workstation availability. The Workstation availability depends on the Workstation timings, holiday list and if some other Work Order Operation was scheduled in that slot. You can mention the number of days for the system to try scheduling the operations in the Manufacturing Settings. This is set to 30 Days by default. If the operation requires time exceeding the available slot, system shall ask you to break the operations. Once the scheduling is done system shall create Time Logs and save them. You can Modify them and submit them later.
  2. You can also create additional time logs against an Operation. For doing so select the respective operation and click on 'Make Time Log'
  3. Transfer Raw Material: This will create a Stock Entry with all the Items required to complete this Work Order to be added to the WIP Warehouse. (this will add sub-Items with BOM as one Item or explode their children based on your setting above).
  4. Update Finished Goods: This will create a Stock Entry that will deduct all the sub-Items from the WIP Warehouse and add them to the Finished Goods Warehouse.
  5. To check all Time Logs made against the Work Order click on 'Show Time Logs'

<img class="screenshot" alt="PO - stop" src="{{docs_base_url}}/assets/img/manufacturing/PO-stop.png">

* You can also re-start a stopped Work Order.

> Note : In order to make a Work Order against an Item you must specify 'Yes' to "Allow Work Order" on the Item form.

{next}
