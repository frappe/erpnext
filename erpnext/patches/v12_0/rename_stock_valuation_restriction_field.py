import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc('stock', 'doctype', 'stock_settings')
	rename_field("Stock Settings", "restrict_amounts_in_report_to_role", "restrict_stock_valuation_to_role")
	frappe.get_doc("Stock Settings").update_global_defaults()
