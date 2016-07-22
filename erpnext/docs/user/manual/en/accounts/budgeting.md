In ERPNext, you can set and manage Budgets against a specific Account. This is useful when, for example, you are doing online sales. You have a budget for search ads, and you want ERPNext to stop or warn you from over spending, based on that budget.

Budgets are also great for planning purposes. When you are making plans for the next financial year, you would typically target a revenue based on which you would set your expenses. Setting a budget will ensure that your expenses do not get out of hand, at any point, as per your plans.

In ERPNext, budget against an Account is defined via Cost Center. Following are the steps to define a Budget.

###Cost Center

To create new Cost Center, go to:

> Accounts > Budget and Cost Center > Chart of Cost Center > Add New Cost Center

<img class="screenshot" alt="Budget" src="{{docs_base_url}}/assets/img/accounts/budgeting-cost-center.png">

###Budgeting

####Step 1: Create a new Budget

To define a Budget, go to:

> Accounts > Budget and Cost Center > Budget > New

####Step 2: Select Cost Center

In the Budget form, select a Cost Center. Budgets can be defined against any Cost Center whether it is a Group / Leaf node in the Chart of Cost Centers. 

####Step 3: Select Account

In the Budgets table, select Income / Expense account for which Budget is to be defined. 

<img class="screenshot" alt="Budget" src="{{docs_base_url}}/assets/img/accounts/budget-account.png">

####Step 4: Monthly Distribution

If you have seasonal business, you can also define a Monthly Distribution record, to distribute the budget between months. If you don't set the monthly distribution, ERPNext will calculate the budget on yearly
basis or in equal proportion for every month.

<img class="screenshot" alt="Monthly Distribution" src="{{docs_base_url}}/assets/img/accounts/monthly-budget-distribution.png">

####Step 5: Alert on Budget

While setting budget, you can also define the actions when expenses will exceed the allocated budget for a period. You can set separate action for monthly and annual budgets. There are 3 types of actions: Stop, Warn and Ignore. If Stop, system will not allow to book expenses more than allocated budget. In Case of Warn, it will just warn the user that expenses has been exceeded from the allocated budget. And Ignore will do nothing.

<img class="screenshot" alt="Monthly Distribution" src="{{docs_base_url}}/assets/img/accounts/budget-warning.png">

####Budget Variance Report

At any point of time, user can check Budget Variance Report to analysis the expense vs budget against a cost center.

To check Budget Variance report, go to:

Accounts > Budget and Cost Center > Budget Variance Report

<img class="screenshot" alt="Budget Variance Report" src="{{docs_base_url}}/assets/img/accounts/budget-variance-report.png">

{next}
