import frappe


def execute():
	if frappe.db.exists("DocType", "Stock Level") or not frappe.db.exists("DocType", "Bin"):
		return

	frappe.rename_doc("DocType", "Bin", "Stock Level", force=True)
	frappe.reload_doc("stock", "doctype", "stock_level")
