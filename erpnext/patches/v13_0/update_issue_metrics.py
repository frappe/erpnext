from __future__ import unicode_literals
import frappe

from frappe.core.doctype.communication.communication import set_avg_response_time
from erpnext.support.doctype.issue.issue import set_resolution_time, set_user_resolution_time

def execute():
	if frappe.db.exists('DocType', 'Issue'):
		frappe.reload_doctype('Issue')

		count = 0
		for parent in frappe.get_all('Issue', order_by='creation desc'):
			parent_doc = frappe.get_doc('Issue', parent.name)

			communication = frappe.get_all('Communication', filters={
				'reference_doctype': 'Issue',
				'reference_name': parent.name,
				'communication_medium': 'Email',
				'sent_or_received': 'Sent'
			}, order_by = 'creation asc', limit=1)

			if communication:
				communication_doc = frappe.get_doc('Communication', communication[0].name)
				set_avg_response_time(parent_doc, communication_doc)

			if parent_doc.status in ['Closed', 'Resolved']:
				set_resolution_time(parent_doc)
				set_user_resolution_time(parent_doc)

			# commit after every 100 records
			count += 1
			if count % 100 == 0:
				frappe.db.commit()