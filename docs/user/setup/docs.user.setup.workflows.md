---
{
	"_label": "Workflows"
}
---
In order to allow multiple people to submit  multiple requests, for approvals, by multiple users, ERPNext requires you to fill the workflow conditions. ERPNext tracks the multiple permissions before submission.

Example of a leave application workflow is given below:

If an user  applies for a leave, then his request will be sent to the HR department. The HR department(HR User) will either reject or approve this request. Once this process is completed, the user's Manager(leave approver) will get an indication that the HR department has Accepted or Rejected. The Manager, who is the approving authority, will either Approve or Reject this request. Accordingly,the user will get his Approved or Rejected status. 

![Workflow](img/workflow-leave-fl.jpg)




To make this Workflow and transition rules go to :

 > Setup > Workflow > New Workflow


#### Step 1: Enter the different states of Leave Approval Process.


 ![Workflow](img/workflow-leave1.png)



#### Step 2: Enter Transition Rules.


![Workflow](img/workflow-leave2.png)


Example of a Leave Application Process:

Go to the Human Resources Module and click on Leave Application. Apply for a Leave.

When a Leave Application is submitted, the status on the right hand corner of the page shows as "Applied"

![Workflow Employee LA](img/workflow-employee-la.png)

When the HR User logs in,  he can either Approve or Reject. If approved the status on the right hand corner of the page shows as Approved. However, a blue band of information is displayed saying approval is pending by leave approver.

![Leave Approver](img/workflow-hr-user-la.png)


When the leave approver opens the Leave Application page, he should select the status and convert to Approved or Rejected.

![Workflow Leave Approver](img/workflow-leave-approver-la.png)


