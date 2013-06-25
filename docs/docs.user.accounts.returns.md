---
{
	"_label": "Handling Returns"
}
---
Returns are a part of doing business. Your Customers may return Items in exchange of other Items or money back or you may return Items to your Supplier. In each case there could be a variety of scenarios.

### Credit and Debit Notes

Credit Notes are given to your Customers against a return that can be redeemed as cash or adjusted in another purchase. You can create a Journal Voucher of type Credit Note as follows:

- Debit: Income
- Credit: Customer

Similarly if you are deducting an amount from your Supplier’s bill due to rejection or similar, you can issue a Debit Note to your Supplier. You can adjust the Debit Note against another pending Purchase Invoice (in which case, remember to set the “Against Purchase Invoice” column or return the money. In the second case you will have to create a new payment entry (Journal Voucher) when you receive the money. Entry for a Debit Note would be:

- Debit: Supplier
- Credit: Expense

> If Items are also returned, remember to make a Delivery Note or Stock Entry for the Items.

### Exchange

If there is an exchange with your Customer, you can create a new POS type Sales Invoice in which the returning item has a negative quantity and the selling item has a positive quantity. In this way your taxes will also be adjusted against the return.

### Sales and Purchase Return Wizard

This is a tool that can help you automate the entry for this process. Go to:

> Accounts > Tools > Sales and Purchase Return