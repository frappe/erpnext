<h1>Employees Loan Management</h1>

Employee Loan is an sum of money paid by Employer to Employee based on certain terms and condition. There are multiple ways accounting for the Employee loan can be managed. Company could collect loan from an employee separately. Or they can choose to deduct loan installment from the employee's salary.

Let's check below how accounting can be managed for Employee Loan in ERPNext.

### 1. Setup Masters

Create following Groups and Ledgers in Chart of Accounts if not there.
      
#### 1.1  Employee Loan Account

Create Group as 'Employees Loans' under Current Assets and create employee loan A/C (Ledger) under it. [Check this link for new account creation]({{docs_base_url}}/user/manual/en/setting-up/articles/managing-tree-structure-masters)

![CoA]({{docs_base_url}}/assets/img/articles/Selection_433.png)

#### 1.2 Salaries Account

Create Group as 'Salaries' under Current Liabilities and create employee salary loan A/C (Ledger) under it.

![CoA]({{docs_base_url}}/assets/img/articles/Selection_434.png)

#### 1.3 Interest Account

Create Ledger as 'Interest on Loan' under Indirect Income.

### 2. Book Loan Amount

Once loan amount is finalized, make journal voucher to book loan payment entry. You should Credit Loan amount to Bank/Cash account and Debit Loan amount employee loan account.  

![Loan Entry]({{docs_base_url}}/assets/img/articles/Selection_435.png)

### 3. Book Loan Recovery and Interest

#### 3.1 Loan Recovery Entry

If your employee pays separately for his/her loan installment and loan interest, then create journal voucher. 

![Loan Reco]({{docs_base_url}}/assets/img/articles/Selection_436.png)

#### 3.2 Loan Adjustment in Salary

And if you deduct loan installment and interest from employees salary, then book journal entry for the same.

![Loan Reco]({{docs_base_url}}/assets/img/articles/Selection_437.png)

In the Salary Slip of an employee, then create two Deduction Types in Salary Structure. One as 'Loan Installment' and other one as 'Loan Interest'. So that you can update those values under this deduction heads.

### 4. Loan Account Report

After recovering loan and loan interest, General Ledger report will show the loan account details as follows.

![Loan Reco]({{docs_base_url}}/assets/img/articles/Selection_439.png)

<!-- markdown -->
