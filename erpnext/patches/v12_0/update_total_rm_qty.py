from __future__ import unicode_literals
import frappe


def execute():
	frappe.reload_doctype("BOM")
	frappe.reload_doctype("Work Order")
	frappe.reload_doctype("Material Request")

	bom = dict(frappe.db.sql("""
		select parent, sum(qty)
		from `tabBOM Item`
		group by parent
	"""))

	mreq = dict(frappe.db.sql("""
		select parent, sum(qty)
		from `tabMaterial Request Item`
		group by parent
	"""))

	wo = dict(frappe.db.sql("""
		select parent, sum(required_qty)
		from `tabWork Order Item`
		group by parent
	"""))

	for parent, qty in bom.items():
		frappe.db.set_value('BOM', parent, 'total_raw_material_qty', qty, update_modified=False)

	for parent, qty in mreq.items():
		frappe.db.set_value('Material Request', parent, 'total_qty', qty, update_modified=False)

	for parent, qty in wo.items():
		frappe.db.set_value('Work Order', parent, 'total_raw_material_qty', qty, update_modified=False)
