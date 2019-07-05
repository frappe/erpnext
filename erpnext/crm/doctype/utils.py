import frappe
from frappe import _
import json

@frappe.whitelist()
def get_document_with_phone_number(number):
	# finds contacts and leads
	if not number: return
	number = number.lstrip('0')
	number_filter = {
		'phone': ['like', '%{}'.format(number)],
		'mobile_no': ['like', '%{}'.format(number)]
	}
	contacts = frappe.get_all('Contact', or_filters=number_filter, limit=1)

	if contacts:
		return frappe.get_doc('Contact', contacts[0].name)

	leads = frappe.get_all('Lead', or_filters=number_filter, limit=1)

	if leads:
		return frappe.get_doc('Lead', leads[0].name)

@frappe.whitelist()
def get_last_interaction(number, reference_doc):
	reference_doc = json.loads(reference_doc) if reference_doc else get_document_with_phone_number(number)

	if not reference_doc: return

	reference_doc = frappe._dict(reference_doc)

	last_communication = {}
	last_issue = {}
	if reference_doc.doctype == 'Contact':
		customer_name = ''
		query_condition = ''
		for link in reference_doc.links:
			link = frappe._dict(link)
			if link.link_doctype == 'Customer':
				customer_name = link.link_name
			query_condition += "(`reference_doctype`='{}' AND `reference_name`='{}') OR".format(link.link_doctype, link.link_name)

		if query_condition:
			query_condition = query_condition[:-2]
			last_communication = frappe.db.sql("""
				SELECT `name`, `content`
				FROM `tabCommunication`
				WHERE {}
				ORDER BY `modified`
				LIMIT 1
			""".format(query_condition)) # nosec

		if customer_name:
			last_issue = frappe.get_all('Issue', {
				'customer': customer_name
			}, ['name', 'subject', 'customer'], limit=1)

	elif reference_doc.doctype == 'Lead':
		last_communication = frappe.get_all('Communication', filters={
			'reference_doctype': reference_doc.doctype,
			'reference_name': reference_doc.name,
			'sent_or_received': 'Received'
		}, fields=['name', 'content'], limit=1)

	return {
		'last_communication': last_communication[0] if last_communication else None,
		'last_issue': last_issue[0] if last_issue else None
	}

@frappe.whitelist()
def add_call_summary(docname, summary):
	call_log = frappe.get_doc('Call Log', docname)
	summary = _('Call Summary by {0}: {1}').format(
		frappe.utils.get_fullname(frappe.session.user), summary)
	if not call_log.summary:
		call_log.summary = summary
	else:
		call_log.summary += '<br>' + summary
	call_log.save(ignore_permissions=True)

def get_employee_emails_for_popup(communication_medium):
	now_time = frappe.utils.nowtime()
	weekday = frappe.utils.get_weekday()

	available_employee_groups = frappe.get_all("Communication Medium Timeslot", filters={
		'day_of_week': weekday,
		'parent': communication_medium,
		'from_time': ['<=', now_time],
		'to_time': ['>=', now_time],
	}, fields=['employee_group'])

	available_employee_groups = tuple([emp.employee_group for emp in available_employee_groups])

	employees = frappe.get_all('Employee Group Table', filters={
		'parent': ['in', available_employee_groups]
	}, fields=['user_id'])

	employee_emails = set([employee.user_id for employee in employees])

	return employee_emails
