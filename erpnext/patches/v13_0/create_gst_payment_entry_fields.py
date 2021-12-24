# Copyright (c) 2021, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	frappe.reload_doc('accounts', 'doctype', 'advance_taxes_and_charges')
	frappe.reload_doc('accounts', 'doctype', 'payment_entry')

	custom_fields = {
		'Payment Entry': [
			dict(fieldname='gst_section', label='GST Details', fieldtype='Section Break', insert_after='deductions',
				print_hide=1, collapsible=1),
			dict(fieldname='company_address', label='Company Address', fieldtype='Link', insert_after='gst_section',
				print_hide=1, options='Address'),
			dict(fieldname='company_gstin', label='Company GSTIN',
				fieldtype='Data', insert_after='company_address',
				fetch_from='company_address.gstin', print_hide=1, read_only=1),
			dict(fieldname='place_of_supply', label='Place of Supply',
				fieldtype='Data', insert_after='company_gstin',
				print_hide=1, read_only=1),
			dict(fieldname='customer_address', label='Customer Address', fieldtype='Link', insert_after='place_of_supply',
				print_hide=1, options='Address', depends_on = 'eval:doc.party_type == "Customer"'),
			dict(fieldname='customer_gstin', label='Customer GSTIN',
				fieldtype='Data', insert_after='customer_address',
				fetch_from='customer_address.gstin', print_hide=1, read_only=1)
		]
	}

	create_custom_fields(custom_fields, update=True)