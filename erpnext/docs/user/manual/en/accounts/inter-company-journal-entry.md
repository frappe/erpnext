# Inter Company Journal Entry

You can also create Inter Company Journal Entry if you are making transactions with multiple Companies.
You can select the Accounts which you wish to use in the Inter Company transactions.
Just go to,

> Accounts > Company and Accounts > Chart Of Accounts

Select the Account which you would like to set as an Internal Account for the transaction, and check the **Inter Company Account** checkbox. It can now be used for Inter Company Journal Entry Transactions.

<img class="screenshot" alt="Internal Account" src="{{docs_base_url}}/assets/img/accounts/internal-account.png">

You need to do the same for all the Companies' Accounts which you want to use for Inter Company Journal Entry transactions.

Now, to create an Inter Company Journal Entry go to:

> Accounts > Company and Accounts > Journal Entry > New

<img class="screenshot" alt="Inter Company Journal Entry" src="{{docs_base_url}}/assets/img/accounts/inter-company-jv.png">

In the Journal Entry, you must select,

* Type of Voucher - **Inter Company Journal Entry**.
* Add rows for the individual accounting entries. In each row, you must specify:
  * The Internal account that will be affected. 
  * The amount to Debit or Credit.
  * The Cost Center (If it is an Income or Expense).

On submitting the Journal Entry, you will find a button on the top right corner, **Make Inter Company Journal Entry**.

<img class="screenshot" alt="Submitted Inter Company Journal Entry" src="{{docs_base_url}}/assets/img/accounts/inter-company-jv-submit.png">

Click on the button, you will be asked to select the Company against which you wish to create the linked Journal Entry.

<img class="screenshot" alt="Select Company" src="{{docs_base_url}}/assets/img/accounts/select-company-jv.png">

On selecting the Company, you will be routed to another Journal Entry where the relevant fields will be mapped, i.e. Company, Voucher Type, Inter Company Journal Entry Reference etc. 

<img class="screenshot" alt="Linked Journal Entry" src="{{docs_base_url}}/assets/img/accounts/linked-jv.png">

Select the Internal accounts for the Company selected and submit the Journal Entry, make sure the total Debit and Credit Amounts are same as the previously created Journal Entry's total Credit and Debit Amounts respectively.

You can also find the reference link at the bottom, which will be added in both the linked Journal Entries and will be removed if any of the Journal Entries are cancelled.

{next}
