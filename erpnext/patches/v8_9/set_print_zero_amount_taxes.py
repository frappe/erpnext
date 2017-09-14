from __future__ import unicode_literals
import frappe

from erpnext.setup.install import create_print_zero_amount_taxes_custom_field

def execute():
	create_print_zero_amount_taxes_custom_field()