from __future__ import unicode_literals
import frappe

from erpnext.setup.install import create_print_zero_amount_taxes_custom_field

def execute():
	frappe.reload_doc("printing", "doctype", "print_style")
	create_print_zero_amount_taxes_custom_field()