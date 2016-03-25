Payments made against Sales Invoices or Purchase Invoices can be made by
clicking on “Make Payment Entry” button on “Submitted” invoices.

  1. Update the “Bank Account” (you can also set the default account in the Company master).
  2. Update posting date.
  3. Enter the cheque number, cheque date.
  4. Save and Submit.

<img class="screenshot" alt="Manking Payment" src="{{docs_base_url}}/assets/img/accounts/make-payment.png">

Payments can also be made independent of invoices by creating a new Journal
Voucher and selecting the type of payment.

#### Incoming Payment

For payments from Customers,

  * Debit: Bank or Cash Account
  * Credit: Customer

> Note: Remember to add “Against Sales Invoice” or “Is Advance” as applicable.

#### Outgoing Payment

For payments to Suppliers,

  * Debit: Supplier
  * Credit: Bank or Cash Account

### Example Payment Journal Entry

<img class="screenshot" alt="Manking Payment" src="{{docs_base_url}}/assets/img/accounts/new-bank-entry.png">

* * *

### Reconciling Cheque Payments

If you are receiving payments or making payments via cheques, the bank
statements will not accurately match the dates of your entry, this is because
the bank usually takes time to “clear” these payments. Also you may have
mailed a cheque to your Supplier and it may be a few days before it is
received and deposited by the Supplier. In ERPNext you can synchronize your
bank statements and your Journal Entrys using the “Bank Reconciliation”
tool.

To use this, go to:

> Accounts > Tools > Bank Reconciliation

Select your “Bank” Account and enter the dates of your statement. Here you
will get all the “Bank Voucher” type entries. In each of the entry on the
right most column, update the “Clearance Date” and click on “Update”.

By doing this you will be able to sync your bank statements and entries into
the system.

* * *

## Managing Outstanding Payments

In most cases, apart from retail sales, billing and payments are separate
activities. There are several combinations in which these payments are done.
These cases apply to both sales and purchases.

  * They can be upfront (100% in advance).
  * Post shipment. Either on delivery or within a few days of delivery.
  * Part in advance and part on or post delivery.
  * Payments can be made together for a bunch of invoices.
  * Advances can be given together for a bunch of invoices (and can be split across invoices).

ERPNext allows you to manage all these scenarios. All accounting entries (GL
Entry) can be made against a Sales Invoice, Purchase Invoice or Journal
Vouchers (in special cases, an invoice can be made via a Sales Invoice too).

The total outstanding amount against an invoice is the sum of all the
accounting entries that are made “against” (or are linked to) that invoice.
This way you can combine or split payments in Journal Entrys to manage the
scenarios.

### Matching Payments to Invoices

In complex scenarios, especially in the capital goods industry, sometimes
there is no direct link between payments and invoices. You send invoices to
your Customers and your Customer sends you block payments or payments based on
some schedule that is not linked to your invoices.

In such cases, you can use the Payment to Invoice Matching Tool.

> Accounts > Tools > Payment Reconciliation

In this tool, you can select an account (your Customer’s account) and click on
“Pull Payment Entries” and it will select all un-linked Journal Entrys and
Sales Invoices from that Customer.

To cancel off some payments and invoices, select the Invoices and Journal
Vouchers and click on “Reconcile”.

{next}
