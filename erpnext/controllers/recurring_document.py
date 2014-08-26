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

def manage_recurring_documents(doctype, next_date=None, commit=True):
	"""
		Create recurring documents on specific date by copying the original one
		and notify the concerned people
	"""
	next_date = next_date or nowdate()

	if doctype == "Sales Order":
		date_field = "transaction_date"
	elif doctype == "Sales Invoice":
		date_field = "posting_date"

	recurring_documents = frappe.db.sql("""select name, recurring_id
		from `tab%s` where ifnull(convert_into_recurring, 0)=1
		and docstatus=1 and next_date=%s
		and next_date <= ifnull(end_date, '2199-12-31')""" % (doctype, '%s'), (next_date))

	exception_list = []
	for ref_document, recurring_id in recurring_documents:
		if not frappe.db.sql("""select name from `tab%s`
				where %s=%s and recurring_id=%s and docstatus=1"""
				% (doctype, date_field, '%s', '%s'), (next_date, recurring_id)):
			try:
				ref_wrapper = frappe.get_doc(doctype, ref_document)
				new_document_wrapper = make_new_document(ref_wrapper, date_field, next_date)
				send_notification(new_document_wrapper)
				if commit:
					frappe.db.commit()
			except:
				if commit:
					frappe.db.rollback()

					frappe.db.begin()
					frappe.db.sql("update `tab%s` \
						set convert_into_recurring = 0 where name = %s" % (doctype, '%s'), 
						(ref_document))
					notify_errors(ref_document, doctype, ref_wrapper.customer, ref_wrapper.owner)
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

	period_from = get_next_date(ref_wrapper.period_from, mcount)

	# get last day of the month to maintain period if the from date is first day of its own month
	# and to date is the last day of its own month
	if (cstr(get_first_day(ref_wrapper.period_from)) == \
			cstr(ref_wrapper.period_from)) and \
		(cstr(get_last_day(ref_wrapper.period_to)) == \
			cstr(ref_wrapper.period_to)):
		period_to = get_last_day(get_next_date(ref_wrapper.period_to,
			mcount))
	else:
		period_to = get_next_date(ref_wrapper.period_to, mcount)

	new_document.update({
		date_field: posting_date,
		"period_from": period_from,
		"period_to": period_to,
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
		attachments = [{
			"fname": new_rv.name + ".pdf",
			"fcontent": frappe.get_print_format(new_rv.doctype, new_rv.name, as_pdf=True)
		}])

def notify_errors(doc, doctype, customer, owner):
	from frappe.utils.user import get_system_managers
	recipients = get_system_managers(only_name=True)

	frappe.sendmail(recipients + [frappe.db.get_value("User", owner, "email")],
		subject="[Urgent] Error while creating recurring %s for %s" % (doctype, doc),
		message = frappe.get_template("templates/emails/recurring_sales_invoice_failed.html").render({
			"type": doctype,
			"name": doc,
			"customer": customer
		}))

	assign_task_to_owner(doc, doctype, "Recurring Invoice Failed", recipients)

def assign_task_to_owner(doc, doctype, msg, users):
	for d in users:
		from frappe.widgets.form import assign_to
		args = {
			'assign_to' 	:	d,
			'doctype'		:	doctype,
			'name'			:	doc,
			'description'	:	msg,
			'priority'		:	'High'
		}
		assign_to.add(args)