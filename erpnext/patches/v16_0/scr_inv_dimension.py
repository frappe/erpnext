import frappe

from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions


def execute():
	for dimension in get_inventory_dimensions():
		custom_field = frappe.get_doc(
			"Custom Field",
			{"fieldname": dimension.source_fieldname, "dt": "Subcontracting Receipt Supplied Item"},
		)
		if custom_field:
			custom_field.db_set({"reqd": 0, "mandatory_depends_on": "eval:doc.reference_name"})
