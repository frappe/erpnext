Purchase Invoice is the exact opposite of your Sales Invoice. It is the document
that your Supplier sends you for products delivered or services rendered. Here you
accrue expenses to your Supplier. 

To make a new Purchase Invoice, type "Purchase Invoice" in the global search bar
and select "New Purchase Invoice".

<img class="screenshot" alt="Purchase Invoice" src="{{docs_base_url}}/assets/img/accounts/purchase-invoice.png">

or click on “Make Purchase Invoice” in Purchase Order or Purchase Receipt.

<img class="screenshot" alt="Purchase Invoice" src="{{docs_base_url}}/assets/img/accounts/purchase-invoice.png">

You are required to fill in the following fields:

|  |  |
| ----- | -------- |
| Series | This represents the prefix of the identification number of each invoice. Note that it can only be set once. |
| Company | The company to bear the liability. |
| Supplier | This is the supplier to whom the company will be liable. |
| Posting date | The date of the transaction. The default posting date is the date the invoice is created on ERPNext. |
| Due Date | The date on which the payment is due. Note that that the due date cannot be earlier than the posting date. |
| Posting Time | The time of the day on the posting date. |
| Is paid | Check this check box if the invoice is partly or fully paid. |
| Edit Posting Date and Time | Check this check box if you want to change the default posting date. |

| Supplier Invoice Details |  |
| ------------------------ | --- |
| Supplier Invoice No. | The supplier's invoice number |
| Supplier Invoice Date | The date on the supplier's invoice |

| Address and Contact |  |
| ------------------- | --- |
| Select Supplier Address | The supplier's address. |
| Select Shipping Address | The supplier's shipping address. |
| Contact Person | The supplier's contact person. |

###### Currency and Price List is only relevant for foreign currency transactions.
|  Currency and Price List |  |
| ------------------------ | --- |
| Currency | The currency that the invoice is to paid in. |
| Price List | The price list to use for the invoice. |
| Exchange Rate |  The exchange rate in effect on posting date. The default is the latest exchange rate stored in ERPNext Currency Exchange for the selected currency. | 
| Price List Exchange Rate | The exchange rate to be used if price list currency is different from currency. It defaults to exchange rate. | 
| Ignore Pricing Rule | Check this check box if you want ERPNext to ignore all pricing rules for this invoice. |

|  |  |
| --- | --- |
| Update Stock | Check this check box if you want the inventory records to be updated by this invoice. Consequently, there will be no need for a delivery note to update inventory |
| Taxes and Charges | Purchase Taxes and Charges Template to use for the invoice. The tax table will be populated with it. |

| Additional Discount |  |
| ------------------- | --- |
| Apply Additional Discount On | Amount to apply discount on |
| Additional Discount Percentage | If discount is a percentage, enter the percentage here |
| Additional Discount Amount | If discount is an amount not percentage, enter the amount here |

| Advance Payments |  |
| ---------------- | --- |
| Get Advance Payments | Click this button to draw all advance payments to the supplier into the invoice. |

|Terms and Conditions |  |
| ------------------- | --- |
| Terms | Terms and Conditions template to be used for the invoice. |
| Terms and Conditions | The terms and conditions pertaining to the invoice |

###### Raw Materials is only relevant if you are using the sub-contracting feature
|  |  |
| --- | --- |
| Raw Materials Supplied | Select yes from the drop down if the invoice represents payment for a sub-contract. |
| Supplier Warehouse | The warehouse you are maintaining for the supplier. |

| Printing Settings |  |
| ----------------- | --- |
| Letter Head | The company's letterhead. |
| Print Heading | The Print Heading to use. |

| More Information |   |
| ---------------- | --- |
| Credit To | The account to use for the credit part of the transaction. |
| Status | The status of the invoice. You will usually not need to change this value. |
| Is Opening |  Check this check box if you wish to make the amount on the invoice the opening balance for the supplier. |
| Remarks | Remarks concerning the invoice. |
| Rejected Warehouse | Warehouse where you are maintaining stock of rejected items. |

###### Payments section only appears is "Is Paid" is checked
| Payments |   |
| -------- | --- |
| Mode of Payment | The mode of payment. |
| Paid Amount | The amount that has been paid on the invoice. |
| Cash/Bank Account | The ledger account from which the invoice was paid. |

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

To see entries in your Purchase Invoice after you “Submit”, click on “View
Ledger”.

If "Is Paid" is checked, extra accounting entries will be made:

Debits:
  * Supplier
  
Credits:
  * Cash/Bank Accounts

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
