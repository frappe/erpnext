import frappe
from frappe.model.rename_doc import rename_doc
from frappe.model.utils.rename_field import rename_field

def execute():
	if frappe.db.table_exists("Supplier Type") and not frappe.db.table_exists("Supplier Group"):
		rename_doc("DocType", "Supplier Type", "Supplier Group", force=True)
		frappe.reload_doc('setup', 'doctype', 'supplier_group')
		frappe.reload_doc("accounts", "doctype", "pricing_rule")
		frappe.reload_doc("accounts", "doctype", "tax_rule")
		frappe.reload_doc("buying", "doctype", "buying_settings")
		frappe.reload_doc("buying", "doctype", "supplier")
		rename_field("Supplier Group", "supplier_type", "supplier_group_name")
		rename_field("Supplier", "supplier_type", "supplier_group")
		rename_field("Buying Settings", "supplier_type", "supplier_group")
		rename_field("Pricing Rule", "supplier_type", "supplier_group")
		rename_field("Tax Rule", "supplier_type", "supplier_group")
