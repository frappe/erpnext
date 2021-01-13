from __future__ import unicode_literals
import frappe

from frappe.core.doctype.communication.communication import update_mins_to_first_communication

def execute():
	frappe.reload_doctype('Issue')
	frappe.reload_doctype('Opportunity')

	for doctype in ('Issue', 'Opportunity'):
		frappe.db.sql('update tab{0} set mins_to_first_response=0'.format(doctype))
		for parent in frappe.get_all(doctype, order_by='creation desc', limit=500):
			parent_doc = frappe.get_doc(doctype, parent.name)
			for communication in frappe.get_all('Communication',
				filters={'reference_doctype': doctype, 'reference_name': parent.name,
				'communication_medium': 'Email'},
				order_by = 'creation asc', limit=2):

				communication_doc = frappe.get_doc('Communication', communication.name)

				update_mins_to_first_communication(parent_doc, communication_doc)

				if parent_doc.mins_to_first_response:
					continue