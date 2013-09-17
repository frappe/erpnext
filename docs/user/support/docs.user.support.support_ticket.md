---
{
	"_label": "Support Ticket"
}
---
Support Ticket is an incoming query from your Customer, usually via email or from the “Contact” section of your website. (To fully integrate the Support Ticket to email, see the Email Settings section). 

> Tip: A dedicated support email id is a good way to integrate incoming queries via email. For example, you can send support queries to ERPNext at support@erpnext.com and it will automatically create a Support Ticket in the Web Notes system.

<br>


> Support > Support Ticket > New Support Ticket



![Support Ticket](img/support-ticket.png)



#### Discussion Thread

When a new email is fetched from your mailbox, a new Support Ticket record is created and an automatic reply is sent to the sender indicating the Support Ticket Number. The sender can send additional information to this email. All subsequent emails containing this Support Ticket number in the subject will be added to this Support Ticket thread. The sender can also add attachments to the email.

Support Ticket maintains all the emails which are sent back and forth against this issue in the system so that you can track what transpired between the sender and the person responding. 

#### Status

When a new Support Ticket is created, its status is “Open”, when it is replied, its status becomes “Waiting for Reply”. If the sender replies back its status again becomes “Open”.

#### Closing

You can either “Close” the Support Ticket manually by clicking on “Close Ticket” in the toolbar or if its status is “Waiting For Reply” . If the sender does not reply in 7 days, then the Support Ticket closes automatically.

#### Allocation

You can allocate the Support Ticket by using the “Assign To” feature in the right sidebar. This will add a new To Do to the user and also send a message indicating that this Support Ticket is allocated.