import frappe

def execute():
	qms_icons = frappe.get_all("Desktop Icon", filters={
		"module_name": "Quality Management"
	})

	for icon in qms_icons:
		frappe.db.set_value('Desktop Icon', icon.name, 'color', '#1abc9c')
		frappe.db.set_value('Desktop Icon', icon.name, 'icon', 'fa fa-check-square-o')
