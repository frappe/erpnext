# Manage Foreign Exchange Difference

In ERPNext, you can create transactions in the foriegn currency as well. When creating transaction in the foreign currency, system updates current exchanage rate with respect to customer/supplier's currency and base currency on your Company. Since Exchange Rate is always flucuating, on might receive payment from the client on exchange rate different from one mentioned in the Sales/Purchase Invoice. Following is the intruction on how to manage different amount avail in payment entry due to exchange rate change.

#### Add Expense Account

To mange currency difference, create Account **Foreign Exchange Gain/Loss**. This account is generally created on the Expense side of P&L statement. However, you can place it under another group as per your accounting requirement.

<img alt="Accounts Frozen Date" class="screenshot" src="/docs/assets/img/articles/exchange-rate-difference-1.png">

#### Book Payment Entry

In the payment voucher, update invoice amount against Customer or Supplier account, then update actual payment amount against Bank/Cash account. Add new row and select Foreign Exchange Gain/Loss to update currency difference amount.

In the below scenario, Sales Invoice was made EUR, at the exchange rate of 1.090. As per this rate, Sales Invoice amount in USD (base currency) was $1000.

One receipt of payment, exchange rate changed. As per the new exchange rate, payment received in the base currency was $1080. This means gain of $80 due to change in exchange rate. Following is how Foreign Exchange Gain will be booked in this scenerio.

<img alt="Accounts Frozen Date" class="screenshot" src="/docs/assets/img/articles/exchange-rate-difference-2.gif">

In case you incur loss due to change foriegn exchnage rate, then different amount about be updated in the debit of Foreign Exchange Gain/Loss account. Also you can add another row to update another expenses like bank charges, remittance charges etc.

<!-- markdown -->
