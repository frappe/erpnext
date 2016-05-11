# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from __future__ import unicode_literals
import frappe

domains = {
	'Manufacturing': {
		'desktop_icons': ['Item', 'BOM', 'Customer', 'Supplier', 'Sales Order',
			'Production Order', 'Stock Entry', 'Buying', 'Selling', 'Accounts']
	},
	'Retail': {
		'remove_roles': ['Manufacturing User', 'Manufacturing Manager', 'Maintenance User'],
		'desktop_icons': ['POS', 'Item', 'Customer', 'Sales Invoice', 'Accounts']
	},
	'Distribution': {
		'remove_roles': ['Manufacturing User', 'Manufacturing Manager', 'Maintenance User'],
	},
	'Services': {
		'desktop_icons': ['Project', 'Time Log', 'Customer', 'Sales Invoice', 'Lead', 'Opportunity',
			'Expense Claim', 'Employee'],
		'remove_roles': ['Manufacturing User', 'Manufacturing Manager', 'Maintenance User'],
		'properties': [
			{'doctype': 'Item', 'fieldname': 'is_stock_item', 'property': 'default', 'value': 0},
			{'fieldname': 'barcode', 'property': 'hidden', 'value': 1}
		]
	}
}

def setup_domain(domain):
	if not domain in domains:
		return

	from frappe.desk.doctype.desktop_icon.desktop_icon import set_desktop_icons
	data = frappe._dict(domains[domain])

	if data.remove_roles:
		for role in data.remove_roles:
			frappe.db.sql('delete from tabUserRole where role=%s', role)

	if data.desktop_icons:
		set_desktop_icons(data.desktop_icons)

	if data.properties:
		for args in data.properties:
			frappe.make_property_setter(args)

	frappe.clear_cache()

def reset():
	from frappe.desk.page.setup_wizard.setup_wizard import add_all_roles_to
	add_all_roles_to('Administrator')

	frappe.db.sql('delete from `tabProperty Setter`')