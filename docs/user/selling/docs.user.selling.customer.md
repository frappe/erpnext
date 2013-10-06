---
{
	"_label": "Customer Master",
	"_title_image": "img/customers.png"
}
---
A customer, who is sometimes known as a client, buyer, or purchaser is the one who receives goods, services, products, or ideas, from a seller for a monetary consideration. A customer can also receive goods or services from a vendor or a supplier for other valuable considerations.

 You can either directly create your Customers via 

> Selling > Customer

or upload it via the Data Import Tool.



![Customer Master](img/customer.png)




> Note: Customers are separate from Contacts and Addresses. A Customer can have multiple Contacts and Addresses.

### Contacts and Addresses
￼
Contacts and Addresses in ERPNext are stored separately so that you can attach multiple Contacts or Addresses to Customers and Suppliers.

To add a Contact or Address directly from the Customer record, click on “New Contact” or “New Address”.

> Tip: When you select a Customer in any transaction, one Contact and Address gets pre-selected. This is the “Default Contact or Address”. 

To Import multiple Contacts and Addresses from a spreadsheet, use the Data Import Tool.

### Integration with Accounts

In ERPNext, there is a separate Account record for each Customer, for each Company.

When you create a new Customer, ERPNext will automatically create an Account Ledger for the Customer under “Accounts Receivable” in the Company set in the Customer record. 

> Advanced Tip: If you want to change the Account Group under which the Customer Account is created, you can set it in the Company master.

If you want to create an Account in another Company, just change the Company value and “Save” the Customer again.

### Customer Settings

You can link a Price List to a Customer (select “Default Price List”), so that when you select that Customer, the Price List will be automatically selected.

You can set “Credit Days” so that it is automatically set in the Sales Invoices made against this Customer.

You can set how much credit you want to allow for a Customer by adding the “Credit Limit”. You can also set a global “Credit Limit” in the Company master.Classifying Customers

ERPNext allows you to group your Customers and also divide them into Territories. Grouping will help you get better analysis of your data and identify which Customers are profitable and which are not. Territories will help you set sales targets for the respective territories.

### Customer Group

You can group your Customers so that you can get trend analysis for each group. Typically Customers are grouped by market segment (that is usually based on your domain).

> Tip: If you think all this is too much effort, you can leave it at “Default Customer Group”. But all this effort, will pay off when you start getting reports.
￼
An example of a sample report is given below:


![Sales Analytics](img/sales-analytics-customer.png)




### Territory

If your business operates in multiple Territories (could be countries, states or cities) it is usually a great idea to build your structure in the system. Once you group your Customers by Territories, you can set annual targets for each Item Group and get reports that will show your actual performance in the territory v/s what you had planned.

### Sales Person

Sales Persons behave exactly like Territories. You can create an organization chart of Sales Persons where each Sales Person’s target can be set individually. Again as in Territory, the target has to be set against Item Group.

### Sales Partner

A Sales Partner is a third party distributor / dealer / commission agent / affiliate / reseller who sells the companies products, for a commission. This is useful if you make the end sale to the Customer, involving your Sales Partner.

If you sell to your Sales Partner who in-turn sells it to the Customer, then you must make a Customer instead.