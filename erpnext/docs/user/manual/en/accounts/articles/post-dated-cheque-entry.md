<h1>Post Dated Cheque Entry</h1>

Post Dated Cheque is a cheque dated on future date given to another party. This actually works as an advance payment which will could be cleared post cheque date only.

In ERPNext, you can manage post dated cheque entries via journal voucher. Following are step to book payment entry for post dated cheque.

####New Journal Voucher

To open new journal voucher go to 

`Accounts > Documents > Journal Voucher > New`

####Set Posting Date and other details

Assuming your Cheque Date is 31st December, 2014 (or any future date) and you need value of this cheque to reflect in the bank balance after cheque date only.

![Journal Voucher]({{docs_base_url}}/assets/img/articles/Selection_005d73bc7.png)

Note: Journal Voucher Reference Date should equal to or less than Posting Date.

####Step 3: Save and Submit Journal Voucher

After entering required details Save and Submit the Journal Voucher.

####Adjusting Post Dated  Cheque Entry

If Post Dated Journal Voucher needs to be adjusted against any invoice, it can be accomplished via [Payment Reconciliation Tool](https://erpnext.com/user-guide/accounts/payment-reconciliation).

When cheque is cleared in the future date, i.e. actual date on the cheque, you can update its Clearance Date via [Bank Reconciliation Tool](https://erpnext.com/user-guide/accounts/bank-reconciliation).

You might find value of this Journal Voucher already reflecting against bank's ledger. You should check **Bank Reconciliation Statement**, a report in the account module to know difference of balance as per system, and balance expected in the bank.
<!-- markdown -->