import frappe

def execute():
	frappe.reload_doc('stock', 'doctype', 'item_variant_settings')
	frappe.reload_doc('stock', 'doctype', 'variant_field')

	doc = frappe.get_doc('Item Variant Settings')
	doc.append('fields', {
		'field_name': "has_serial_no"
	})
	doc.save()