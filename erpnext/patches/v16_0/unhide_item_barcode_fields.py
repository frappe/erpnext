import frappe

from erpnext.stock.doctype.stock_settings.stock_settings import get_transaction_barcode_fields


def execute():
	transaction_fields = set(get_transaction_barcode_fields())

	for setter in frappe.get_all(
		"Property Setter",
		filters={
			"field_name": ("in", ["barcode", "barcodes", "scan_barcode"]),
			"property": "hidden",
			"is_system_generated": 1,
		},
		fields=["name", "doc_type", "field_name"],
	):
		if (setter.doc_type, setter.field_name) not in transaction_fields:
			frappe.delete_doc("Property Setter", setter.name)
