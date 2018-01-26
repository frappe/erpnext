# Payroll Entry

You can also create salary slip for multiple employees using Payroll Entry:

> Human Resources > Payroll Entry

<img class="screenshot" alt="Payroll Entry" src="/docs/assets/img/human-resources/payroll-entry.png">

In Payroll Entry,

  1. Select the Company for which you want to create the Salary Slips. You can also select the other fields like Branch, Department, Designation or Project to be more specific.
  2. Check "Salary Slip based on Timesheet" if you want to process timesheet based Salary Slips.
  3. Select the Start Date and End Date or Fiscal year and month for which you want to create the Salary Slips.
  4. Click on "Get Employee Details" to get a list of Employees for which the Salary Slips will be created based on the selected criteria.
  5. Select the Cost Center and Payment Account.
  6. Save the form and Submit it to create Salary Slip records for each active Employee for the time period selected. If the Salary Slips are already created, the system will not create any more Salary Slips. You can also just save the form as Draft and create the Salary Slips later.

<img class="screenshot" alt="Payroll Entry" src="/docs/assets/img/human-resources/created-payroll.png">

Once all Salary Slips are created, you can check by clicking on "View Salary Slips", if they are created correctly or edit it if you want to deduct Leave Without Pay (LWP).

After checking, you can "Submit" them all together by clicking on "Submit Salary Slip".

### Booking Salaries in Accounts

The final step is to book the Salaries in your Accounts.

Salaries in businesses are usually dealt with extreme privacy. In most cases,
the companies issues a single payment to the bank combining all salaries and
the bank distributes the salaries to each employee’s salary account. This way
there is only one payment entry in the company’s books of accounts and anyone
with access to the company’s accounts will not have access to the individual
salaries.

The salary payment entry is a Journal Entry that debits the total of the
earning type salary component and credits the total of deduction type salary 
component of all Employees to the default account set at Salary Component level 
for each component.

To generate your salary payment voucher from Payroll Entry, click on, 
> Make > Bank Entry

<img class="screenshot" alt="Payroll Entry" src="/docs/assets/img/human-resources/payroll-make-bank-entry.png">

It will ask to enter the Bank Transaction Reference Number and date. All other details will be auto-filled according to your Payroll Entry form. Click on Save and create it.

<img class="screenshot" alt="Payroll Entry" src="/docs/assets/img/human-resources/payroll-journal-entry.png">

{next}
