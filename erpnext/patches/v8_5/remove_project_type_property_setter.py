import frappe

def execute():
	ps = frappe.db.get_value('Property Setter', dict(doc_type='Project', field_name='project_type',
		property='options'))
	if ps:
		frappe.delete_doc('Property Setter', ps)