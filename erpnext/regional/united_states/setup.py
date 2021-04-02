# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup(company=None, patch=True):
	make_custom_fields()
	add_print_formats()
	update_address_template()


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


def update_address_template():
	html = """{{ address_line1 }}<br>
		{% if address_line2 %}{{ address_line2 }}<br>{% endif -%}
		{{ city }}, {% if state %}{{ state }}{% endif -%}{% if pincode %} {{ pincode }}<br>{% endif -%}
		{% if country != "United States" %}{{ country|upper }}{% endif -%}
		"""

	address_template = frappe.db.get_value('Address Template', 'United States')
	if address_template:
		frappe.db.set_value('Address Template', 'United States', 'template', html)
	else:
		frappe.get_doc(dict(doctype='Address Template', country='United States', template=html)).insert()
