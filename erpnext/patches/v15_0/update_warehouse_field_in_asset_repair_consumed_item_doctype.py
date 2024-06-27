import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import IfNull


def execute():
	if frappe.db.has_column("Asset Repair", "warehouse"):
		ar_item = DocType("Asset Repair Consumed Item")
		ar = DocType("Asset Repair")
		(
			frappe.qb.update(ar_item)
			.join(ar)
			.on(ar.name == ar_item.parent)
			.set(ar_item.warehouse, ar.warehouse)
			.where(IfNull(ar.warehouse, "") != "")
		).run()
