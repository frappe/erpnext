import frappe

def execute():
	frappe.reload_doctype("Item")
	from erpnext.stock.doctype.bin.bin import update_item_projected_qty
	for item in frappe.get_all("Item", filters={"is_stock_item": 1}):
		update_item_projected_qty(item.name)