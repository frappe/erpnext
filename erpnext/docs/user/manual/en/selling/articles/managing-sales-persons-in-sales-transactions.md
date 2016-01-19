<h1>Managing Sales Persons In Sales Transactions</h1>

In ERPNext, Sales Person master is maintained in [tree structure](https://erpnext.com/kb/setup/managing-tree-structure-masters). Sales Person table is available in all the Sales transactions, at the bottom of  transactions form.

If you have specific Sales Person attached to Customer, you can mention Sales Person details in the Customer master itself. On selection of Customer in the transactions, you will have Sales Person details auto-fetched in that transaction.

####Sales Person Contribution

If you have more than one sales person working together on an order, then with listing all the sales person for that order, you will also need to define contribution based on their effort. For example, Sales Person Aasif, Harish and Jivan are working on order. While Aasif and Harish followed this order throughout, Jivan got involved just in the end. Accordingly you should define % Contribution in the sales transaction as:

![Sales Person]({{docs_base_url}}/assets/img/articles/Selection_01087d575.png)

Where Sales Order Net Total is 30,000.

<div class=well>Total % Contribution for all Sales Person must be 100%. If only one Sales Person is selected, then enter % Contribution as 100% for him/her.</div>

####Sales Person Transaction Report

You can check Sales Person Transaction Report from 

`Selling > Standard Reports > Sales Person-wise Transaction Summary`

This report will be generated based on Sales Order, Delivery Note and Sales Invoice. This report will give you total amount of sales made by an employee over a period. Based on data provided from this report, you can determine incentives and plan appraisal for an employee.

![SP Report]({{docs_base_url}}/assets/img/articles/Selection_011.png)

####Sales Person wise Commission

ERPNext doesn't calculate commission payable to an Employee, but only provide total amount of sales made by him/her. As a work around, you can add your Sales Person as Sales Partner, as commission calculation feature is readily available in ERPNext. You can check Sales Partner's Commission report from 

`Accounts > Standard Reports > Sales Partners Commission`

####Disable Sales Person Feature

If you don't track sales person wise performance, and doesn't wish to use this feature, you can disable it from:

`Setup > Customize > Features Setup` 

![Feature Setup]({{docs_base_url}}/assets/img/articles/Selection_01244aec7.png)

After uncheck Sales Extras from Sales and Purchase section, refresh your ERPNext account's tab, so that forms will take effect based on your setting.

<!-- markdown -->