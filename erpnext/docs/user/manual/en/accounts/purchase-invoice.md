# Purchase Invoice

Purchase Invoice is the exact opposite of your Sales Invoice. It is the bill
that your Supplier sends you for products or services delivered. Here you
accrue expenses to your Supplier. Making a Purchase Invoice is very similar to
making a Purchase Order.

To make a new Purchase Invoice:
> type "new purchase invoice" into the search bar then select "New Purchase 
Invoice" from the drop down

or click on “Make Purchase Invoice” in Purchase Order or Purchase Receipt.

You can also create a Purchase Invoice from:
> Accounts > Billing > Purchase Invoice > New Purchase Invoice

<img class="screenshot" alt="Purchase Invoice" src="{{docs_base_url}}/assets/img/accounts/purchase-invoice.png">

The concept of “Posting Date” is again same as Sales Invoice. “Bill No” and
“Bill Date” helps to track the bill number as set by your Supplier for
reference.

#### Is Paid option
The **Is Paid** checkbox should be checked if there is a part or full payment 
on the invoice at posting date.

#### Update Stock
The **Update Stock** checkbox should be checked if you want ERPNext to automatically
 update your inventory. Consequently, there will be no need for a Delivery Note.

#### Accounting Impact

Like in Sales Invoice, you have to enter an Expense or an Asset account for
each row in your Items table. This helps to indicate if the Item is an Asset
or an Expense. You must also enter a Cost Center. These can also be set in the
Item master.

The Purchase Invoice will affect your accounts as follows:

Accounting entries (GL Entry) for a typical double entry “purchase”:

Debits:

  * Expense or Asset (net totals, excluding taxes)
  * Taxes (/assets if VAT-type or expense again).

Credits:

  * Supplier
  
##### Accounting Treatment When **Is Paid** is checked
If **Is Paid** is checked, ERPNext will also make the following
accounting entries:

Debits:

  * Supplier
  
Credits:
  * Bank/Cash Account
  
To see entries in your Purchase Invoice after you “Submit”, click on “View
Ledger”.

* * *

#### Is purchase an “Expense” or an “Asset”?

If the Item is consumed immediately on purchase, or if it is a service, then
the purchase becomes an “Expense”. For example, a telephone bill or travel
bill is an “Expense” - it is already consumed.

For inventory Items, that have a value, these purchases are not yet “Expense”,
because they still have a value while they remain in your stock. They are
“Assets”. If they are raw-materials (used in a process), they will become
“Expense” the moment they are consumed in the process. If they are to be sold
to a Customer, they become “Expense” when you ship them to the Customer.

* * *

#### Deducting Taxes at Source

In many countries, the law may require you to deduct taxes, while paying your
suppliers. These taxes could be based on a standard rate. Under these type of
schemes, typically if a Supplier crosses a certain threshold of payment, and
if the type of product is taxable, you may have to deduct some tax (which you
pay back to your government, on your Supplier’s behalf).

To do this, you will have to make a new Tax Account under “Tax Liabilities” or
similar and credit this Account by the percent you are bound to deduct for
every transaction.

For more help, please contact your Accountant!

{next}
