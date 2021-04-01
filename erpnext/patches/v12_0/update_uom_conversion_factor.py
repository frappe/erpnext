from __future__ import unicode_literals
import frappe, json

def execute():
	from erpnext.setup.setup_wizard.operations.install_fixtures import add_uom_data

	frappe.reload_doc("setup", "doctype", "UOM Conversion Factor")
	frappe.reload_doc("setup", "doctype", "UOM")
	frappe.reload_doc("stock", "doctype", "UOM Category")

	add_uom_data()