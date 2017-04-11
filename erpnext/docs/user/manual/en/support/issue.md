Issue is an incoming query from your Customer, usually via email or
from the “Contact” section of your website. (To fully integrate the Support
Ticket to email, see the Email Settings section).

> Tip: A dedicated support Email Address is a good way to integrate incoming
queries via email. For example, you can send support queries to ERPNext at
support@erpnext.com and it will automatically create a Issue in the
Frappe system.



> Support > Issue > New Issue

<img class="screenshot" alt="Issue" src="{{docs_base_url}}/assets/img/support/issue.png">

#### Discussion Thread

When a new email is fetched from your mailbox, a new Issue record is
created and an automatic reply is sent to the sender indicating the Support
Ticket Number. The sender can send additional information to this email. All
subsequent emails containing this Issue number in the subject will be
added to this Issue thread. The sender can also add attachments to
the email.

Issue maintains all the emails which are sent back and forth against
this issue in the system so that you can track what transpired between the
sender and the person responding.

#### Status

When a new Issue is created, its status is “Open”, when it is
replied, its status becomes “Waiting for Reply”. If the sender replies back
its status again becomes “Open”.

#### Closing

You can either “Close” the Issue manually by clicking on “Close
Ticket” in the toolbar or if its status is “Waiting For Reply” . If the sender
does not reply in 7 days, then the Issue closes automatically.

#### Allocation

You can allocate the Issue by using the “Assign To” feature in the
right sidebar. This will add a new To Do to the user and also send a message
indicating that this Issue is allocated.

{next}
