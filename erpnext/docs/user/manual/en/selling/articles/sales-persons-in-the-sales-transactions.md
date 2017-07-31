# Sales Persons In The Sales Transactions

#Sales Persons in the Sales Transactions

In ERPNext, Sales Person master is maintained in [tree structure]({{docs_base_url}}/user/manual/en/setting-up/articles/managing-tree-structure-masters.html). Sales Person is selectable in all the sales transactions.

Sales Persons can be updated in the Customer master as well. On selection of Customer in the transactions, Sales Persons as updated in the Customer will fetch into sales transaction.

<img class="screenshot" alt="Sales Person Customer" src="{{docs_base_url}}/assets/img/articles/sales-person-transaction-1.png">

####Sales Person Contribution

If more than one sales persons are working together on an order, then contribution (%) should be set for each Sales Person.

<img class="screenshot" alt="Sales Person Order" src="{{docs_base_url}}/assets/img/articles/sales-person-transaction-2.png">

On saving transaction, based on the Net Total and Contriution (%), `Contribution to Net Total` will be calculated for each Sales Person.

<div class=well>Total % Contribution for all Sales Person must be 100%. If only one Sales Person is selected, then % Contribution will be 100.</div>

####Sales Person Transaction Report

Check Sales Person's Transaction report from:

`Selling > Standard Reports > Sales Personwise Transaction Summary`

This report can be generated based on Sales Order, Delivery Note and Sales Invoice. It will give you total amount of sale made by an employe.

<img class="screenshot" alt="Sales Person Report" src="{{docs_base_url}}/assets/img/articles/sales-person-transaction-3.png">

####Sales Person wise Commission

ERPNext only provide total amount of sale made by a Sales Person. If you offer commission to Sales Person, you should add Sales Person as Sales Partners in ERPNext. For Sales Partners, you can define Commission (%). On selected on Sales Partner in a sales transction, based on Net Total, Commission Amount is calculated as well. You can check Sales Partner's commission report from:

`Accounts > Standard Reports > Sales Partners Commission`

<!-- markdown -->