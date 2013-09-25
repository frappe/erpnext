---
{
	"_label": "Salary and Payroll"
}
---
To process Payroll in ERPNext,

1. Create Salary Structures for all Employees.
1. Generate Salary Slips via the Salary Manager Tool.
1. Book the Salary in your Accounts.

### Salary Structure

The Salary Structure represents how Salaries are calculated based on Earnings and Deductions. To create a new Salary Structure go to:

> HR > Salary Structure > New Salary Structure


![Salary Structure](img/salary-structure.png)


### In the Salary Structure,

- Select the Employee
- Set the starting date from which this is valid (Note: There can only be one Salary Structure that can be “Active” for an Employee during any period)
- In the “Earnings” and “Deductions” table all your defined Earning Type and Deductions Type will be auto-populated. Set the values of the Earnings and Deductions and save the Salary Structure.

### Leave Without Pay (LWP)

Leave Without Pay (LWP) happens when an Employee runs out of allocated leaves or takes a leave without an approval (via Leave Application). If you want ERPNext to automatically deduct salary in case of LWP, then you must check on the “Apply LWP” column in the Earning Type and Deduction Type masters. The amount of pay cut is the proportion of LWP days divided by the total working days for the month (based on the Holiday List).

If you don’t want ERPNext to manage LWP, just don’t click on LWP in any of the Earning Types and Deduction Types.

---

### Creating Salary Slips

Once the Salary Structure is created, you can make a salary slip from the same form or you can process your payroll for the month using the Salary Manager.

To create a salary slip from Salary Structure, click on the button Make Salary Slip.


![Salary Slip](img/salary-slip-1.png)

<br>


Through Salary Manager:

> HR > Process Payroll


![Salary Manager](img/salary-manager.png)



In the Salary Manager tool,

1. Select the Company for which you want to create the Salary Slips.
1. Select the Month and the Year for which you want to create the Salary Slips.
1. Click on “Create Salary Slips”. This will create Salary Slip records for each active Employee for the month selected. If the Salary Slips are created, the system will not create any more Salary Slips. All updates will be shown in the “Activity Log” section.
1. Once all Salary Slips are created, you can check if they are created correctly or edit it if you want to deduct Leave Without Pay (LWP).
1. After checking, you can “Submit” them all together by clicking on “Submit Salary Slips”. 1. If you want them to be automatically emailed to the Employee, make sure to check the “Send Email” box.

### Booking Salaries in Accounts

The final step is to book the Salaries in your Accounts. 

Salaries in businesses are usually dealt with extreme privacy. In most cases, the companies issues a single payment to the bank combining all salaries and the bank distributes the salaries to each employee’s salary account. This way there is only one payment entry in the company’s books of accounts and anyone with access to the company’s accounts will not have access to the individual salaries.

The salary payment entry is a Journal Voucher entry that debits the total salary of all Employees to the Salary Account and credits the company’s bank Account.

To generate your salary payment voucher from the Salary Manager, click on “Make Bank Voucher” and a new Journal Voucher with the total salaries will be created.