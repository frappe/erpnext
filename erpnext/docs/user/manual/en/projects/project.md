# Project

Project management in ERPNext is Task driven. You can create Project and assign multiple Tasks against it.

<img class="screenshot" alt="Project" src="{{docs_base_url}}/assets/img/project/project.png">

You can also track % Completion of a Project using different methods.

  1. Task Completion
  2. Task Progress
  3. Task Weight

<img class="screenshot" alt="Project" src="{{docs_base_url}}/assets/img/project/project-percent-complete.png">

Some examples of how the % Completion is calculated based on Tasks.

<img class="screenshot" alt="Project" src="{{docs_base_url}}/assets/img/project/percent-complete-calc.png">

<img class="screenshot" alt="Project" src="{{docs_base_url}}/assets/img/project/percent-complete-formula.png">

### Managing tasks
Project can be divided into multiple Tasks.
Task can be created via Project document itself or can be created via  [Task]({{docs_base_url}}/user/manual/en/projects/tasks.html)

<img class="screenshot" alt="Project" src="{{docs_base_url}}/assets/img/project/project_task.png">

* To view Task made against a Project click on 'Tasks'

<img class="screenshot" alt="Project - View Task" src="{{docs_base_url}}/assets/img/project/project_view_task.png">

<img class="screenshot" alt="Project - Task List" src="{{docs_base_url}}/assets/img/project/project_task_list.png">

* You can also view the Tasks from the Project document itself

<img class="screenshot" alt="Project - Task Grid" src="{{docs_base_url}}/assets/img/project/project_task_grid.png">

* To add Weights to Tasks you can follow the below steps

<img class="screenshot" alt="Project - Task Grid" src="{{docs_base_url}}/assets/img/project/tasks.png">
<img class="screenshot" alt="Project - Task Grid" src="{{docs_base_url}}/assets/img/project/task-weights.png">


### Managing time

ERPNext uses [Time Log]({{docs_base_url}}/user/manual/en/projects/time-log.html) to track the progress of a Project.
You can create Time Logs against each task.
The Actual Start and End Time along with the costing shall then be updated based on the Time Log.

* To view Time Log made against a Project click on 'Time Logs'

<img class="screenshot" alt="Project - View Time Log" src="{{docs_base_url}}/assets/img/project/project_view_time_log.png">

<img class="screenshot" alt="Project - Time Log List" src="{{docs_base_url}}/assets/img/project/project_time_log_list.png">

* You can also create a Time Log directlly and link it to the Project.

<img class="screenshot" alt="Project - Link Time Log" src="{{docs_base_url}}/assets/img/project/project_time_log_link.png">

### Managing expenses

You can book [Expense Claim]({{docs_base_url}}/user/manual/en/human-resources/expense-claim.html) against a project task.
The system shall update the total amount from expense claims in the project costing section.

* To view Expense Claims made against a Project click on 'Expense Claims'

<img class="screenshot" alt="Project - View Expense Claim" src="{{docs_base_url}}/assets/img/project/project_view_expense_claim.png">

* You can also create a Expense Claims directlly and link it to the Project.

<img class="screenshot" alt="Project - Link Expense Claim" src="{{docs_base_url}}/assets/img/project/project_expense_claim_link.png">

* Total amount of Expense Claims booked against a project is shown under 'Total Expense Claim' in the Project Costing Section

<img class="screenshot" alt="Project - Total Expense Claim" src="{{docs_base_url}}/assets/img/project/project_total_expense_claim.png">

### Cost Center

You can make a [Cost Center]({{docs_base_url}}/user/manual/en/accounts/setup/cost-center.html) against a Project or use an existing cost center to track all expenses made against that project.

<img class="screenshot" alt="Project - Cost Center" src="{{docs_base_url}}/assets/img/project/project_cost_center.png">

###Project Costing

The Project Costing section helps you track the time and expenses incurred against the project.

<img class="screenshot" alt="Project - Costing" src="{{docs_base_url}}/assets/img/project/project_costing.png">

* The Costing Section is updated based on Time Logs made.

* Gross Margin is the difference between Total Costing Amount and Total Billing Amount

###Billing

You can make/link a [Sales Order]({{docs_base_url}}/user/manual/en/selling/sales-order.html) against a project. Once linked you can use the standard sales module to bill your customer against the Project.

<img class="screenshot" alt="Project - Sales Order" src="{{docs_base_url}}/assets/img/project/project_sales_order.png">

###Gantt Chart

A Gantt Chart illustrates a project schedule.
ERPNext gives you a illustrated view of tasks scheduled against that project in Gantt Chart View.

* To view gantt chart against a project, go to that project and click on 'Gantt Chart'

<img class="screenshot" alt="Project - View Gantt Chart" src="{{docs_base_url}}/assets/img/project/project_view_gantt_chart.png">

<img class="screenshot" alt="Project - Gantt Chart" src="{{docs_base_url}}/assets/img/project/project_gantt_chart.png">

{next}
