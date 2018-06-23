import frappe

def execute():
	bins = frappe.db.sql("select name from `tabBin` where reserved_qty_for_production > 0")
	for d in bins:
		bin_doc = frappe.get_doc("Bin", d[0])
		bin_doc.update_reserved_qty_for_production()