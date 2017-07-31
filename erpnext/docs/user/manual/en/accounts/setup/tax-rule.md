# Tax Rule

You can define which [Tax Template](/docs/user/manual/en/setting-up/setting-up-taxes.html) must be applied on a Sales / Purchase transaction using Tax Rule.

<img class="screenshot" alt="Tax Rule" src="/docs/assets/img/accounts/tax-rule.png">

You can define Tax Rules for Sales or Purchase Taxes. 
While making a Transaction the system will select and apply tax template based on the tax rule defined.
The system selects Tax Rule with maximum matching Filters.

Let us consider a senario to understand Tax Rule Better.

Suppose we define 2 Tax Rules as below.

<img class="screenshot" alt="Tax Rule" src="/docs/assets/img/accounts/tax-rule-1.png">

<img class="screenshot" alt="Tax Rule" src="/docs/assets/img/accounts/tax-rule-2.png">

Here Tax Rule 1 has Billing Country as India and Tax Rule 2 has Billing Country as United Kingdom

Now supposed we try to create a Sales Order for a customer whose default Billing Country is India, system shall select Tax Rule 1.
In case the customers Billing Country was United Kingdom, the system would have selected Tax Rule 2.

