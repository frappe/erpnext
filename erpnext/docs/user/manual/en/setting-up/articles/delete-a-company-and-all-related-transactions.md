# Delete A Company And All Related Transactions

#Delete All Related Transactions for a Company

Often, users setup all the master data and then create a few dummy records. Then they want to delete the dummy records and the company and start over again, keeping the other master data like Customers, Items, BOMs intact.

Version 5 onwards, you can now delete all dummy transactions related to a company.

To do that, open the company record.
 
`Setup > Accounts > Company` or  `Accounts > Setup > Company`

In Company master, click on the **Delete Company Transactions** button right at the bottom of the form. Then you must re-type the company name to confirm if you are sure you want to continue with this.

This action will wipe out all the data related to that company like Quotation, Invoices, Purchase Orders etc. So be careful

<img alt="Delete Transactions" class="screenshot" src="/docs/assets/img/articles/delete-transactions.gif">

**Note:** If you want to delete the company record itself, use the normal "Delete" button from Menu options. It will also delete Chart of Accounts, Chart of Cost Centers and Warehouse records for that company.

<!-- markdown -->
