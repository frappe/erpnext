import frappe

from frappe.core.doctype.communication.email import update_mins_to_first_communication

def execute():
	frappe.reload_doctype('Issue')
	frappe.reload_doctype('Opportunity')

	for doctype in ('Issue', 'Opportunity'):
		for parent in frappe.get_all(doctype, order_by='creation desc', limit=1000):
			for communication in frappe.get_all('Communication',
				filters={'reference_doctype': doctype, 'reference_name': parent.name},
				order_by = 'creation desc', limit=2):

				parent_doc = frappe.get_doc(doctype, parent.name)
				communication_doc = frappe.get_doc('Communication', communication.name)

				update_mins_to_first_communication(parent_doc, communication_doc)

				if parent_doc.mins_to_first_response:
					continue