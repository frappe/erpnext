# Multi Currency Accounting

In ERPNext, you can make accounting entries in multiple currency. For example, if you have a bank account in foreign currency, you can make transactions in that currency and system will show bank balance in that specific currency only.

## Setup

To get started with multi-currency accounting, you need to assign accounting currency in Account record. You can define Currency from Chart of Accounts while creating Account.

<img class="screenshot" alt="Set Currency from Chart of Accounts"  	src="/docs/assets/img/accounts/multi-currency/chart-of-accounts.png">

You can also assign / modify the currency by opening specific Account record for existing Accounts.

<img class="screenshot" alt="Modify Account Currency"  	src="/docs/assets/img/accounts/multi-currency/account.png">

For Customer / Supplier (Party), you can also define it's billing currency in the Party record. If the Party's accounting currency is different from Company Currency, you should mention Default Receivable / Payable Account in that currency.

<img class="screenshot" alt="Customer Accounting Currency"  	src="/docs/assets/img/accounts/multi-currency/customer.png">


Once you defined Currency in the Account and selected relevant accounts in the Party record , you are ready to make transactions against them. If Party account currency is different from Company Currency, system will restrict to make transaction for that party with that currency only. If account currency is same as Company Currency, you can make transactions for that Party in any currency. But accounting entries (GL Entries) will always be in Party Account Currency.

You can change accounting currency in Party / Account record, until making any transactions against them. After making accounting entries, system will not allow to change the currency for both Party / Account record.

In case of multi-company setup, accounting currency of Party must be same for all the companies.

### Exchange Rates
When dealing with multiple currencies, ERPNext has the Currency Exchange module for managing exchange rates. It allows you to save the exchange rate quotes you require. 

For foreign currency transactions, ERPNext checks Currency Exchange for any matching record. If this fails, ERPNext will attempt to get the exchange rate quote from [fixer.io](http://fixer.io). If this still fails, then the exchange rate will have to be entered manually.

#### Exchange Rate Selection
ERPNext automatically fetches the latest exchange rate available.


## Transactions

### Sales Invoice

In Sales Invoice, transaction currency must be same as accounting currency of Customer if Customer's accounting currency is other than Company Currency. Otherwise, you can select any currency in Invoice. On selection of Customer, system will fetch Receivable account from Customer / Company. The currency of receivable account must be same as Customer's accounting currency.

Now, in POS, Paid Amount will be entered in transaction currency, instead of earlier Company Currency. Write Off Amount will also be entered in transaction currency.

Outstanding Amount and Advance Amount will always be calculated and shown in Customer's Account Currency.

<img class="screenshot" alt="Sales Invoice Outstanding"  	src="/docs/assets/img/accounts/multi-currency/sales-invoice.png">

### Purchase Invoice

Similarly, in Purchase Invoice, accounting entries will be made based on Supplier's accounting currency. Outstanding Amount and Advance Amount will also be shown in the supplier's accounting currency. Write Off Amount will now be entered in transaction currency.

### Journal Entry

In Journal Entry, you can make transactions in different currencies. There is a checkbox "Multi Currency", to enable multi-currency entries. If "Multi Currency" option selected, you will be able to select accounts with different currencies.

<img class="screenshot" alt="Journal Entry Exchange Rate"  	src="/docs/assets/img/accounts/multi-currency/journal-entry-multi-currency.png">

 
In Accounts table, on selection of foreign currency account, system will show Currency section and fetch Account Currency and Exchange Rate automatically. You can change / modify the Exchange Rate later manually. Debit / Credit amount should be entered in Account Currency, system will calculate and show the Debit / Credit amount in Company Currency automatically.

<img class="screenshot" alt="Journal Entry in multi currency"  	src="/docs/assets/img/accounts/multi-currency/journal-entry-row.png">

## Reports

### General Ledger

In General Ledger, system shows debit / credit amount in both currency if filtered by an Account and Account Currency is different from Company Currency.

<img class="screenshot" alt="General Ledger Report"  	src="/docs/assets/img/accounts/multi-currency/general-ledger.png">

### Accounts Receivable / Payable

In Accounts Receivable / Payable report, system shows all the amounts in Party / Account Currency.

<img class="screenshot" alt="Accounts Receivable Report"  	src="/docs/assets/img/accounts/multi-currency/accounts-receivable.png">

{next}
