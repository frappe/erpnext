from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	custom_fields = {
		'Sales Invoice Item': [
			dict(fieldname='taxable_value', label='Taxable Value',
				fieldtype='Currency', insert_after='base_net_amount', hidden=1, options="Company:company:default_currency",
				print_hide=1)
		]
	}

	create_custom_fields(custom_fields, update=True)
