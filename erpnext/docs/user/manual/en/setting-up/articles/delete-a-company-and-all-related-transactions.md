<h1>Delete All Related Transactions for a organization</h1>

Often, users setup all the master data and then create a few dummy records. Then they want to delete the dummy records and the organization and start over again, keeping the other master data like Customers, Items, BOMs intact.

Version 5 onwards, you can now delete all dummy transactions related to a organization.

To do that, open the organization record.
 
`Setup > Accounts > organization` or  `Accounts > Setup > organization`

In organization master, click on the **Delete organization Transactions** button right at the bottom of the form. Then you must re-type the organization name to confirm if you are sure you want to continue with this.

This action will wipe out all the data related to that organization like Quotation, Invoices, Purchase Orders etc. So be careful

![Delete organization]({{docs_base_url}}/assets/img/articles/delete-organization.png)


**Note:** If you want to delete the organization record itself, the use the normal "Delete" button from Menu options. It will also delete Chart of Accounts, Chart of Cost Centers and Warehouse records for that organization.

<!-- markdown -->