# Loan Management
This module enables companies which provides loans to define and manage loans.
Employees can request loans, which are then reviewed and approved. For the approved loans, 
repayment schedule for the entire loan cycle can be generated and automatic deduction from salary can also be set up. 

### Loan Type
To create a new Loan Type go to:

> Human Resources > Loan Management > Loan Type > New Loan Type

Configure Loan limit and Rate of interest.

<img class="screenshot" alt="Loan Type" src="{{docs_base_url}}/assets/img/human-resources/loan-type.png">

### Loan Application

Employee can apply for loan by going to:

> Human Resources > Loan Management > Loan Application > New Loan Application

<img class="screenshot" alt="Loan Application" src="{{docs_base_url}}/assets/img/human-resources/employee-loan-application.png">

#### In the Loan Application,

  * Enter Employee details and Loan details
  * Select the repayment method, and based on your selection enter Repayment Period in Months or repayment Amount
  
On save, Employee can see Repayment Information and make changes if required before submitting.

<img class="screenshot" alt="Loan Application" src="{{docs_base_url}}/assets/img/human-resources/repayment-info.png">

### Loan

Once the Loan is approved, Manager can create Loan record for the Employee.

> Human Resources > Loan Management > Loan > New Loan

<img class="screenshot" alt="Loan Application" src="{{docs_base_url}}/assets/img/human-resources/employee-loan.png">

#### In the Loan,

 * Enter Employee and Loan Application
 * Check "Repay from Salary" if the loan repayment will be deducted from the salary
 * Enter Disbursement Date, Repayment Start Date, and Account Info
 * If the amount has been disbursed and status is set to "Disbursed", as soon as you hit save, the repayment schedule is generated.
 * The first repayment payment date would be set as per the "Repayment Start Date".  
 
<img class="screenshot" alt="repayment Schedule" src="{{docs_base_url}}/assets/img/human-resources/repayment-schedule.png">

#### Loan Repayment for Members

* After submitting the document, if the status is "Disbursed" and "Repay from Salary" is unchecked, you can click on "Make Repayment Entry" and select the payments which haven't been paid till date.
* After selecting the rows, you will be routed to Journal Entry where the selected payments will be added and placed in their respective Debit/ Credit accounts.
* On submitting the Journal Entry, "Paid" will be checked in the payment rows of the Repayment Schedule, for which the Journal entry has been created.

<img class="screenshot" alt="Make Repayment" src="{{docs_base_url}}/assets/img/human-resources/loan-repayment.gif">

#### Loan repayment deduction from Salary

To auto deduct the Loan repayment from Salary, check "Repay from Salary" in Loan. It will appear as Loan repayment in Salary Slip.

<img class="screenshot" alt="Salary Slip" src="{{docs_base_url}}/assets/img/human-resources/loan-repayment-salary-slip.png">

<div class="embed-container">
  <iframe src="https://www.youtube.com/embed/IUM0t7t4zFU?rel=0" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen>
  </iframe>
</div>

{next}