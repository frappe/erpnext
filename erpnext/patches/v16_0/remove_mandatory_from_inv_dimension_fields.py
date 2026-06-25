import frappe

from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_documents


def execute():
	"""Mandatory inventory dimensions are now enforced on the server side
	(StockController.validate_inventory_dimension_mandatory) instead of via field-level
	`reqd`/`mandatory_depends_on`. Clear those properties from the related custom fields."""
	dimensions = frappe.get_all(
		"Inventory Dimension",
		fields=[
			"source_fieldname",
			"reference_document",
			"document_type",
			"apply_to_all_doctypes",
		],
	)

	for dimension in dimensions:
		if not dimension.source_fieldname or not dimension.reference_document:
			continue

		# Scope to the exact doctypes where this dimension generated fields so unrelated
		# mandatory custom fields (same name/target on a different doctype) are never touched.
		if dimension.apply_to_all_doctypes:
			doctypes = [d[0] for d in get_inventory_documents()]
		elif dimension.document_type:
			doctypes = [dimension.document_type]
		else:
			continue

		fieldname = dimension.source_fieldname
		fieldnames = [fieldname, f"to_{fieldname}", f"from_{fieldname}", f"rejected_{fieldname}"]

		custom_fields = frappe.get_all(
			"Custom Field",
			filters={
				"dt": ("in", doctypes),
				"fieldname": ("in", fieldnames),
				"fieldtype": "Link",
				"options": dimension.reference_document,
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
