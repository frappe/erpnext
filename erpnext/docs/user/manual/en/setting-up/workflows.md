In order to allow multiple people to submit multiple requests, for approvals,
by multiple users, ERPNext requires you to fill the workflow conditions.
ERPNext tracks the multiple permissions before submission.

Example of a leave application workflow is given below:

If an user applies for a leave, then his request will be sent to the HR
department. The HR department(HR User) will either reject or approve this
request. Once this process is completed, the user's Manager(leave approver)
will get an indication that the HR department has Accepted or Rejected. The
Manager, who is the approving authority, will either Approve or Reject this
request. Accordingly,the user will get his Approved or Rejected status.

![Workflow]({{docs_base_url}}/assets/old_images/erpnext/workflow-leave-fl.jpg)

To make this Workflow and transition rules go to :

> Setup > Workflow > New Workflow

#### Step 1: Enter the different states of Leave Approval Process.

<img class="screenshot" alt="Workflow" src="{{docs_base_url}}/assets/img/setup/workflow-1.png">

#### Step 2: Enter Transition Rules.

<img class="screenshot" alt="Workflow" src="{{docs_base_url}}/assets/img/setup/workflow-2.png">

#### Notes:

> Note 1: When you make a workflow you essentially overwrite the code that is
written for that document. Thus the document will function based on your
workflow and not based on the pre-set code settings. Hence there might be no
submit button / option if you have not specified it in the workflow.

> Note 2: Document status of saved is 0, of submitted is 1, and of cancelled is
2.

> Note 3: A document cannot be cancelled unless it is submitted.

> Note 4: If you wish to give the option to cancel, you will have to write a
workflow transition step that says from submitted you can cancel.

  

#### Example of a Leave Application Process:  

Go to the Human Resources Module and click on Leave Application. Apply for a
Leave.

When a Leave Application is submitted, the status on the right hand corner of
the page shows as "Applied"

![Workflow Employee LA]({{docs_base_url}}/assets/old_images/erpnext/workflow-employee-la.png)

When the HR User logs in, he can either Approve or Reject. If approved the
status on the right hand corner of the page shows as Approved. However, a blue
band of information is displayed saying approval is pending by leave approver.

![Leave Approver]({{docs_base_url}}/assets/old_images/erpnext/workflow-hr-user-la.png)

When the leave approver opens the Leave Application page, he should select the
status and convert to Approved or Rejected.

![Workflow Leave Approver]({{docs_base_url}}/assets/old_images/erpnext/workflow-leave-approver-la.png)

{next}
