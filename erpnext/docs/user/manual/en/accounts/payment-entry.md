# Payment Entry

Payment Entry can be made against following transactions.

  1. Sales Invoice.
  2. Purchase Invoice.
  3. Sales Order (Advance Payment)
  4. Purchase Order (Advance Payment)

####Step 1: Make Payment

On submitting a document against which Payment Entry can be made, you will find Make Payment button.

<img class="screenshot" alt="Making Payment" src="/docs/assets/img/accounts/payment-entry-1.png">

####Step 2: Mode of Payment

In the Payment Entry, select Mode of Payment (eg: Bank, Cash, Wire Transfer). In the Mode of Payment master, default Account can be set. This default payment Account will fetch into Payment Entry.

<img class="screenshot" alt="Making Paymentt" src="/docs/assets/img/accounts/payment-entry-2.gif">

####Step 3: Payment Amount

Enter actual payment amount received from the Customer or paid to the Supplier.

<img class="screenshot" alt="Making Payment" src="/docs/assets/img/accounts/payment-entry-3.png">

####Step 4: Allocate Amount

If creating Payment Entry for the Customer, Payment Amount will be allocated against Sales Invoice.

<img class="screenshot" alt="Making Payment" src="/docs/assets/img/accounts/payment-entry-4.gif">

On the same lines, when creating Payment Entry for a Supplier, Payment Amount will be allocated against Purchase Invoice.

You Entry can be created directly from `Account > Payment Entry > New`. In the new entry, on selection of the Party (Customer/Supplier), all the outstanding Invoices and open Orders will be fetched for party. The Payment Amount will be auto-allocated, preferably against invoice.

####Step 5: Deductions

When making payment entry, there could be some difference in the actual payment amount and the invoice outstanding. This difference could be due to rounding error, or change in the currency exchange rate. You can set an Account here where this difference amount will be booked.

<img class="screenshot" alt="Making Payment" src="/docs/assets/img/accounts/payment-entry-5.gif">

####Step 6: Submit

Save and Submit Payment Entry. On submission, outstanding will be updated in the Invoices. 

<img class="screenshot" alt="Making Payment" src="/docs/assets/img/accounts/payment-entry-8.png">

If payment entry was created against Sales Order or Purchase Order, field Advance Paid will be updated in them. when creating Payment invoice against those transactions, Payment Entry will auto-update in that Invoice, so that you can allocate invoice amount against advance payment entry.

For incoming payment, accounts posting will be done as following.

  * Debit: Bank or Cash Account
  * Credit: Customer (Debtor)

For outgoing payment:

  * Debit: Supplier (Creditor)
  * Credit: Bank or Cash Account

###Multi Currency Payment Entry

ERPNext allows you maintain accounts and invoicing in the [multiple currency](/docs/user/manual/en/accounts/multi-currency-accounting.html). If invoice is made in the party currency, Currency Exchange Rate between companies base currency and party currency is also entered in the invoice. When creating Payment Entry against that invoice, you will again have to mention the Currency Exchange Rate at the time of payment.

<img class="screenshot" alt="Making Payment" src="/docs/assets/img/accounts/payment-entry-6.png">

Since Currency Exchange Rate is fluctuating all the time, it can lead to difference in the payment amount against invoice total. This difference amount can be booked in the Currency Exchange Gain/Loss Amount.

<img class="screenshot" alt="Making Payment" src="/docs/assets/img/accounts/payment-entry-7.png">

Payments can also be made independent of invoices by creating a new Payment Entry.

###Internal Intransfer

Following internal transfers can be managed from the Payment Entry.

1. Bank - Cash
2. Cash - Bank
3. Cash - Cash
4. Bank - Bank

<img class="screenshot" alt="Making Payment" src="/docs/assets/img/accounts/payment-entry-9.png">

###Difference between Payment Entry and Journal Entry?

 1. Journal Entry requires understanding of which Account will get Debited or Credited. In the Payment Entry, it is managed in the backend, hence simpler for the User.
 2. Payment Entry is more efficient in managing payment in the foreign currency.
 3. Journal Entry can still be used for:
	- Updating opening balance in an Accounts.
	- Fixed Asset Depreciation entry.
	- For adjusting Credit Note against Sales Invoice and Debit Note against Purchase Invoice, incase there is no payment happening at all.

* * *

## Managing Outstanding Payments

In most cases, apart from retail sales, billing and payments are separate activities. There are several combinations in which these payments are done. These cases apply to both sales and purchases.

  * They can be upfront (100% in advance).
  * Post shipment. Either on delivery or within a few days of delivery.
  * Part in advance and part on or post delivery.
  * Payments can be made together for a bunch of invoices.
  * Advances can be given together for a bunch of invoices (and can be split across invoices).

ERPNext allows you to manage all these scenarios. All accounting entries (GL Entry) can be made against a Sales Invoice, Purchase Invoice or Payment Entry of advance payment (in special cases, an invoice can be made via a Sales Invoice too).

The total outstanding amount against an invoice is the sum of all the accounting entries that are made “against” (or are linked to) that invoice. This way you can combine or split payments in Payment Entry to manage the
scenarios.

{next}
