# Email Alerts

You can configure various email alerts in your system to remind you of important activities such as:

1. Completion date of a Task.
2. Expected Delivery Date of a Sales Order.
3. Expected Payment Date.
4. Reminder of followup.
5. If an Order greater than a particular value is received or sent.
6. Expiry notification for a Contract.
7. Completion / Status change of a Task.

For this, you need to setup an Email Alert.

> Setup > Email > Email Alert

### Setting Up An Alert

To setup an Email Alert:

1. Select which Document Type you want watch changes on
2. Define what events you want to watch. Events are:
	1. New: When a new document of the selected type is made.
	2. Save / Submit / Cancel: When a document of the selected type is saved, submitted, cancelled.
	3. Value Change: When a particular value in the selected type changes.
	4. Days Before / Days After: Trigger this alert a few days before or after the **Reference Date.** To set the days, set **Days Before or After**. This can be useful in reminding you of upcoming due dates or reminding you to follow up on certain leads of quotations.
3. Set additional conditions if you want.
4. Set the recipients of this alert. The recipient could either be a field of the document or a list of fixed Email Addresses.
5. Compose the message


### Setting a Subject
You can retrieve the data for a particular field by using `doc.[field_name]`. To use it in your subject / message, you have to surround it with `{% raw %}{{ }}{% endraw %}`. These are called [Jinja](http://jinja.pocoo.org/) tags. So, for example to get the name of a document, you use `{% raw %}{{ doc.name }}{% endraw %}`. The below example sends an email on saving a Task with the Subject, "TASK##### has been created"

<img class="screenshot" alt="Setting Subject" src="/docs/assets/img/setup/email/email-alert-subject.png">

### Setting Conditions

Email alerts allow you to set conditions according to the field data in your documents. For example, if you want to recieve an Email if a Lead has been saved as "Interested" as it's status, you put `doc.status == "Interested"` in the conditions textbox. You can also set more complex conditions by combining them.

<img class="screenshot" alt="Setting Condition" src="/docs/assets/img/setup/email/email-alert-condition.png">

The above example will send an Email Alert when a Task is saved with the status "Open" and the Expected End Date for the Task is the date on or before the date on which it was saved on.


### Setting a Message

You can use both Jinja Tags (`{% raw %}{{ doc.[field_name] }}{% endraw %}`) and HTML tags in the message textbox.

	{% raw %}<h3>Order Overdue</h3>

	<p>Transaction {{ doc.name }} has exceeded Due Date. Please take necessary action.</p>

	<!-- show last comment -->
	{% if comments %}
	Last comment: {{ comments[-1].comment }} by {{ comments[-1].by }}
	{% endif %}

	<h4>Details</h4>

	<ul>
	<li>Customer: {{ doc.customer }}
	<li>Amount: {{ doc.total_amount }}
	</ul>{% endraw %}

---

### Setting a Value after the Alert is Set

Sometimes to make sure that the email alert is not sent multiple times, you can
define a custom property (via Customize Form) like "Email Alert Sent" and then
set this property after the alert is sent by setting the **Set Property After Alert**
field.

Then you can use that as a condition in the **Condition** rules to ensure emails are not sent multiple times

<img class="screenshot" alt="Setting Property in Email Alert" src="/docs/assets/img/setup/email/email-alert-subject.png">

### Example

1. Defining the Criteria
    <img class="screenshot" alt="Defining Criteria" src="/docs/assets/img/setup/email/email-alert-1.png">

1. Setting the Recipients and Message
    <img class="screenshot" alt="Set Message" src="/docs/assets/img/setup/email/email-alert-2.png">

{next}
