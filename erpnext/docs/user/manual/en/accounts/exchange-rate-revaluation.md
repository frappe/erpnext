# Exchange Rate Revaluation

In ERPNext, you can make accounting entries in multiple currency. For example, if you have a bank account in foreign currency, you can make transactions in that currency and system will show bank balance in that specific currency only.

## Setup

To get started with multi-currency accounting, you need to assign accounting currency in Account record. You can define Currency from Chart of Accounts while creating Account.

<img class="screenshot" alt="Set Currency from Chart of Accounts"  	src="{{docs_base_url}}/assets/img/accounts/multi-currency/chart-of-accounts.png">

You can also assign / modify the currency by opening specific Account record for existing Accounts.

<img class="screenshot" alt="Modify Account Currency"  	src="{{docs_base_url}}/assets/img/accounts/multi-currency/account.png">

### Exchange Rate Revaluation

Exchange Rate Revaluation feature is for dealing the situation when you have a multiple currency accounts in one company's chart of accounts

Steps :

1. Set the 'Unrealized Exchange / Gain Loss Account' field in Company DocType. This aacount is to balance the difference of total credit and total debit.

<img class="screenshot" alt="Field Set for Comapny"  	src="{{docs_base_url}}/assets/img/accounts/exchange-rate-revaluation/field_set_company.png">

2. Select the Company.

3. Click the Get Entries button. It shows the accounts which having different currency as compare to 'Default Currency' in Company DocType. It will fetch the new exchange rate automatically if not set in Currency Exchange DocType for that currency else it will fetch the 'Exchange Rate' from Currency Exchange DocType

<img class="screenshot" alt="Exchange Rate Revaluation"  	src="{{docs_base_url}}/assets/img/accounts/exchange-rate-revaluation/exchange-rate-revaluation.png">

4. On Submitting, 'Make Journal Entry' button will appear. This will create a journal entry for the Exchange Rate Revaluation.

<img class="screenshot" alt="Exchange Rate Revaluation Submitting"  	src="{{docs_base_url}}/assets/img/accounts/exchange-rate-revaluation/exchange-rate-revaluation-submit.png">

<img class="screenshot" alt="Journal Entry"  	src="{{docs_base_url}}/assets/img/accounts/exchange-rate-revaluation/journal-entry.png">