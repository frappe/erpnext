# Expense Claim

Expense Claim is made when Employee’s make expenses out of their pocket on behalf of the company. For example, if they take a customer out for lunch, they can make a request for reimbursement via the Expense Claim form.

To make a new Expense Claim, go to:

> HR > Expense Claim > New Expense Claim

<img class="screenshot" alt="Expense Claim" src="{{docs_base_url}}/assets/img/human-resources/expense_claim.png">

Set the Employee ID, date and the list of expenses that are to be claimed and
“Submit” the record.

### Set Account for Employee
Set employee's expense account on the employee form, system books an expense amount of an employee under this account.
<img class="screenshot" alt="Expense Claim" src="{{docs_base_url}}/assets/img/human-resources/employee_account.png">

### Approving Expenses

Approver for the Expense Claim is selected by an Employee himself. Users to whom `Expense Approver` role is assigned will shown in the Expense Claim Approver field.

After saving Expense Claim, Employee should [Assign document to Approver]({{docs_base_url}}/user/manual/en/using-eprnext/assignment.html). On assignment, approving user will also receive email notification. To automate email notification, you can also setup [Email Alert]({{docs_base_url}}/user/manual/en/setting-up/email/email-alerts.html).

Expense Claim Approver can update the “Sanctioned Amounts” against Claimed Amount of an Employee. If submitting, Approval Status should be submitted to Approved or Rejected. If Approved, then Expense Claim gets submitted. If rejected, then Expen
Comments can be added in the Comments section explaining why the claim was approved or rejected.

### Booking the Expense

On submission of Expense Claim, system books an expense against the expense account and the employee account
<img class="screenshot" alt="Expense Claim" src="{{docs_base_url}}/assets/img/human-resources/expense_claim_book.png">

User can view unpaid expense claim using report "Unclaimed Expense Claims"
<img class="screenshot" alt="Expense Claim" src="{{docs_base_url}}/assets/img/human-resources/unclaimed_expense_claims.png">

### Payment for Expense Claim

To make payment against the expense claim, user has to click on Make > Bank Entry
#### Expense Claim
<img class="screenshot" alt="Expense Claim" src="{{docs_base_url}}/assets/img/human-resources/payment.png">

#### Payment Entry
<img class="screenshot" alt="Expense Claim" src="{{docs_base_url}}/assets/img/human-resources/payment_entry.png">


Note: This amount should not be clubbed with Salary because the amount will then be taxable to the Employee.

### Linking with Task & Project

* To Link Expense Claim with Task or Project specify the Task or the Project while making an Expense Claim

<img class="screenshot" alt="Expense Claim - Project Link" src="{{docs_base_url}}/assets/img/project/project_expense_claim_link.png">

{next}
