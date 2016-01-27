#Sales Persons in the Sale Transactions

In ERPNext, Sales Person master is maintained in [tree structure]({{docs_base_url}}/user/manual/en/setting-up/articles/managing-tree-structure-masters.html). Sales Person table is available in all the Sales transactions where you can select Sales Person who worked on that specific sales transaction.

Sales Persons can be updated in the Customer master as well. On selection of Customer in the transactions, default Sales Persons for that Customer will be auto-fetched.

<img class="screenshot" alt="Sales Person Customer" src="{{docs_base_url}}/assets/img/selling/sales-person-transaction-1.png">

####Sales Person Contribution

If more than one sales persons are working together on an order, then contribution % should also for each Sales Person, based on their effort.

<img class="screenshot" alt="Sales Person Order" src="{{docs_base_url}}/assets/img/selling/sales-person-transaction-2.png">

On saving transaction, based on the Net Total and %Contriution, Contribution to Net Total will be calculated for each Sales Person.

<div class=well>Total % Contribution for all Sales Person must be 100%. If only one Sales Person is selected, then % Contribution will be 100.</div>

####Sales Person Transaction Report

You can check Sales Person Transaction Report from:

`Selling > Standard Reports > Sales Personwise Transaction Summary`

This report can be generated based on Sales Order, Delivery Note and Sales Invoice. It will give you total amount of sales made by an employee over a period. 

<img class="screenshot" alt="Sales Person Report" src="{{docs_base_url}}/assets/img/selling/sales-person-transaction-3.png">

####Sales Person wise Commission

ERPNext doesn't calculate commission payable to an Employee, but only provide total amount of sales made by him/her. As a work around, you can add your Sales Person as Sales Partner, as commission calculation feature is readily available in ERPNext. You can check Sales Partner's Commission report from 

`Accounts > Standard Reports > Sales Partners Commission`

####Disable Sales Person Feature

If you don't track sales person wise performance, and doesn't wish to use this feature, you can disable it from:

`Setup > Customize > Features Setup` 

<img class="screenshot" alt="Disable Sales Person" src="{{docs_base_url}}/assets/img/selling/sales-person-transaction-4.png">

<!-- markdown -->