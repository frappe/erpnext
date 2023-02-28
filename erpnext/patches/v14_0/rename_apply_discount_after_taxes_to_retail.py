import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	rename_map = {
		"Quotation Item": [("apply_discount_after_taxes", "apply_taxes_on_retail")],
		"Sales Order Item": [("apply_discount_after_taxes", "apply_taxes_on_retail")],
		"Delivery Note Item": [("apply_discount_after_taxes", "apply_taxes_on_retail")],
		"Sales Invoice Item": [("apply_discount_after_taxes", "apply_taxes_on_retail")],
		"Supplier Quotation Item": [("apply_discount_after_taxes", "apply_taxes_on_retail")],
		"Purchase Order Item": [("apply_discount_after_taxes", "apply_taxes_on_retail")],
		"Purchase Receipt Item": [("apply_discount_after_taxes", "apply_taxes_on_retail")],
		"Purchase Invoice Item": [("apply_discount_after_taxes", "apply_taxes_on_retail")],

		"Company": [
			("buying_apply_discount_after_taxes", "buying_apply_taxes_on_retail"),
			("selling_apply_discount_after_taxes", "selling_apply_taxes_on_retail")
		],

		"Item Default Rule": [
			("buying_apply_discount_after_taxes", "buying_apply_taxes_on_retail"),
			("selling_apply_discount_after_taxes", "selling_apply_taxes_on_retail")
		],
	}

	for dt, fields in rename_map.items():
		frappe.reload_doctype(dt, force=1)

		for old_field, new_field in fields:
			if frappe.db.has_column(dt, old_field):
				print("{0}: Renaming Field {1} -> {2}".format(dt, old_field, new_field))
				rename_field(dt, old_field, new_field)
			else:
				print("{0}: Old Field {1} not found".format(dt, old_field, new_field))
