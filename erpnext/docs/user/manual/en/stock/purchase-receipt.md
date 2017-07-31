# Purchase Receipt

Purchase Receipts are made when you accept material from your Supplier usually
against a Purchase Order.

You can also accept Purchase Receipts directly ( Set Purchase Order
Required as “No” in Global Defaults).

You can make a Purchase Receipt directly from:

> Stock > Purchase Receipt > New Purchase Receipt

or from a “Submitted” Purchase Order, by clicking on “Make Purchase Receipt”.

<img class="screenshot" alt="Purchase Receipt" src="{{docs_base_url}}/assets/img/stock/purchase-receipt.png">

### Rejections

In the Purchase Receipt, you are required to enter whether all the materials
you receive are of acceptable quality (in case you check). If you have any
rejections, update the “Rejected Quantity” column in the Items table.

If you reject, you are required to enter a “Rejected Warehouse” to indicate
where you are storing the rejected Items.

### Quality Inspections

If for certain Items, it is mandatory to record Quality Inspections (if you
have set it in your Item master), you will need to update the “Quality
Inspection No” (QA No) column. The system will only allow you to “Submit” the
Purchase Receipt if you update the “Quality Inspection No”.

### UOM Conversions

If your Purchase Order for an Item is in a different Unit of Measure (UOM)
than what you stock (Stock UOM), then you will need to update the “UOM
Conversion Factor”. 

### Currency Conversions

Since the incoming Item affects the value of your inventory, it is important
to convert it into your base Currency, if you have ordered in another
Currency. You will need to update the Currency Conversion Rate if applicable.

### Taxes and Valuation

Some of your taxes and charges may affect your Items value. For example, a Tax
may not be added to your Item’s valuation, because if you sell the Item, you
will have to add the tax at that time. So make sure to mark all your taxes in
the Taxes and Charges table correctly for accurate valuation.

### Serial Numbers and Batches

If your Item is serialized or batched, you will have to enter Serial Number
and Batch in the Item's table. You are allowed to enter multiple Serial Numbers
in one row (each on a separate line) and you must enter the same number of
Serial Numbers as the quantity. You must enter each Batch number on a separate
line.

* * *

#### What happens when the Purchase Receipt is “Submitted”?

A Stock Ledger Entry is created for each Item adding the Item in the Warehouse
by the “Accepted Quantity” If you have rejections, a Stock Ledger Entry is
made for each Rejection. The “Pending Quantity” is updated in the Purchase
Order.

* * *

#### Adding value to your Items post Purchase Receipt:

Some times, certain expenses that add value to your purchased Items are known
only after a while. Common example is, if you are importing the Items, you
will come to know of Customs Duty etc only when your “Clearing Agent” sends
you a bill. If you want to attribute this cost to your purchased Items, you
will have to use the Landed Cost Wizard. Why “Landed Cost”? Because it
represents the charges that you paid when it landed in your possession.

{next}
