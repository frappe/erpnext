import frappe


def execute():
	settings = frappe.get_doc("Item Variant Settings")
	settings.remove_invalid_fields_for_copy_fields_in_variants()
