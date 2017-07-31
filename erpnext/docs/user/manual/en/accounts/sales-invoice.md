# Sales Invoice

A Sales Invoice is a bill that you send to your customers, against which the customer processes the payment. Sales Invoice is an accounting transaction. On submission of Sales Invoice,  the system updates the receivable and books income against a Customer Account.

You can create a Sales Invoice directly from

> Accounts > Billing > Sales Invoice > New Sales Invoice

or you can Make a new Sales Invoice after you submit the Delivery Note.

<img class="screenshot" alt="Sales Invoice" src="/docs/assets/img/accounts/sales-invoice.png">

#### Accounting Impact

All Sales must be booked against an “Income Account”. This refers to an
Account in the “Income” section of your Chart of Accounts. It is a good
practice to classify your income by type (like product income, service income
etc). The Income Account must be set for each row of the Items table.

> Tip: To set default Income Accounts for Items, you can set it in the Item or
Item Group.

The other account that is affected is the Account of the Customer. That is
automatically set from “Debit To” in the heading section.

You must also mention the Cost Centers in which your Income must be booked.
Remember that your Cost Centers tell you the profitability of the different
lines of business or product. You can also set a default Cost Center in the
Item master.

#### Accounting entries (GL Entry) for a typical double entry “Sale”:

When booking a sale (accrual):

**Debit:** Customer (grand total) **Credit:** Income (net total, minus taxes for each Item) **Credit:** Taxes (liabilities to be paid to the government)

> To see entries in your Sales Invoice after you “Submit”, click on “View
Ledger”.

#### Dates

Posting Date: The date on which the Sales Invoice will affect your books of
accounts i.e. your General Ledger. This will affect all your balances in that
accounting period.

Due Date: The date on which the payment is due (if you have sold on credit).
This can be automatically set from the Customer master.

#### Recurring Invoices

If you have a contract with a Customer where you bill the Customer on a
monthly, quarterly, half-yearly or annual basis, you can check the “Recurring
Invoice” box. Here you can fill in the details of how frequently you want to
bill this Invoice and the period for which the contract is valid.

ERPNext will automatically create new Invoices and mail it to the Email Addresses
you set.

#### POS Invoices

Consider a scenario where retail transaction is carried out. For e.g: A retail shop.
If you check the **Is POS** checkbox, then all your **POS Profile** data is fetched
into the Sales Invoice and you can easily make payments.
Also, if you check the **Update Stock** the stock will also update automatically,
without the need of a Delivery Note.

<img class="screenshot" alt="POS Invoice" src="/docs/assets/img/accounts/pos-sales-invoice.png">

#### Billing Timesheet with Project

If you want to bill employees working on Projects on hourly basis (contract based),
they can fill out Timesheets which consists their billing rate. When you make a new
Sales Invoice, select the Project for which the billing is to be made, and the
corresponding Timesheet entries for that Project will be fetched.

<img class="screenshot" alt="POS Invoice" src="/docs/assets/img/accounts/billing-timesheet-sales-invoice.png">

* * *

#### "Pro Forma" Invoice

If you want to give an Invoice to a Customer to make a payment before you
deliver, i.e. you operate on a payment first basis, you should create a
Quotation and title it as a “Pro-forma Invoice” (or something similar) using
the Print Heading feature.

“Pro Forma” means for formality. Why do this? Because if you book a Sales
Invoice it will show up in your “Accounts Receivable” and “Income”. This is
not ideal as your Customer may or may not decide to pay up. But since your
Customer wants an “Invoice”, you could give the Customer a Quotation (in
ERPNext) titled as “Pro Forma Invoice”. This way everyone is happy.

This is a fairly common practice. We follow this at Frappé too.
{next}
