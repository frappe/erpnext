from __future__ import unicode_literals

import frappe

from erpnext.regional.india.setup import make_custom_fields


def execute():

	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	make_custom_fields()

	frappe.reload_doctype('Tax Category')
	frappe.reload_doctype('Sales Taxes and Charges Template')
	frappe.reload_doctype('Purchase Taxes and Charges Template')

	# Create tax category with inter state field checked
	tax_category =  frappe.db.get_value('Tax Category', {'name': 'OUT OF STATE'}, 'name')

	if not tax_category:
		inter_state_category = frappe.get_doc({
			'doctype': 'Tax Category',
			'title': 'OUT OF STATE',
			'is_inter_state': 1
		}).insert()

		tax_category = inter_state_category.name

	for doctype in ('Sales Taxes and Charges Template', 'Purchase Taxes and Charges Template'):
		if not frappe.get_meta(doctype).has_field('is_inter_state'): continue

		template = frappe.db.get_value(doctype, {'is_inter_state': 1, 'disabled': 0}, ['name'])
		if template:
			frappe.db.set_value(doctype, template, 'tax_category', tax_category)

		frappe.db.sql("""
			DELETE FROM `tabCustom Field`
			WHERE fieldname = 'is_inter_state'
			AND dt IN ('Sales Taxes and Charges Template', 'Purchase Taxes and Charges Template')
		""")
