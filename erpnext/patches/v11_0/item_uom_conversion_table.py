import frappe
from frappe.utils import flt

def execute():
	frappe.reload_doc("stock", "doctype", "item")
	frappe.reload_doc("stock", "doctype", "uom_conversion_detail")
	frappe.reload_doc("stock", "doctype", "uom_conversion_graph")

	names = frappe.get_all("Item")
	for name in names:
		doc = frappe.get_doc("Item", name)
		for d in doc.uoms:
			if d.uom == doc.stock_uom:
				continue
			conv = doc.append("uom_conversion_graph", {
				"from_qty": 1.0,
				"from_uom": doc.stock_uom,
				"to_qty": flt(1 / d.conversion_factor, doc.precision("to_qty", "uom_conversion_graph")),
				"to_uom": d.uom
			})
			conv.db_insert()