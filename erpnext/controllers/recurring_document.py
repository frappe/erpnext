from __future__ import unicode_literals
import frappe
import frappe.utils
import frappe.defaults

from frappe.utils import add_days, cint, cstr, date_diff, flt, getdate, nowdate, \
	get_first_day, get_last_day, comma_and
from frappe.model.naming import make_autoname

from frappe import _, msgprint, throw
from erpnext.accounts.party import get_party_account, get_due_date, get_party_details
from frappe.model.mapper import get_mapped_doc

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

	recurring_documents = frappe.db.sql("""select name, recurring_id
		from `tab{}` where ifnull(is_recurring, 0)=1
		and docstatus=1 and next_date='{}'
		and next_date <= ifnull(end_date, '2199-12-31')""".format(doctype, next_date))

	exception_list = []
	for ref_document, recurring_id in recurring_documents:
		if not frappe.db.sql("""select name from `tab%s`
				where %s=%s and recurring_id=%s and docstatus=1"""
				% (doctype, date_field, '%s', '%s'), (next_date, recurring_id)):
			try:
				ref_wrapper = frappe.get_doc(doctype, ref_document)
				if hasattr(ref_wrapper, "before_recurring"):
					ref_wrapper.before_recurring()

				new_document_wrapper = make_new_document(ref_wrapper, date_field, next_date)
				send_notification(new_document_wrapper)
				if commit:
					frappe.db.commit()
			except:
				if commit:
					frappe.db.rollback()

					frappe.db.begin()
					frappe.db.sql("update `tab%s` \
						set is_recurring = 0 where name = %s" % (doctype, '%s'),
						(ref_document))
					notify_errors(ref_document, doctype, ref_wrapper.get("customer") or ref_wrapper.get("supplier"),
						ref_wrapper.owner)
					frappe.db.commit()

				exception_list.append(frappe.get_traceback())
			finally:
				if commit:
					frappe.db.begin()

	if exception_list:
		exception_message = "\n\n".join([cstr(d) for d in exception_list])
		frappe.throw(exception_message)

def make_new_document(ref_wrapper, date_field, posting_date):
	from erpnext.accounts.utils import get_fiscal_year
	new_document = frappe.copy_doc(ref_wrapper)
	mcount = month_map[ref_wrapper.recurring_type]

	from_date = get_next_date(ref_wrapper.from_date, mcount)

	# get last day of the month to maintain period if the from date is first day of its own month
	# and to date is the last day of its own month
	if (cstr(get_first_day(ref_wrapper.from_date)) == \
			cstr(ref_wrapper.from_date)) and \
		(cstr(get_last_day(ref_wrapper.to_date)) == \
			cstr(ref_wrapper.to_date)):
		to_date = get_last_day(get_next_date(ref_wrapper.to_date,
			mcount))
	else:
		to_date = get_next_date(ref_wrapper.to_date, mcount)

	new_document.update({
		date_field: posting_date,
		"from_date": from_date,
		"to_date": to_date,
		"fiscal_year": get_fiscal_year(posting_date)[0],
		"owner": ref_wrapper.owner,
	})

	if ref_wrapper.doctype == "Sales Order":
		new_document.update({
			"delivery_date": get_next_date(ref_wrapper.delivery_date, mcount,
				cint(ref_wrapper.repeat_on_day_of_month))
	})

	new_document.submit()

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
		attachments = [frappe.attach_print(new_rv.doctype, new_rv.name, file_name=new_rv.name)])

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
			msgprint(_("Please select {0}").format(doc.meta.get_label("recurring_type")),
			raise_exception=1)

		elif not (doc.from_date and doc.to_date):
			throw(_("Period From and Period To dates mandatory for recurring %s") % doc.doctype)

#
def convert_to_recurring(doc, posting_date):
    if doc.is_recurring:
        if not doc.recurring_id:
            frappe.db.set(doc, "recurring_id", doc.name)

        set_next_date(doc, posting_date)

    elif doc.recurring_id:
        frappe.db.sql("""update `tab%s` set is_recurring = 0
            where recurring_id = %s""" % (doc.doctype, '%s'), (doc.recurring_id))
#

def validate_notification_email_id(doc):
	if doc.notification_email_address:
		email_list = filter(None, [cstr(email).strip() for email in
			doc.notification_email_address.replace("\n", "").split(",")])

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

	frappe.db.set(doc, 'next_date', next_date)

	msgprint(_("Next Recurring {0} will be created on {1}").format(doc.doctype, next_date))
