A customer, who is sometimes known as a client, buyer, or purchaser is the one
who receives goods, services, products, or ideas, from a seller for a monetary
consideration. A customer can also receive goods or services from a vendor or
a supplier for other valuable considerations.

You can either directly create your Customers via

> Selling > Customer

or upload it via the Data Import Tool.

<img class="screenshot" alt="Customer" src="/assets/manual_erpnext_com/img/crm/customer.png">

> Note: Customers are separate from Contacts and Addresses. A Customer can
have multiple Contacts and Addresses.

### Contacts and Addresses

Contacts and Addresses in ERPNext are stored separately so that you can
attach multiple Contacts or Addresses to Customers and Suppliers.

Read [Contact](/contents/crm/contact) to know more.

### Integration with Accounts

In ERPNext, there is a separate Account record for each Customer, for each
Company.

When you create a new Customer, ERPNext will automatically create an Account
Ledger for the Customer under “Accounts Receivable” in the Company set in the
Customer record.

> Advanced Tip: If you want to change the Account Group under which the
Customer Account is created, you can set it in the Company master.

If you want to create an Account in another Company, just change the Company
value and “Save” the Customer again.

### Customer Settings

You can link a Price List to a Customer (select “Default Price List”), so that
when you select that Customer, the Price List will be automatically selected.

You can set “Credit Days”, so that it is automatically set due date in the Sales
Invoices made against this Customer. Credit Days can be defined as fixed days or last day of the next month based on invoice date.

You can set how much credit you want to allow for a Customer by adding the
“Credit Limit”. You can also set a global “Credit Limit” in the Company
master. Classifying Customers

ERPNext allows you to group your Customers using [Customer Group](/contents/crm/setup/customer-group) 
and also divide them into [Territories](/contents/crm/setup/territory)
Grouping will help you get better analysis of your data and
identify which Customers are profitable and which are not. Territories will
help you set sales targets for the respective territories.
You can also mention [Sales Person](/contents/crm/setup/sales-person) against a customer.

### Sales Partner

A Sales Partner is a third party distributor / dealer / commission agent /
affiliate / reseller who sells the companies products, for a commission. This
is useful if you make the end sale to the Customer, involving your Sales
Partner.

If you sell to your Sales Partner who in-turn sells it to the Customer, then
you must make a Customer instead.

{next}
