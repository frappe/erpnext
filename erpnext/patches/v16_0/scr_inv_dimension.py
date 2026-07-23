import frappe

from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions


def execute():
	for dimension in get_inventory_dimensions():
		if frappe.db.exists(
			"Custom Field",
			{
				"fieldname": dimension.source_fieldname,
				"dt": "Subcontracting Receipt Supplied Item",
				"reqd": 1,
			},
		):
			frappe.set_value(
				"Custom Field",
				{
					"fieldname": dimension.source_fieldname,
					"dt": "Subcontracting Receipt Supplied Item",
					"reqd": 1,
				},
				{"reqd": 0, "mandatory_depends_on": "eval:doc.reference_name"},
			)
