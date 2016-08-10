#Post Dated Cheque Entry

Post Dated Cheque is a cheque dated on future date. Party generally give post dated cheque, as advance payment. This cheque would be cleared only when cheque date arrives.

In ERPNext, create Payment Entry for post dated cheque.

####New Payment Entry

To open new journal voucher go to 

`Explore > Accounts > Payment Entry > New`

#### Set Posting Date

Assuming your Cheque Date is 31st December, 2016 (or any future date). As a result, this posting in your bank ledger will appear on Posting Date updated.

<img alt="JE Posting Date" class="screenshot" src="{{docs_base_url}}/assets/img/articles/post-dated-1.png">

Note: Payment Entry Reference Date should equal to or less than Posting Date.

####Step 3: Save and Submit

After entering required details, Save and Submit the Payment Entry.

####Adjusting Post Dated  Cheque Entry

You can adjust Post Dated Payment Entry against an invoice via [Payment Reconciliation Tool]({{docs_base_url}}/user/manual/en/accounts/tools/payment-reconciliation.html).

When cheque is cleared, i.e. on actual date on the cheque, you can update its Clearance Date via [Bank Reconciliation Tool]({{docs_base_url}}/user/manual/en/accounts/tools/bank-reconciliation.html).

In the Chart of Accounts, you might find value of this Payment Entry already reflecting against bank Account. You should check **Bank Reconciliation Statement**, a report in the account module to know difference of bank balance as per system, and actual balance in the bank's statement.
<!-- markdown -->