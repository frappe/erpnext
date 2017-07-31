# Salary Slip From Timesheet

#Salary Slip from Timesheet

If salary / wages for your employees are calculated based on number of hours worked, you can use Timesheet to track actual hours worked, and for creating Salary Slip.

####Employee creates Timesheet

To track actual hours employee has worked for, create Timesheet for each Employee. We suggest you to create Timesheet based on a payment period. For example, if you paying employee on a weekly bases, create one Timesheet for an Employee for one week. However, you can create multiple Timesheets, and create one Salary Slip for the multiple Timesheets.

<img class="screenshot" alt="Sales Invoice" src="{{docs_base_url}}/assets/img/project/timesheet/timesheet-salary-slip-1.png">

####Salary Structure for the Employee

In the Salary Structure of the Employee, check field "Salary Slip Based on Timesheet". On checking this field, you see fields Salary Component and Hour Rate. Amount for that Salary Component (say Basic) will be calculated based on:

<div class=well> Total Timesheet Hours *  Hour Rate </div>

Amount directly for other Salary Components (eg: House Rent Allowance, Phone Allowance) can be define directly. When creating Salary Slip, Amount for these Salary Component will be fetched as it is.

<img class="screenshot" alt="Sales Invoice" src="{{docs_base_url}}/assets/img/project/timesheet/timesheet-salary-slip-2.png">

####Create Salary Slip from Timesheet

To create Salary Slip against Timesheet, open Timesheet and click on "Salary Slip".

<img class="screenshot" alt="Sales Invoice" src="{{docs_base_url}}/assets/img/project/timesheet/timesheet-salary-slip-3.png">

In the Salary Slip, Timesheet ID will be updated. You can select more Timesheet to be paid via this Salary Slip. Based on the Timesheets selected, Total Working Hours will be calculated.

<img class="screenshot" alt="Sales Invoice" src="{{docs_base_url}}/assets/img/project/timesheet/timesheet-salary-slip-4.gif">

Hour Rate will be fetched from the Salary Structure of an Employee. Based on Total Working Hours and Hour Rate, Amount will be calculated for the Salary Component is to be calculated based on actual hours worked.

####Save and Submit Salary Slip

On Submission of Salary Slip, Timesheet's status will be updated to "Payslip".

<img class="screenshot" alt="Sales Invoice" src="{{docs_base_url}}/assets/img/project/timesheet/timesheet-salary-slip-5.png">

<div class=well> 

Creating Salary Slip based on Timesheet will allow you to manage payment for the overtime.
	<ol>
		<li>Employee created Timesheet for the overtime.</li>
		<li>In the Salary Structure of an Employee, set Overtime as a Salary Component to be calculated based on hourly bases.</li>
		<li>When creating Salary Structure for an Employee, pull Timesheet when overtime details are tracked.</li>
	</ol>
</div>