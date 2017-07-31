# Subcontracting

Subcontracting is a type of job contract that seeks to outsource certain types
of work to other companies. It allows work on more than one phase of the
project to be done at once, often leading to a quicker completion.
Subcontracting is practiced by various industries. For example, manufacturers
making a number of products from complex components subcontract certain
components and package them at their facilities.  

If your business involves outsourcing certain processes to a third party
Supplier, where you buy the raw material from, you can track this by using the
sub-contracting feature of ERPNext.  

### Setup Sub-Contracting:

  1. Create separate Items for the unprocessed and the processed product. For example if you supply unpainted X to your Supplier and the Supplier returns you X, you can create two Items: “X-unpainted” and “X”.
  2. Create a Warehouse for your Supplier so that you can keep track of Items supplied. (you may supply a months worth of Items in one go).
  3. For the processed Item, in the Item master, set “Is Sub Contracted Item” to “Yes”.

<img class="screenshot" alt="Sub-Contracting" src="/docs/assets/img/manufacturing/subcontract.png">
  

__Step 1:__ Make a Bill of Materials for the processed Item, with the unprocessed
Items as sub-items. For example, If you are manufacturing a pen, the processed
pen will be named under Bill of Materials(BOM), whereas, the refill, knob, and
other items which go into the making of pen, will be categorized as sub-items.

<img class="screenshot" alt="Sub-Contracting" src="/docs/assets/img/manufacturing/subcontract2.png">

__Step 2:__ Make a Purchase Order for the processed Item. When you “Save”, in the “Raw Materials Supplied”, all your un-processed Items will be updated based on your Bill of Materials.

<img class="screenshot" alt="Sub-Contracting" src="/docs/assets/img/manufacturing/subcontract3.png">

__Step 3:__ Make a Stock Entry to deliver the raw material Items to your Supplier.

<img class="screenshot" alt="Sub-Contracting" src="/docs/assets/img/manufacturing/subcontract4.png">

__Step 4:__ Receive the Items from your Supplier via Purchase Receipt. Make sure to check the “Consumed Quantity” in the “Raw Materials” table so that the
correct stock is maintained at the Supplier’s end.

<img class="screenshot" alt="Sub-Contracting" src="/docs/assets/img/manufacturing/subcontract5.png">

> Note 1: Make sure that the “Rate” of processed Item is the processing rate
(excluding the raw material rate).

> Note 2: ERPNext will automatically add the raw material rate for your
valuation purpose when you receive the finished Item in your stock.

### Video Help

<iframe width="660" height="371" src="https://www.youtube.com/embed/ThiMCC2DtKo" frameborder="0" allowfullscreen></iframe>

{next}
