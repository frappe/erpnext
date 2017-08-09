#Checking Link Between Documents

Links option shows one document is linked to which other documents. Check Menu for the Links options.

<img alt="Cancel Doc" class="screenshot" src="/docs/assets/img/articles/links-1.gif">

####Scenario

If you need that against Sales Order, which Delivery Note and Sales Invoice has been created, you should open Sales Order document, and check Links. Same way, you can also check Purchase Order, and find which Purchase Receipt and Purchase Ivoice is linked with it.

####How It Works?

When you check Links for a Sales Order, it lists all the record where this Sales Order ID is linked. When Delivery Note is created against Sales Order, then Sales Order link is updated in the Delivery Note Item table.

####Backward Links

If I check Links in the Purchase Receipt, will it list Purchase Order from which this Purchase Receipt was created?

Links only shows forward linkages. For the backward links, you should check current document itself. In the Purchase Receipt Item table table, you can check which Purchase Order it is linked to.

<img alt="Cancel Doc" class="screenshot" src="/docs/assets/img/articles/links-2.gif">

<!-- markdown -->