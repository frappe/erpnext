import frappe
from erpnext.stock.stock_balance import update_bin_qty, get_indented_qty


def execute():
	frappe.reload_doc("stock", "doctype", "stock_settings")
	frappe.reload_doc("stock", "doctype", "material_request")
	frappe.reload_doc("stock", "doctype", "material_request_item")

	frappe.db.set_value("Stock Settings", None, "no_partial_indent", 1, update_modified=False)

	bin_details = frappe.db.sql("""
		SELECT item_code, warehouse
		FROM `tabBin`
	""", as_dict=1)

	for entry in bin_details:
		update_bin_qty(entry.get("item_code"), entry.get("warehouse"), {
			"indented_qty": get_indented_qty(entry.get("item_code"), entry.get("warehouse"))
		})

	mreqs = frappe.db.sql_list("""
		select name
		from `tabMaterial Request`
		where docstatus = 1
	""")

	for name in mreqs:
		doc = frappe.get_doc("Material Request", name)
		doc.set_completion_status(update=True, update_modified=False)
		doc.set_status(update=True, update_modified=False)
		doc.clear_cache()
