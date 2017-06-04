import frappe

def execute():
	if not frappe.db.exists("Role", "Stock User"):
		frappe.rename_doc("Role", "Material User", "Stock User")
	if not frappe.db.exists("Role", "Stock Manager"):
		frappe.rename_doc("Role", "Material Manager", "Stock Manager")
	if not frappe.db.exists("Role", "Item Manager"):
		frappe.rename_doc("Role", "Material Master Manager", "Item Manager")
