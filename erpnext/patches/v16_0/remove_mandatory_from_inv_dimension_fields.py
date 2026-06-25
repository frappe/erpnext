import frappe


def execute():
	"""Mandatory inventory dimensions are now enforced on the server side
	(StockController.validate_inventory_dimension_mandatory) instead of via field-level
	`reqd`/`mandatory_depends_on`. Clear those properties from the related custom fields."""
	dimensions = frappe.get_all(
		"Inventory Dimension",
		fields=["source_fieldname", "target_fieldname"],
	)

	fieldnames = set()
	for dimension in dimensions:
		for fieldname in [dimension.source_fieldname, dimension.target_fieldname]:
			if not fieldname:
				continue

			fieldnames.update(
				[
					fieldname,
					f"to_{fieldname}",
					f"from_{fieldname}",
					f"rejected_{fieldname}",
				]
			)

	if not fieldnames:
		return

	custom_fields = frappe.get_all(
		"Custom Field",
		filters={
			"fieldname": ("in", list(fieldnames)),
			"fieldtype": "Link",
		},
		or_filters={"reqd": 1, "mandatory_depends_on": ("is", "set")},
		pluck="name",
	)

	for name in custom_fields:
		frappe.db.set_value(
			"Custom Field",
			name,
			{"reqd": 0, "mandatory_depends_on": ""},
			update_modified=False,
		)
