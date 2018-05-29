# Workflows

In order to allow multiple people to submit multiple requests, for approvals,
by multiple users, ERPNext requires you to fill the workflow conditions.
ERPNext tracks the multiple permissions before submission.

Example of a leave application workflow is given below:

If a user applies for a leave, then his request will be sent to the HR
department. The HR department (HR User) will either reject or approve this
request. Once this process is completed, the user's Manager (leave approver)
will get an indication that the HR department has Accepted or Rejected. The
Manager, who is the approving authority, will either Approve or Reject this
request. Accordingly,the user will get his Approved or Rejected status.

<img class="screenshot" alt="Workflow" src="{{docs_base_url}}/assets/img/setup/workflow-leave-fl.jpg">

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


#### Enable/Disable Self approval

> New in Version 11

<img class="screenshot" alt="Workflow" src="{{docs_base_url}}/assets/img/setup/workflow-6.png">


#### Conditions

> New in Version 11

In Version 11, you can also add a condition for the transition to be applicable. For example in this case if someone applies to leave for more than 5 days, a particular role must approve. For this in the particular transition you can set a property for `Condition` as:

```
doc.total_leave_days <= 5
```

Then if someone applied for leave for less than 5 days, only that particular transition will apply.

This can be extended to any property of the document.

#### Example of a Leave Application Process:

When a Leave Application is saved by Employee, the status of the document changes to "Applied"

<img class="screenshot" alt="Workflow" src="{{docs_base_url}}/assets/img/setup/workflow-3.png">

When the HR User logs in, he can either Approve or Reject. If approved the
status of the document changes to "Approved by HR". However, it is yet to be approved by Leave Approver.

<img class="screenshot" alt="Workflow" src="{{docs_base_url}}/assets/img/setup/workflow-4.png">

When the Leave Approver opens the Leave Application page, he can finally "Approve" or "Reject" the Leave Application.

<img class="screenshot" alt="Workflow" src="{{docs_base_url}}/assets/img/setup/workflow-5.png">

#### Workflow Actions

> New in Version 11

Workflow Actions is a single place to manage all the pending actions you can take on Workflows.

If a User is eligible to take action on some workflows, emails will be sent to the user, with the relevant document as attachment, from where the user can `Approve` or `Reject` the Workflow.
<img class="screenshot" alt="Workflow" src="{{docs_base_url}}/assets/img/setup/workflow-actions-email.png">

Also the users will see entries in their Workflow Action list.
<img class="screenshot" alt="Workflow" src="{{docs_base_url}}/assets/img/setup/workflow-actions-list.png">

**Note:** You can set email template for Workflow Actions on each state.
The template might consist message for users to proceed with the next Workflow Actions


### Video Tutorial:

<div>
    <div class="embed-container">
        <iframe src="https://www.youtube.com/embed/yObJUg9FxFs?rel=0" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen>
        </iframe>
    </div>
</div>

{next}

