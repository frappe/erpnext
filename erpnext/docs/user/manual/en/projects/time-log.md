Time Logs are a way to track time worked.
They can be used to track the following

* Billable work to Customers
* Production Order Operations
* Tasks
* Project
* Internal References

<img class="screenshot" alt="Time Log" src="{{docs_base_url}}/assets/img/project/time_log.png">

###Creating Time Logs

1. To create a new Time Log, you can go to 
> Projects > Time Log > new Time Log

2. You can also create a new Time Log via Calendar

To create Time Logs via Calender, go to Time Log and select Calendar.

<img class="screenshot" alt="Time Log - View Calender" src="{{docs_base_url}}/assets/img/project/time_log_view_calendar.png">

* To create a Time Log for multiple days, click and drag the cursor across days.

<img class="screenshot" alt="Time Log - Drag Calender" src="{{docs_base_url}}/assets/img/project/time_log_calendar_day.gif">

* You can also create Time Logs from 'week' and 'day' view of the calender.

<img class="screenshot" alt="Time Log - Drag Calender" src="{{docs_base_url}}/assets/img/project/time_log_calendar_week.gif">

* Time Logs for Manufacturing processes needs to be created from the Production Order. 
* To create more Time Logs against Operations select the respective operation and click on the 'Make Time Log' button.

###Billing using Time Logs

* If you wish to bill against a Time Log you need to select the 'Billable' option.

* In the costing section, the system will pull up the Costing & Billing rate from [Activity Cost]({{docs_base_url}}/user/manual/en/projects/activity-cost.html) 
	based on the Employee and Activity Type specified.

* The system shall then calculate the Costing and Billing amount based on the Hours mentioned in the Time Log.

* If 'Billable' is not selected, the system shall display the 'Billing Amount' as 0.

<img class="screenshot" alt="Time Log - Costing" src="{{docs_base_url}}/assets/img/project/time_log_costing.png">

* After submitting the Time Log, you need to create [Time Log batch]({{docs_base_url}}/user/manual/en/projects/time-log-batch.html) to further bill the Time Log.

{next}
