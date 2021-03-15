from __future__ import unicode_literals
import frappe


def execute():
	frappe.reload_doctype("Work Order Item")

	frappe.db.sql("""
		update `tabWork Order Item` wo_item
		inner join `tabItem` i on i.name = wo_item.item_code
		set wo_item.stock_uom = i.stock_uom, wo_item.stock_required_qty = wo_item.required_qty * wo_item.conversion_factor
	""")
