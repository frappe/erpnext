#Auto Creation of Material Request

To prevent stockouts, you can track item's reorder level. When stock level goes below reorder level, purchase manager is notified and instructed to initiate purchase process for the item.

In ERPNext, you can update item's Reorder Level and Reorder Qty in the Item master. If same item has different reorder level, you can also update warehouse-wise reorder level and reorder qty.

<img alt="reorder level" class="screenshot" src="{{docs_base_url}}/assets/img/articles/reorder-request-1.png">

With reorder level, you can also define what should be the next action. Either new purchase or transfer from another warehouse. Based on setting in Item master, purpose will be updated in the Material Request as well.

<img alt="reorder level next action" class="screenshot" src="{{docs_base_url}}/assets/img/articles/reorder-request-2.png">

When item's stock reaches reorder level, Material Request is auto-created automatically. You can enable this feature from:

`Stock > Setup > Stock Settings`

<img alt="active auto-material request" class="screenshot" src="{{docs_base_url}}/assets/img/articles/reorder-request-3.png">

A separate Material Request will be created for each item. User with Purchase Manager's role will receive email alert about these Material Requests.

If auto creation of Material Request is failed, User with Purchase Manager role will be informed about error message. One of the most encountered error message is:

**An error occurred for certain Items while creating Material Requests based on Re-order level.**
**Date 01-04-2016 not in any Fiscal Year.**

One of the reason of error could be Fiscal Year as well. Click [here]({{docs_base_url}}/user/manual/en/accounts/articles/fiscal-year-error.html) to learn more about it.
<!-- markdown -->