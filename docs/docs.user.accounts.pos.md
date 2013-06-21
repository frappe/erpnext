---
{
	"_label": "Point of Sale (POS) Invoice"
}
---
For retail operations, the delivery of goods, accrual of sale and payment all happens in one event, that is usually called the “Point of Sale”. 

You can make a Sales Invoice of type POS by checking on “Is POS”. When you check this, you will notice that some fields get hidden and some new ones emerge.

> Tip: In retail, you may not create a separate Customer record for each customer. You can create a general Customer called “Walk-in Customer” and make all your transactions against this Customer record.

#### Different sections of the POS

- Update Stock: If this is checked, Stock Ledger Entries will be made when you “Submit” this Sales Invoice and there is no need for a separate Delivery Note. 
- In your Items table, you will also have to update inventory information like “Warehouse” (can come as default), “Serial Number” or “Batch Number” if applicable. 
- Update “Payment Details” like your Bank / Cash Account, paid amount etc. 
- If you are writing off certain amount, for example change or you get extra change, check on “Write off Outstanding Amount” and set the Account.

#### POS Settings

If you are in retail operations, you want your Point of Sale to be as quick and efficient as possible. To do this, you can create a POS Setting for a user from:

Accounts > Point of Sale (POS) Setting

and set default values as defined.

---

#### Accounting entries (GL Entry) for a Point of Sale:

Debits:

- Customer (grand total)	
- Bank / Cash (payment)

Credits:

- Income (net total, minus taxes for each Item) 
- Taxes (liabilities to be paid to the government)
- Customer (payment)
- Write Off (optional)

To see entries after “Submit”, click on “View Ledger”.
￼
