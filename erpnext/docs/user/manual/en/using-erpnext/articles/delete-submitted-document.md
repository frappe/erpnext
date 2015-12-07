<h1>Delete Submitted Document</h1>

ERPNext allows you to assign deletion permission exclusively to User. Only those users will be able to delete records. Click [here](/user-guide/setting-up/permissions/role-based-permissions) to learn more about permissions.

To delete any document from system you should cancel all linked documents. For example if you need to delete Sales Order, but Delivery Note and Sales Invoice has already been created against that Sales Order. Then you should cancel and delete documents in reverse order, i.e. Sales Invoice, Delivery Note and then Sales Order. If payment entry was also made against Sales Invoice, then you should first Cancel and Delete that Journal Voucher, and then come to Sales Invoice.

Following are step to delete submitted documents.

####1. Cancel Document

To be able to delete Submitted document, it must be cancelled first. After document is cancelled, you will find option to delete it.

![Cancel Sales Order]({{docs_base_url}}/assets/img/articles/Selection_064.png)

####2. Delete Document

After cancellation, go to File menu and click on Delete option.

![Cancel Sales Order]({{docs_base_url}}/assets/img/articles/Selection_066.png)

#### Deleting from List

For bulk deletion, you can select multiple Cancelled records and delete them at once from the list.

![Cancel Sales Order List]({{docs_base_url}}/assets/img/articles/Selection_069.png)

<!-- markdown -->