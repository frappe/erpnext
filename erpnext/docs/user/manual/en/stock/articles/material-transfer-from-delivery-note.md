# Material Transfer from Delivery Note

In ERPNext, you can create Material Transfer entry from [Stock Entry](/docs/user/manual/en/stock/stock-entry.html) document. However, there are some scenarios in the Material Transfer where it needs to be presented as a Delivery Note. 

### Scenarios

1. One of the examples is when you transfer a Material from your stores to project site, however, you need to present it as a Delivery Note to the client.

2. Also, there are statutory requirements where taxes are to be applied on each transfer of Material. It is easier to manage in a transaction like Delivery Note, than in the Stock Entry.

Considering these scenarios, the provision of Material Transfer has been added in the Delivery Note as well. Following are the steps to use Delivery Note for creating Material Transfer entry.

### Steps

#### Enable Customer Warehouse

Delivery Note Item doctype as a hidden field of Customer Warehouse. You can enable it from [Customize Form](/docs/user/manual/en/customize-erpnext/customize-form.html). Here is the quick demonstration of the same.

<img class="screenshot" alt="Delivery Note Material Transfer" src="{{docs_base_url}}/assets/img/stock/customer-warehouse.gif">

### Select Warehouses

When creating a Delivery Note for Material Transfer, for an item select source Warehouse as From Warehouse.

In the Customer Warehouse, select a Warehouse where Material is to be transferred or select a target warehouse.

<img class="screenshot" alt="Delivery Note Material Transfer" src="{{docs_base_url}}/assets/img/stock/customer-warehouse-2.png">

On the submission of a Delivery Note, item's stock will be deducted from "From Warehouse" and added to the "Customer Warehouse".