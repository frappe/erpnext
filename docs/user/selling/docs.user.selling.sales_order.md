---
{
	"_label": "Sales Order"
}
---
The Sales Order confirms your sales and triggers purchase (**Material  Request**) shipment (**Delivery Note**), billing (**Sales Invoice**) and manufacturing (**Production Plan**)

A Sales Order is usually a binding Contract with your Customer.

Once your customer confirms the Quotation you can convert your Quotation into a Sales Order.



![Sales Order](img/sales-order-f.jpg)





Alternatively, you can create a Sales Order directly from:


> Selling > Sales Order > New Sales Order



![Sales Order](img/sales-order.png)





Most of the information in your Sales Order is the same as the Quotation. There are a few amongst other things that a Sales Order will ask you to update.

- Expected date of delivery.
- Customer Purchase Order number: If your customer has sent you a Purchase Order, you can update its number for future reference (in billing).

#### Packing List

The “Packing List” table will be automatically updated when you “Save” the Sales Order. If any Items in your table are Sales BOM (packets), then the “Packing List” will contain the exploded (detailed) list of your Items.

#### Reservation and Warehouses

If your Sales Order contains Items for which inventory is tracked (Is Stock Item is “Yes”) then, ERPNext will ask you for “Reservation Warehouse”. If you have set a default Warehouse for the Item, it will automatically set this Warehouse here.

This “reserved” quantity will help you project what is the quantity you need to purchase based on all your commitments.

#### Sales Team

**Sales Partner:** If this Sale was booked via a Sales Partner, you can update the Sales Partner’s details with commission and other info that you can aggregate.

**Sales Persons:** ERPNext allows you to tag multiple Sales Persons who may have worked on this deal. You can also split the amount in targets of different Sales Persons and track how much incentives they earned on this deal.

#### Next Steps

Once your “Submit” your Sales Order, you can now trigger different aspects of your organization:

- To begin purchase click on “Make Purchase Request”
- To make a shipment entry click on “Make Delivery Note”
- To bill, make “Make Sales Invoice”
- To stop further process on this Sales Order, click on “Stop”

#### Submission

Sales Order is a “Submittable” transaction. See Document Stages. You will be able to execute dependent steps (like making a Delivery Note) only after “Submitting” this Sales Order.

