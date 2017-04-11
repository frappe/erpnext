from __future__ import unicode_literals
import frappe
import calendar
import frappe.utils
import frappe.defaults

from frappe.utils import cint, cstr, getdate, nowdate, \
	get_first_day, get_last_day, split_emails

from frappe import _, msgprint, throw

month_map = {'Monthly': 1, 'Quarterly': 3, 'Half-yearly': 6, 'Yearly': 12}
date_field_map = {
	"Sales Order": "transaction_date",
	"Sales Invoice": "posting_date",
	"Purchase Order": "transaction_date",
	"Purchase Invoice": "posting_date"
}

def create_recurring_documents():
	manage_recurring_documents("Sales Order")
	manage_recurring_documents("Sales Invoice")
	manage_recurring_documents("Purchase Order")
	manage_recurring_documents("Purchase Invoice")

def manage_recurring_documents(doctype, next_date=None, commit=True):
	"""
		Create recurring documents on specific date by copying the original one
		and notify the concerned people
	"""
	next_date = next_date or nowdate()

	date_field = date_field_map[doctype]

	condition = " and ifnull(status, '') != 'Closed'" if doctype in ("Sales Order", "Purchase Order") else ""

	recurring_documents = frappe.db.sql("""select name, recurring_id
		from `tab{0}` where is_recurring=1
		and (docstatus=1 or docstatus=0) and next_date=%s
		and next_date <= ifnull(end_date, '2199-12-31') {1}""".format(doctype, condition), next_date)

	exception_list = []
	for ref_document, recurring_id in recurring_documents:
		if not frappe.db.sql("""select name from `tab%s`
				where %s=%s and recurring_id=%s and (docstatus=1 or docstatus=0)"""
				% (doctype, date_field, '%s', '%s'), (next_date, recurring_id)):
			try:
				reference_doc = frappe.get_doc(doctype, ref_document)
				new_doc = make_new_document(reference_doc, date_field, next_date)
				if reference_doc.notify_by_email:
					send_notification(new_doc)
				if commit:
					frappe.db.commit()
			except:
				if commit:
					frappe.db.rollback()

					frappe.db.begin()
					frappe.db.sql("update `tab%s` \
						set is_recurring = 0 where name = %s" % (doctype, '%s'),
						(ref_document))
					notify_errors(ref_document, doctype, reference_doc.get("customer") or reference_doc.get("supplier"),
						reference_doc.owner)
					frappe.db.commit()

				exception_list.append(frappe.get_traceback())
			finally:
				if commit:
					frappe.db.begin()

	if exception_list:
		exception_message = "\n\n".join([cstr(d) for d in exception_list])
		frappe.throw(exception_message)

def make_new_document(reference_doc, date_field, posting_date):
	new_document = frappe.copy_doc(reference_doc, ignore_no_copy=False)
	mcount = month_map[reference_doc.recurring_type]

	from_date = get_next_date(reference_doc.from_date, mcount)

	# get last day of the month to maintain period if the from date is first day of its own month
	# and to date is the last day of its own month
	if (cstr(get_first_day(reference_doc.from_date)) == cstr(reference_doc.from_date)) and \
		(cstr(get_last_day(reference_doc.to_date)) == cstr(reference_doc.to_date)):
			to_date = get_last_day(get_next_date(reference_doc.to_date, mcount))
	else:
		to_date = get_next_date(reference_doc.to_date, mcount)

	new_document.update({
		date_field: posting_date,
		"from_date": from_date,
		"to_date": to_date,
		"next_date": get_next_date(reference_doc.next_date, mcount,cint(reference_doc.repeat_on_day_of_month))
	})

	if new_document.meta.get_field('set_posting_time'):
		new_document.set('set_posting_time', 1)

	# copy document fields
	for fieldname in ("owner", "recurring_type", "repeat_on_day_of_month",
		"recurring_id", "notification_email_address", "is_recurring", "end_date",
		"title", "naming_series", "select_print_heading", "ignore_pricing_rule",
		"posting_time", "remarks", 'submit_on_creation'):
		if new_document.meta.get_field(fieldname):
			new_document.set(fieldname, reference_doc.get(fieldname))

	# copy item fields
	for i, item in enumerate(new_document.items):
		for fieldname in ("page_break",):
			item.set(fieldname, reference_doc.items[i].get(fieldname))

	new_document.run_method("on_recurring", reference_doc=reference_doc)

	if reference_doc.submit_on_creation:
		new_document.insert()
		new_document.submit()
	else:
		new_document.docstatus=0
		new_document.insert()

	return new_document

def get_next_date(dt, mcount, day=None):
	dt = getdate(dt)

	from dateutil.relativedelta import relativedelta
	dt += relativedelta(months=mcount, day=day)

	return dt

def send_notification(new_rv):
	"""Notify concerned persons about recurring document generation"""

	frappe.sendmail(new_rv.notification_email_address,
		subject=  _("New {0}: #{1}").format(new_rv.doctype, new_rv.name),
		message = _("Please find attached {0} #{1}").format(new_rv.doctype, new_rv.name),
		attachments = [frappe.attach_print(new_rv.doctype, new_rv.name, file_name=new_rv.name, print_format=new_rv.recurring_print_format)])

def notify_errors(doc, doctype, party, owner):
	from frappe.utils.user import get_system_managers
	recipients = get_system_managers(only_name=True)

	frappe.sendmail(recipients + [frappe.db.get_value("User", owner, "email")],
		subject="[Urgent] Error while creating recurring %s for %s" % (doctype, doc),
		message = frappe.get_template("templates/emails/recurring_document_failed.html").render({
			"type": doctype,
			"name": doc,
			"party": party
		}))

	assign_task_to_owner(doc, doctype, "Recurring Invoice Failed", recipients)

def assign_task_to_owner(doc, doctype, msg, users):
	for d in users:
		from frappe.desk.form import assign_to
		args = {
			'assign_to' 	:	d,
			'doctype'		:	doctype,
			'name'			:	doc,
			'description'	:	msg,
			'priority'		:	'High'
		}
		assign_to.add(args)

def validate_recurring_document(doc):
	if doc.is_recurring:
		validate_notification_email_id(doc)
		if not doc.recurring_type:
			frappe.throw(_("Please select {0}").format(doc.meta.get_label("recurring_type")))

		elif not (doc.from_date and doc.to_date):
			frappe.throw(_("Period From and Period To dates mandatory for recurring {0}").format(doc.doctype))

def validate_recurring_next_date(doc):
	posting_date = doc.get("posting_date") or doc.get("transaction_date")
	if getdate(posting_date) > getdate(doc.next_date):
		frappe.throw(_("Next Date must be greater than Posting Date"))

	next_date = getdate(doc.next_date)
	if next_date.day != doc.repeat_on_day_of_month:

		# if the repeat day is the last day of the month (31)
		# and the current month does not have as many days,
		# then the last day of the current month is a valid date
		lastday = calendar.monthrange(next_date.year, next_date.month)[1]
		if doc.repeat_on_day_of_month < lastday:

			# the specified day of the month is not same as the day specified
			# or the last day of the month
			frappe.throw(_("Next Date's day and Repeat on Day of Month must be equal"))

def convert_to_recurring(doc, posting_date):
	if doc.is_recurring:
		if not doc.recurring_id:
			doc.db_set("recurring_id", doc.name)

		set_next_date(doc, posting_date)

		if doc.next_date:
			validate_recurring_next_date(doc)

	elif doc.recurring_id:
		doc.db_set("recurring_id", None)

def validate_notification_email_id(doc):
	if doc.notify_by_email:
		if doc.notification_email_address:
			email_list = split_emails(doc.notification_email_address.replace("\n", ""))

			from frappe.utils import validate_email_add
			for email in email_list:
				if not validate_email_add(email):
					throw(_("{0} is an invalid email address in 'Notification \
						Email Address'").format(email))

		else:
			frappe.throw(_("'Notification Email Addresses' not specified for recurring %s") \
				% doc.doctype)

def set_next_date(doc, posting_date):
	""" Set next date on which recurring document will be created"""
	if not doc.repeat_on_day_of_month:
		msgprint(_("Please enter 'Repeat on Day of Month' field value"), raise_exception=1)

	next_date = get_next_date(posting_date, month_map[doc.recurring_type],
		cint(doc.repeat_on_day_of_month))

	doc.db_set('next_date', next_date)

	msgprint(_("Next Recurring {0} will be created on {1}").format(doc.doctype, next_date))
