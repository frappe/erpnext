Project is divided into Tasks. 
In ERPNext, you can also create a Task independently.

<img class="screenshot" alt="Task" src="{{docs_base_url}}/assets/img/project/task.png">

### Status of the Task

A Task can have either of the following status - Open, Working, Pending Review, Closed, Cancelled.

<img class="screenshot" alt="Task - Status" src="{{docs_base_url}}/assets/img/project/task_status.png">

* By default each new Task created shall have the status set to 'Open'.

* If a Time Log is made against a task, its status shall be set to 'Working'.

### Dependent Task

You can specify a list of dependent task under the 'Depends On' section.

<img class="screenshot" alt="Depends On" src="{{docs_base_url}}/assets/img/project/task_depends_on.png">

* You cannot close the parent Task until all 'Dependant Task' are closed.

* If the Dependent Task are delayed and overlap with the expected Start Date of the Parent task, the system will reschedule the parent task.

### Managing Time

ERPNext uses [Time Log]({{docs_base_url}}/user/manual/en/projects/time-log.html) to track the progress of a Task.
You can create multiple Time Logs against each task.
The Actual Start and End Time along with the costing shall then be updated based on the Time Log.

* To view Time Log made against a Task click on 'Time Logs'

<img class="screenshot" alt="Task - View Time Log" src="{{docs_base_url}}/assets/img/project/task_view_time_log.png">

<img class="screenshot" alt="Task - Time Log List" src="{{docs_base_url}}/assets/img/project/task_time_log_list.png">

* You can also create a Time Log directlly and link it to the Task.

<img class="screenshot" alt="Task - Link Time Log" src="{{docs_base_url}}/assets/img/project/task_time_log_link.png">

### Managing Expenses

You can book [Expense Claim]({{docs_base_url}}/user/manual/en/human-resource-management/expense-claim.html) against a task.
The system shall update the total amount from expense claims in the costing section.

* To view Expense Claims made against a Task click on 'Expense Claims'

<img class="screenshot" alt="Task - View Expense Claim" src="{{docs_base_url}}/assets/img/project/task_view_expense_claim.png">

* You can also create a Expense Claims directlly and link it to the Task.

<img class="screenshot" alt="Task - Link Expense Claim" src="{{docs_base_url}}/assets/img/project/task_expense_claim_link.png">

* Total amount of Expense Claims booked against a task is shown under 'Total Expense Claim' in the Task Costing Section

<img class="screenshot" alt="Task - Total Expense Claim" src="{{docs_base_url}}/assets/img/project/task_total_expense_claim.png">

{next}
