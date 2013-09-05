---
{
	"_label": "Subcontracting"
}
---
If your business involves outsourcing certain processes to a third party Supplier, where you buy the raw material from, you can track this by using the sub-contracting feature of ERPNext.

To setup sub-contracting:

1. Create separate Items for the unprocessed and the processed product. For example if you supply unpainted X to your Supplier and the Supplier returns you X, you can create two Items: “X-unpainted” and “X”.
1. Create a Warehouse for your Supplier so that you can keep track of Items supplied. (you may supply a months worth of Items in one go).
1. For the processed Item, in the Item master, set “Is Sub Contracted Item” to “Yes”.



![Subcontract](img/subcontract.png)






1. Make a Bill of Materials for the processed Item, with the unprocessed Items as sub-items.For example, If you are manufacturing a pen, the processed pen will be named under Bill of Materials(BOM), whereas, the refill, knob, and other items which go into the making of pen, will be categorised as sub-items.
1. Make a Purchase Order for the processed Item. When you “Save”, in the “Raw Materials Detail”, all your un-processed Items will be updated based on your Bill of Materials.
	1. Make sure that the “Rate” of this Item is the processing rate (excluding the raw material rate).
	1. ERPNext will automatically add the raw material rate for your valuation purpose when you receive the finished Item in your stock. 
1. Make a Stock Entry to deliver the raw material Items to your Supplier.
1. Receive the Items from your Supplier via Purchase Receipt. Make sure to check the “Consumed Quantity” in the “Raw Materials” table so that the correct stock is maintained at the Supplier’s end.
