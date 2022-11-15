import frappe

def execute():
	frappe.reload_doctype('Task')
	for t in frappe.get_all('Task', fields=['name']):
		task = frappe.get_doc('Task', t.name)
		task.update_depends_on()
		if task.depends_on_tasks:
			task.db_set('depends_on_tasks', task.depends_on_tasks, update_modified=False)
