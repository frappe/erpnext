import frappe

from erpnext.setup.install import create_compact_item_print_custom_field
from frappe.utils import cint

def execute():
	frappe.reload_doctype('Stock Settings')
	stock_settings = frappe.get_doc('Stock Settings', 'Stock Settings')
	stock_settings.show_barcode_field = cint(frappe.db.get_value("Features Setup", None, "fs_item_barcode"))
	if not frappe.db.exists("UOM", stock_settings.stock_uom):
		stock_settings.stock_uom = None
	stock_settings.save()

	create_compact_item_print_custom_field()

	compact_item_print = frappe.db.get_value("Features Setup", None, "compact_item_print")
	frappe.db.set_value("Print Settings", None, "compact_item_print", compact_item_print)

	# remove defaults
	frappe.db.sql("""delete from tabDefaultValue where defkey in ('fs_item_serial_nos',
		'fs_item_batch_nos', 'fs_brands', 'fs_item_barcode',
		'fs_item_advanced', 'fs_packing_details', 'fs_item_group_in_details',
		'fs_exports', 'fs_imports', 'fs_discounts', 'fs_purchase_discounts',
		'fs_after_sales_installations', 'fs_projects', 'fs_sales_extras',
		'fs_recurring_invoice', 'fs_pos', 'fs_manufacturing', 'fs_quality',
		'fs_page_break', 'fs_more_info', 'fs_pos_view', 'compact_item_print')""")

	frappe.delete_doc('DocType', 'Features Setup')
