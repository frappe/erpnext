import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("stock", "doctype", "item")
	frappe.reload_doc("stock", "doctype", "stock_settings")
	frappe.reload_doc("accounts", "doctype", "accounts_settings")

	rename_field("Stock Settings", "tolerance", "over_delivery_receipt_allowance")
	rename_field("Item", "tolerance", "over_delivery_receipt_allowance")

	qty_allowance = frappe.db.get_single_value("Stock Settings", "over_delivery_receipt_allowance")
	frappe.db.set_value("Accounts Settings", None, "over_delivery_receipt_allowance", qty_allowance)

	frappe.db.sql("update tabItem set over_billing_allowance=over_delivery_receipt_allowance")
