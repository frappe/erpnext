# Round of Account Validation Message

**Question** 

When submitting an invoice, why does it ask for a Round Off Account? How to update it?

<img class="screenshot" alt="Fees Section" src="{{docs_base_url}}/assets/img/accounts/round-off-account.png">

**Answer**

In the Purchase Invoice, Grand Total is calculated based on various calculations like:

- Qty * Rate = Amount
- Tax and other charges applied to each item
- Discount applied to some or all the items
- Multiplication with exchange rate, in case of multiple currencies

As a result of multiple calculations, there could be some rounding loss in the final amount. This rounding loss is generally very marginal like 0.034. But for the accounting accuracy, has to be posted in the accounts. Hence, you need to define a default Round-Off account in the Company master in which such amount availed as a result of rounding loss can be booked.

You need to create Round-off Account in the Chart of Accounts and update in the Company master. Steps here.

* Accounts > Chart of Accounts
* In the Chart of Account, check or create new Account under Expense > Direct Expense. Ignore if account for this purpose already existing
* Come to Company master 
  Account > Company
* Open Company in which Round-Off account has to be updated.
* In the Company master, scroll to Accounts Settings and select Round-Off account and Cost Center.
    <img class="screenshot" alt="Fees Section" src="{{docs_base_url}}/assets/img/accounts/company-round-off-account.png">

Once Round-Off account this updated in the Company master, then try to submit Purchase Invoice once again.
