<h1>Customer for Multiple Company</h1>

ERPNext allows you managing multiple companies in one ERPNext account. It is possible that you will have Customer and Supplier which would belong to more than one company of yours. While creating sales and purchase transactions, system shows result of Customer and Suppliers for that Company only.

It means if you have added (say) Wind Mills Limited as a customer for the first company, you will not be able to select it as a customer when creating Sales Order (or any other sales transaction) for another company.

There are two approach to address this scenario.

####Create Another Customer Record

You should create another Customer record for Wind Mills Limited, but for the second company.

If you try adding another customer with exact same name (as Wind Mills Limited), system will throw a validation message that, account already exist for Wind Mills Limited.

![Common Customer]({{docs_base_url}}/assets/img/articles/$SGrab_306.png)

>To be able to track customerwise receivables, ERPNext created accounting ledger for each customer in the Chart of Account, under Accounts Receivable group.

As indicated in the error message, since Account Name already exist for the first customer, you should change customer name for second customer a bit (say Wind Mills Pvt. Limited) to bring uniqueness in it. Then you will be able to save Customer correctly.

####Change Company in Existing Customer

Since creating another Customer record for the same party will be over-load in the system, you can change company in the exist Customer master of Wind Mills Limited, and re-save it. On saving customer again, it will create another accounting ledger for Wind Mills in the Chart of Account of second company.

![Common Customer Account]({{docs_base_url}}/assets/img/articles/$SGrab_307.png)

<!-- markdown -->