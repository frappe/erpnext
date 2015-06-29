import frappe

def execute():
	frappe.reload_doctype("Item")
	for d in  frappe.get_list("Item", filters={"has_variants":1}):
		manage_variant = frappe.new_doc("Manage Variants")
		manage_variant.item = d.name
		manage_variant.attributes = frappe.db.sql("select item_attribute as attribute, item_attribute_value as attribute_value \
			from `tabItem Variant` where parent = %s", d.name, as_dict=1)
		manage_variant.generate_combinations()
		manage_variant.create_variants()