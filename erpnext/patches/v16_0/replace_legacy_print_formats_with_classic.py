import frappe
from frappe.model.rename_doc import get_link_fields, update_link_field_values

LEGACY_PRINT_FORMATS = {
	"Sales Order": ("Sales Order Standard", "Sales Order with Item Image"),
	"Sales Invoice": ("Sales Invoice Standard", "Sales Invoice with Item Image"),
	"Delivery Note": ("Delivery Note Standard", "Delivery Note with Item Image"),
	"Purchase Order": ("Purchase Order Standard", "Purchase Order with Item Image"),
	"Purchase Invoice": ("Purchase Invoice Standard", "Purchase Invoice with Item Image"),
	"POS Invoice": ("POS Invoice Standard", "POS Invoice with Item Image"),
	"Quotation": ("Quotation Standard", "Quotation with Item Image"),
	"Request for Quotation": ("Request for Quotation with Item Image",),
}


def execute():
	link_fields = get_link_fields("Print Format")

	for doctype, legacy_formats in LEGACY_PRINT_FORMATS.items():
		classic = f"{doctype} Classic"
		if not frappe.db.exists("Print Format", classic):
			continue

		for legacy in legacy_formats:
			if frappe.db.exists("Print Format", {"name": legacy, "standard": "Yes"}):
				replace_print_format(doctype, legacy, classic, link_fields)

		frappe.clear_cache(doctype=doctype)


def replace_print_format(doctype: str, legacy: str, classic: str, link_fields: list[dict]):
	update_link_field_values(link_fields, legacy, classic, "Print Format")
	frappe.db.set_value(
		"Property Setter",
		{"doc_type": doctype, "property": "default_print_format", "value": legacy},
		"value",
		classic,
		update_modified=False,
	)
	frappe.db.set_value(
		"Payment Request", {"print_format": legacy}, "print_format", classic, update_modified=False
	)
	frappe.delete_doc("Print Format", legacy, ignore_missing=True, force=True)
