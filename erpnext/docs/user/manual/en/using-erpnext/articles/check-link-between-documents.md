<h1>Checking Link Between Documents</h1>

Linked With function in ERPNext allows you checking a document is linked with which other documents. You will find Linked With function in the every document.

![linked with icon]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-02-10 at 5.32.56 pm.png)

####Scenario

If you need to check which Delivery Note and Sales Invoice has been created against Sales Order, you should open Sales Order document, and click on Linked With in it.

![Sales Order Links]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-02-10 at 5.35.44 pm.png)

Since Sales Order is a centralize transaction, using linked-with option in the Sales Order, you can track complete deal, like billing done, purchases made, manufacturing development against this particular order.

####How It Works?

When you check Linked With in for a Sales Order, it lists all the record where this Sales Order ID is updated. It will not show documents where this Sales Order Id is entered as text, and not in the link field.

####Backward Links

If I check Linked With in the Delivery Note, will it list Sales Order created before this delivery  note?

Linked With function works only for the forward linkages. For the backward linkages, you should check current document itself. In the Delivery Note, you can check Item table to see which Sales Order it is linked with.

![Linked With Backward]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-02-10 at 5.36.23 pm.png)

<!-- markdown -->