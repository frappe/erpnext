import frappe

def execute():
	frappe.reload_doctype("Task")

	from erpnext.projects.doctype.task.task import set_tasks_as_overdue
	set_tasks_as_overdue()
