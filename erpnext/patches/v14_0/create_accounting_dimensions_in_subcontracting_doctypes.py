import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


def execute():
	accounting_dimensions = frappe.db.get_all(
		"Accounting Dimension", fields=["fieldname", "label", "document_type", "disabled"]
	)

	if not accounting_dimensions:
		return

	count = 1
	for d in accounting_dimensions:
		if count % 2 == 0:
			insert_after_field = "dimension_col_break"
		else:
			insert_after_field = "accounting_dimensions_section"

		for doctype in [
			"Subcontracting Order",
			"Subcontracting Order Item",
			"Subcontracting Receipt",
			"Subcontracting Receipt Item",
		]:
			field = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": d.fieldname})

			if field:
				continue

			df = {
				"fieldname": d.fieldname,
				"label": d.label,
				"fieldtype": "Link",
				"options": d.document_type,
				"insert_after": insert_after_field,
			}

			try:
				create_custom_field(doctype, df, ignore_validate=True)
				frappe.clear_cache(doctype=doctype)
			except Exception:
				pass

		count += 1
