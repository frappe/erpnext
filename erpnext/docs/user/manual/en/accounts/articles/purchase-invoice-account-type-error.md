# Purchase Invoice - Account Type Error

**Question:** On saving the Purchase Invoice, I am getting a validation message that Credit To Account must be a Balance Sheet account.

<img alt="Role Desk Permission" class="screenshot" src="/docs/assets/img/articles/purchase-invoice-account-type.png">

**Answer: **On submission of a Purchase Invoice, payable is updated towards the Supplier. As per the accounting standards, Payable Account is aligned under Current Liability (credit side of Balance Sheet).

The error message indicates that Account selected in the Credit To field doesn't belong to the Liability Group. Please ensure that Payable Account selected in the Purchase Invoice is located under Liability group.