import frappe


def execute():
	if "Education" in frappe.get_active_domains() and not frappe.db.exists("Role", "Guardian"):
		doc = frappe.new_doc("Role")
		doc.update({"role_name": "Guardian", "desk_access": 0})

		doc.insert(ignore_permissions=True)
