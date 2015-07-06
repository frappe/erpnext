import frappe

def execute():
	frappe.reload_doctype("Item")
	for dt in ["manage_variants", "manage_variants_item", "variant_attribute"]:
		frappe.reload_doc("stock", "doctype", dt)

	for d in  frappe.get_list("Item", filters={"has_variants":1}):
		manage_variant = frappe.new_doc("Manage Variants")
		manage_variant.item_code = d.name
		manage_variant.attributes = frappe.db.sql("select item_attribute as attribute, item_attribute_value as attribute_value \
			from `tabItem Variant` where parent = %s", d.name, as_dict=1)
		if manage_variant.attributes:
			if not frappe.get_list("Item", filters={"variant_of": d.name}, limit_page_length=1):
				frappe.db.sql("delete from `tabItem Variant` where parent=%s", d.name)
			else:			
				manage_variant.generate_combinations()
				manage_variant.create_variants()
	frappe.delete_doc("DocType", "Item Variant")