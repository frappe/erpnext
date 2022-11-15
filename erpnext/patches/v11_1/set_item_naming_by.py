import frappe, os
from frappe import _

def execute():
	frappe.reload_doc('stock', 'doctype', 'item')
	frappe.reload_doc('stock', 'doctype', 'stock_settings')

	stock_settings = frappe.get_single("Stock Settings")
	stock_settings.item_naming_by = "Item Name"
	stock_settings.save()

	frappe.make_property_setter({'doctype': 'Item', 'fieldname': 'item_code', 'property': 'hidden',
		'value': 0})

	frappe.make_property_setter({'doctype': 'Item', 'fieldname': 'item_name', 'property': 'hidden',
		'value': 0})
	frappe.make_property_setter({'doctype': 'Item', 'fieldname': 'item_name', 'property': 'read_only',
		'value': 0})

	frappe.make_property_setter({'doctype': 'Item', 'fieldname': 'naming_series', 'property': 'hidden',
		'value': 0})

	for name in frappe.get_all("Item"):
		name = name.name
		item = frappe.get_doc("Item", name)
		if item.clean_name(item.name) == item.clean_name(item.item_name):
			item.db_set('item_naming_by', 'Item Name')
		else:
			item.db_set('item_naming_by', 'Item Code')

		if item.name == "Service":
			item.db_set('show_item_code', 'No')
