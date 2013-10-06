---
{
	"_label": "Supplier Master"
}
---
Suppliers are companies or individuals who provide you with products or services. They are treated in exactly the same manner as Customers in ERPNext.


You can create a new Supplier via:

> Buying > Supplier > New Supplier

![Supplier](img/supplier.png)


### Contacts and Addresses

 Contacts and Addresses in ERPNext are stored separately so that you can attach multiple Contacts or Addresses to Customers and Suppliers. To add a Contact or Address go to Buying and click on “New Contact” or “New Address”.


> Tip: When you select a Supplier in any transaction, one Contact and Address gets pre-selected. This is the “Default Contact or Address”. So make sure you set your defaults correctly!

### Integration with Accounts

In ERPNext, there is a separate Account record for each Supplier, of Each company.

When you create a new Supplier, ERPNext will automatically create an Account Ledger for the Supplier under “Accounts Receivable” in the Company set in the Supplier record. 

> Advanced Tip: If you want to change the Account Group under which the Supplier Account is created, you can set it in the Company master.

If you want to create an Account in another Company, just change the Company value and “Save” the Supplier again.


> Buying > Contact > New Contact

![Contact](img/contact.png)




You can also import from the Data Import Tool