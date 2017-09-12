# Accounts Settings


<img class="screenshot" alt="Account Settings" src="/docs/assets/img/accounts/account-settings.png">

* Accounts Frozen Upto: Freeze accounting transactions upto specified date, nobody can make / modify entry except specified role.

* Role Allowed to Set Frozen Accounts & Edit Frozen Entries: Users with this role are allowed to set frozen accounts and create / modify accounting entries against frozen accounts.

* Credit Controller: Role that is allowed to submit transactions that exceed credit limits set.

* Make Payment via Journal Entry: If checked, from invoice, if user choose to make payment, this will open the journal entry instead of payment entry

* Unlink Payment on Cancellation of Invoice: If checked, system will unlink the payment against the invoice. Otherwise, it will show the link error.

* Allow Stale Exchange Rate:  This should be unchecked if you want ERPNext to check the age of records fetched from Currency Exchange in foreign currency transactions. If it is unchecked, the exchange rate field will be read-only in documents. 
 
* Stale Days: The number of days to use when deciding if a Currency Exchange record is stale. E.g If Currency Exchange records are to be updated every day, the Stale Days should be set as 1. 

{next}
