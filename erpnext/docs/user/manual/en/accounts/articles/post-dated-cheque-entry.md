#Post Dated Cheque Entry

Post Dated Cheque is a cheque dated on future date. Party generally give post dated cheque, as advance payment. This cheque would be cleared only after cheque date has arrived.

In ERPNext, create Journal Entries for post dated cheque.

####New Journal Entry

To open new journal voucher go to 

`Accounts > Documents > Journal Entry > New`

#### Set Posting Date

Assuming your Cheque Date is 31st December, 2016 (or any future date). As a result, this posting in your bank ledger will appear on Posting Date updated.

<img alt="JE Posting Date" class="screenshot" src="{{docs_base_url}}/assets/img/articles/post-dated-1.gif">

Note: Journal Voucher Reference Date should equal to or less than Posting Date.

####Step 3: Save and Submit

After entering required details, Save and Submit the Journal Entry.

####Adjusting Post Dated  Cheque Entry

If Post Dated Journal Entry needs to be adjusted against any invoice, it can be accomplished via [Payment Reconciliation Tool]({{docs_base_url}}/user/manual/en/accounts/tools/payment-reconciliation.html).

When cheque is cleared, i.e. on actual date on the cheque, you can update its Clearance Date via [Bank Reconciliation Tool]({{docs_base_url}}/user/manual/en/accounts/tools/bank-reconciliation.html).

You might find value of this Journal Entry already reflecting against bank's ledger. You should check **Bank Reconciliation Statement**, a report in the account module to know difference of bank balance as per system, and actual balance in a account.
<!-- markdown -->