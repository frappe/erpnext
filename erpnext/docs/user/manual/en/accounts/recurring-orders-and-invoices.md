#Recurring Orders and Invoices

If you have a contract with a **Customer** where you bill the Customer on a monthly, quarterly, half-yearly or annual basis, you should use recurring feature in orders and invoices. 

#### Scenario:

Subscription for your hosted ERPNext account requires yearly renewal. We use Sales Order for generating proforma invoices. To automate proforma invoicing for renewal, we set original Sales Order as recurring. Recurring proforma invoice is created automatically just before customer's account is about to expire, and requires renewal. This recurring Proforma Invoice is also emailed automatically to the customer.

Feature of setting document as recurring is available in Sales Order, Sales Invoice, Purchase Order and Purchase Invoice.

Option to set document as recurring will be visible only after submission. Recurring is last section in document. Check **Is Recurring** to set document as recurring.

<img alt="Recurring Invoice" class="screenshot" src="/docs/assets/img/accounts/recurring.gif">

**From Date and To Date:** This defines contract period with the customer.

**Repeat on the Day of Month:** If recurring type is set as Monthly, then it will be day of the month on which recurring invoice will be generated.

**End Date:** Date after which auto-creation of recurring invoice will be stopped.

**Notification Email Address:** Email Addresses (separated by comma) on which recurring invoice will be emailed when auto-generated.

**Recurring ID:** Recurring ID will be original document id which will be linked to all corresponding recurring document. For example, original Sales Invoice's id will be updated into all recurring Sales Invoices.

**Recurring Print Format:** Select a print format to define document view which should be emailed to customer.

####Exception Handling:

In a situation where recurring invoice is not created successfully, user with System Manager role is notified about it via email. Also the document on which recurring event failed, "Is Recurring" field is unchecked for it. This means system doesn't try creating recurring invoice for that document again.
	
Failure in creation of recurring invoice could be due to multiple reasons like wrong Email Address mentioned in the Email Notification field in Recurring section etc.

On receipt of notification, if cause of failure is fixed (like correcting Email Address) within 24 hours, then recurring invoice will be generated automatically. If issue is not fixed within the said time, then document should be created for that month/year manually.

{next}
