# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def setup(company=None, patch=True):
	make_custom_fields()
	add_print_formats()

def make_custom_fields():
	custom_fields = {
		'Supplier': [
			dict(fieldname='irs_1099', fieldtype='Check', insert_after='tax_id',
				label='Is IRS 1099 reporting required for supplier?')
		]
	}
	create_custom_fields(custom_fields)

def add_print_formats():
	frappe.reload_doc("regional", "print_format", "irs_1099_form")
	frappe.db.sql(""" update `tabPrint Format` set disabled = 0 where
		name in('IRS 1099 Form') """)
