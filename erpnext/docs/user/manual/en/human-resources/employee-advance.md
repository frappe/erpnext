# Employee Advance

Sometimes employees go outside for company's work and company pays some amount for their expenses in advance. In that time, the employee can create Employee Advance form and the approver will be notified about the same. After Employee Advance gets approved, the accountant releases the payment and makes the payment entry.

To make a new Employee Advance, go to:

> HR > Employee Advance > New Employee Advance

<img class="screenshot" alt="Expense Claim" src="/docs/assets/img/human-resources/employee_advance.png">

Set the Employee ID, date, purpose and requested amount and “Save” the record.

### Approving Expenses

Approver for the Employee Advance is selected by an Employee himself. Users to whom `Expense Approver` role is assigned will shown in the Employee Advance Approver field.

After saving Employee Advance, Employee should [Assign document to Approver](/docs/user/manual/en/using-eprnext/assignment.html). On assignment, approving user will also receive email notification. To automate email notification, you can also setup [Email Alert](/docs/user/manual/en/setting-up/email/email-alerts.html).

Approver should approve or reject the advance request and submit the Employee Advance form.

### Make Payment Entry
After submission of Employee Advance record, accounts user will be able to create payment entry via Journal Entry or Payment Entry form.
The payment entry will look like following:
<img class="screenshot" alt="Employee Advance Payment via Journal Entry" src="/docs/assets/img/human-resources/employee_advance_journal_entry.png">

<img class="screenshot" alt="Employee Advance Payment via Payment Entry" src="/docs/assets/img/human-resources/employee_advance_payment_entry.png">

On submission of payment entry, the paid amount and status will be updated in Employee Advance record.

### Adjust advances on Expense Claim
Later when employee claims the expense and advance record can be fetched in Expense Claim and linked to the claim record.
<img class="screenshot" alt="Employee Advance Payment via Payment Entry" src="/docs/assets/img/human-resources/expense_claim_advances.png">