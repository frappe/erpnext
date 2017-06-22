# Sales Order

The Sales Order confirms your sales and triggers purchase (**Material
Request**) shipment (**Delivery Note**), billing (**Sales Invoice**) and
manufacturing (**Production Plan**)

A Sales Order is usually a binding Contract with your Customer.

Once your customer confirms the Quotation you can convert your Quotation into
a Sales Order.

### Sales Order Flow-Chart

![Sales Order]({{docs_base_url}}/assets/img/buying/sales-order-f.jpg)

To create a new Sales Order go to:

> Selling > Sales Order > New Sales Order

### Creating Sales Order from Quotation

You can also create a Sales Order from a submitted Quotation.

<img class="screenshot" alt="Make Sales Order from Quotation" src="{{docs_base_url}}/assets/img/selling/make-SO-from-quote.png">

Or you can create a new Sales Order and pull details from an Quotation.

<img class="screenshot" alt="Make Sales Order from Quotation" src="{{docs_base_url}}/assets/img/selling/make-so.gif">

Most of the information in your Sales Order is the same as the Quotation.
There are a few amongst other things that a Sales Order will ask you to
update.

  * Expected date of delivery.
  * Customer Purchase Order number: If your customer has sent you a Purchase Order, you can update its number for future reference (in billing).

### Packing List

The “Packing List” table will be automatically updated when you “Save” the
Sales Order. If any Items in your table are Product Bundle (packets), then the
“Packing List” will contain the exploded (detailed) list of your Items.

### Reservation and Warehouses

If your Sales Order contains Items for which inventory is tracked (Is Stock
Item is “Yes”) then, ERPNext will ask you for “Reservation Warehouse”. If you
have set a default Warehouse for the Item, it will automatically set this
Warehouse here.

This “reserved” quantity will help you project what is the quantity you need
to purchase based on all your commitments.

### Taxes

To add taxes to your Quotation, you can select a **Sales Taxes and Charges Template** or add the taxes on your own.

For e.g

<img class="screenshot" alt="Taxes and Charges" src="{{docs_base_url}}/assets/img/selling/taxes-and-charges.gif">

To understand taxes in detail visit [Taxes]({{docs_base_url}}/user/manual/en/setting-up/setting-up-taxes.html).

### Sales Team

**Sales Partner:** If this Sale was booked via a Sales Partner, you can update the Sales Partner’s details with commission and other info that you can aggregate.

**Sales Persons:** ERPNext allows you to tag multiple Sales Persons who may have worked on this deal. You can also split the amount in targets of different Sales Persons and track how much incentives they earned on this deal.

### Recurring Sales Orders

If you have a recurring contract with a Customer where you are required to generate a Sales Order on a monthly, quarterly, half-yearly or annual basis, you can check the “Convert To Recurring Order” box. 

Here you can fill in the details like; of how frequently you want to generate an Order in the 'Recurring Type' field, specify the day of of the month on which the Order needs to be generated in the 'Repeat On Day Of Month' field and the date on which the recurring orders should stop in the 'End Date' field.

**Recurring Type:** Here you can update how frequently you want to generate an Order.

**Repeat On Day Of Month:** You can specify the day of of the month on which the Order needs to be generated.

**End Date:** The date on which the recurring orders should stop can be specified here.

On updating the Sales Order, a Recurring ID will be generated which will be same for all recurring orders generated from this particular Sales Order.

ERPNext will automatically create new Order and mail a notification to the Email Addresses you set in the 'Notification Email Address'field.

<img class="screenshot" alt="Reccuring Sales Order" src="{{docs_base_url}}/assets/img/selling/recurring-sales-order.png">

### Next Steps

Once you “Submit” your Sales Order, you can now trigger different aspects of
your organization:

  * To begin purchase click on “Make Purchase Request”
  * To make a shipment entry click on “Make Delivery Note”
  * To bill, make “Make Sales Invoice”
  * To stop further process on this Sales Order, click on “Stop”

### Submission

Sales Order is a “Submittable” transaction. See Document Stages. You will be
able to execute dependent steps (like making a Delivery Note) only after
“Submitting” this Sales Order.

### Sales Order with Order type Maintenance

When the 'Order Type' of the Sales Order is 'Maintenance' follow the steps
given below:

__Step 1:__ Enter Currency, Price list and Item details.

__Step 2:__ Mention taxes and other information.

__Step 3:__ Save and Submit the form

__Step 4:__ Once the form is submitted, the Action button will provide three
choices.i) Maintenance Visit ii) Maintenance Schedule iii) Invoice.



> **Note 1:**   
By clicking on the Action button and selecting 'Maintenance Visit' you can directly fill the visit form. The Sales Order details will be fetched directly.    

> **Note 2:**    
By clicking on the Action button and selecting 'Maintenance Schedule' you can fill the schedule details. The Sales Order details will be fetched directly.

> **Note 3:**    
By clicking on the Invoice button you can make an Invoice for your
services . The sales orders details will be fetched directly.

{next}
