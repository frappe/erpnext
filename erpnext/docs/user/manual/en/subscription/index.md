If you have a contract with the Customer where your organization gives bill to the Customer on a monthly, quarterly, half-yearly or annual basis, you can use subscription feature to make auto invoicing.

<img class="screenshot" alt="Subscription" src="{{docs_base_url}}/assets/img/subscription/subscription.png">

#### Scenario

Subscription for your hosted ERPNext account requires yearly renewal. We use Sales Invoice for generating proforma invoices. To automate proforma invoicing for renewal, we set original Sales Invoice on the subscription form. Recurring proforma invoice is created automatically just before customer's account is about to expire, and requires renewal. This recurring Proforma Invoice is also emailed automatically to the customer.

To set the subscription for the sales invoice
Goto Subscription > select base doctype "Sales Invoice" > select base docname "Invoice No" > Save

<img class="screenshot" alt="Subscription" src="{{docs_base_url}}/assets/img/subscription/subscription.gif">

**From Date and To Date**: This defines contract period with the customer.

**Repeat on Day**: If frequency is set as Monthly, then it will be day of the month on which recurring invoice will be generated.

**Notify By Email**: If you want to notify the user about auto recurring invoice.

**Print Format**: Select a print format to define document view which should be emailed to customer.

**Disabled**: It will stop to make auto recurring documents against the subscription