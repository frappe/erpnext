import frappe

def execute():
	if frappe.db.table_exists("tabCustomer Issue"):
		frappe.rename_doc("DocType", "Customer Issue", "Warranty Claim")
