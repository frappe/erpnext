from __future__ import unicode_literals
import frappe


def execute():
	frappe.reload_doctype("BOM Explosion Item")
	frappe.reload_doctype("Work Order Item")

	frappe.db.sql("""
		update `tabBOM Explosion Item`
		set
			qty = stock_qty,
			uom = stock_uom,
			stock_qty_consumed_per_unit = qty_consumed_per_unit
	""")

	frappe.db.sql("""
		update `tabWork Order Item` wo_item
		inner join `tabItem` i on i.name = wo_item.item_code
		set wo_item.uom = i.stock_uom
	""")
