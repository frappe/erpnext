import frappe

def execute():
	frappe.rename_doc("Role", "Material User", "Stock User",
		merge=frappe.db.exists("Role", "Stock User"))
	frappe.rename_doc("Role", "Material Manager", "Stock Manager",
		merge=frappe.db.exists("Role", "Stock User"))
	frappe.rename_doc("Role", "Material Master Manager", "Item Manager",
		merge=frappe.db.exists("Role", "Stock User"))
