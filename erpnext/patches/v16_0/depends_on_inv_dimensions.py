import frappe


def get_inventory_dimensions():
	return frappe.get_all(
		"Inventory Dimension",
		fields=[
			"target_fieldname as fieldname",
			"source_fieldname",
			"reference_document as doctype",
			"reqd",
			"mandatory_depends_on",
		],
		order_by="creation",
		distinct=True,
	)


def get_display_depends_on(doctype):
	if doctype not in [
		"Stock Entry Detail",
		"Sales Invoice Item",
		"Delivery Note Item",
		"Purchase Invoice Item",
		"Purchase Receipt Item",
	]:
		return

	display_depends_on = ""

	if doctype in ["Purchase Invoice Item", "Purchase Receipt Item"]:
		display_depends_on = "eval:parent.is_internal_supplier == 1"
	elif doctype != "Stock Entry Detail":
		display_depends_on = "eval:parent.is_internal_customer == 1"
	elif doctype == "Stock Entry Detail":
		display_depends_on = "eval:doc.t_warehouse"

	return display_depends_on


def execute():
	for dimension in get_inventory_dimensions():
		frappe.set_value(
			"Custom Field",
			{"fieldname": dimension.source_fieldname, "dt": "Stock Entry Detail"},
			"depends_on",
			"eval:doc.s_warehouse",
		)
		frappe.set_value(
			"Custom Field",
			{"fieldname": dimension.source_fieldname, "dt": "Stock Entry Detail", "reqd": 1},
			{"mandatory_depends_on": "eval:doc.s_warehouse", "reqd": 0},
		)
		frappe.set_value(
			"Custom Field",
			{
				"fieldname": f"to_{dimension.fieldname}",
				"dt": "Stock Entry Detail",
				"depends_on": "eval:parent.purpose != 'Material Issue'",
			},
			"depends_on",
			"eval:doc.t_warehouse",
		)
		if display_depends_on := get_display_depends_on(dimension.doctype):
			frappe.set_value(
				"Custom Field",
				{"fieldname": dimension.fieldname, "dt": dimension.doctype},
				"mandatory_depends_on",
				display_depends_on if dimension.reqd else dimension.mandatory_depends_on,
			)
