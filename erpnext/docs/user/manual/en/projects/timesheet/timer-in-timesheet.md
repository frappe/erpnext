
# Timer in Timesheet

Timesheets can be tracked against Project and Tasks along with a Timer.

<img class="screenshot" alt="Timer" src="{{docs_base_url}}/assets/img/project/timesheet/timesheet-timer.gif">

#### Steps to start a Timer:

- On clicking, **Start Timer**, a dialog pops up and starts the timer for already present activity for which checkbox `completed` is unchecked.

<img class="screenshot" alt="Timer in Progress" src="{{docs_base_url}}/assets/img/project/timesheet/timesheet-timer-in-progress.png">

- If no activities are present, fill up the activity details, i.e. activity type, expected hours or project in the dialog itself, on clicking **Start**, a new row is added into the Timesheet Details child table and timer begins.

- On clicking, **Complete**, the `hours` and `to_time` fields are updated for that particular activity.

<img class="screenshot" alt="Timer Completed" src="{{docs_base_url}}/assets/img/project/timesheet/timesheet-after-complete.png">

- At any point of time, if the dialog is closed without completing the activity, on opening the dialog again, the timer resumes by calculating how much time has elapsed since `from_time` of the activity.

- If any activities are already present in the Timesheet with completed unchecked, clicking on **Resume Timer** fetches the activity and starts its timer.

- If the time exceeds the `expected_hours`, an alert box appears.

<img class="screenshot" alt="Timer Exceeded" src="{{docs_base_url}}/assets/img/project/timesheet/timesheet-timer-alert.png">
