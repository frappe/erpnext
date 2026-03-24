import frappe


def execute():
	"""Remove has_variants and attribute fields from item variant settings."""
	frappe.reload_doc("stock", "doctype", "Item Variant Settings")

	frappe.db.delete("Variant Field", {"field_name": ["in", ["attributes", "has_variants"]]})
