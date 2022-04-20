import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("projects", "doctype", "project")
	frappe.reload_doc("projects", "doctype", "project_status")

	if frappe.db.has_column("Project", 'is_released'):
		rename_field("Project", 'is_released', 'ready_to_close')

	# STATUS Released -> To Close
	frappe.db.sql("""
		update `tabProject`
		set status = 'To Close'
		where status = 'Released'
	""")
	frappe.db.sql("""
		update `tabProject Status`
		set status = 'To Close'
		where status = 'Released'
	""")

	# STATUS Closed -> Completed
	frappe.db.sql("""
		update `tabProject`
		set status = 'Completed'
		where status = 'Closed'
	""")

	frappe.db.sql("""
		update `tabProject Status`
		set status = 'Completed'
		where status = 'Closed'
	""")
