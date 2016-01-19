<h1>Auto Creation of Material Request</h1>

<h1>Auto Creation of Material Request</h1>

ERPNext allows you to define item-wise and warehouse-wise reorder level in the item master. Reorder level is the item's stock level at which item should be re-ordered.

With reorder level, you can also define what should be the next action. Either new purchase or transfer from another warehouse. Based on setting in Item master, purpose will be updated in the Material Request as well.

![Item Reorder Level]({{docs_base_url}}/assets/img/articles/$SGrab_391.png)

You can have Material Request automatically created for items whose stock level reaches re-order level. You can enable this feature from:

`Stock > Setup > Stock Settings`

![Item Reorder Stock Setting]({{docs_base_url}}/assets/img/articles/$SGrab_392.png)

A separate Material Request will be created for each item. User with Purchase Manager's role will be informed about these Material Request. He can further process this Material Request, and create Supplier Quotation and Purchase Order against it.

If auto creation of Material Request is failed, Purchase Manager will be informed about error message via email. One of the most encountered error message is:

**An error occurred for certain Items while creating Material Requests based on Re-order level.
Date 01-04-2015 not in any Fiscal Year.**

One of the reason of error could be Fiscal Year as well. Click [here](https://erpnext.com/kb/accounts/fiscal-year-error) to learn more about it.
<!-- markdown -->