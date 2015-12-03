<h1>Manage Foreign Exchange Difference</h1>

When you book Sales Invoices and Purchase invoices in multiple currencies, you will have to deal with currency difference while booking payment entry. You can easily manage this in ERPNext in following ways.  

####Add Expense Account

To mange currency difference, create Account **Foreign Exchange Gain/Loss**.

![Account]({{docs_base_url}}/assets/img/articles/Selection_577.png)

####Book Payment Entry

In the payment voucher, update invoice amount against Customer or Supplier account, then update actual payment amount against Bank/ Cash account. Add new row and select Foreign Exchange Gain/Loss to update currency difference amount.

####Scenario

Below is the Sales Invoice for a customer in Europe. The base currency of a Company in USD. Sales Invoice is  made at the exchange rate (USD to Eur) of 1.128.

![Sales Invoice]({{docs_base_url}}/assets/img/articles/Selection_576.png)

When receiving payment from the customer, exchange rate changed to 1.20. As per the update in the exchange rate, payment was for $120. Following is how payment entry will be booked to adjust the difference amount.

![Journal Entry image]({{docs_base_url}}/assets/img/articles/Selection_578.png) 

<!-- markdown -->
