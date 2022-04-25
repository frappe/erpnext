import frappe

def execute():
	frappe.reload_doc("projects", "doctype", "project")
	frappe.reload_doc("projects", "doctype", "projects_settings")
	settings = frappe.get_single("Projects Settings")
	frappe.db.sql("""
		update `tabProject`
		set materials_item_group = %s,
			consumables_item_group = %s,
			lubricants_item_group = %s,
			sublet_item_group = %s
	""", [
		settings.materials_item_group,
		settings.consumables_item_group,
		settings.lubricants_item_group,
		settings.sublet_item_group,
	])
