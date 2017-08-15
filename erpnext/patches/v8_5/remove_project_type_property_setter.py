import frappe

def execute():
	ps = frappe.db.get_value('Property Setter', dict(doc_type='Project', field_name='project_type',
		property='options'))
	if ps:
		frappe.delete_doc('Property Setter', ps)

	project_types = frappe.db.sql_list('select distinct project_type from tabProject')

	for project_type in project_types:
		if project_type and not frappe.db.exists("Project Type", project_type):
			p_type = frappe.get_doc({
				"doctype": "Project Type",
				"project_type": project_type
			})
			p_type.insert()