# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from __future__ import unicode_literals
import frappe

def get_domains():
	'''Written as a function to prevent data mutation effects'''
	return {
		'Manufacturing': {
			'desktop_icons': ['Item', 'BOM', 'Customer', 'Supplier', 'Sales Order',
				'Production Order',  'Stock Entry', 'Purchase Order', 'Task', 'Buying', 'Selling',
				 'Accounts', 'HR', 'ToDo'],
			'properties': [
				{'doctype': 'Item', 'fieldname': 'manufacturing', 'property': 'collapsible_depends_on', 'value': 'is_stock_item'},
			],
			'set_value': [
				['Stock Settings', None, 'show_barcode_field', 1]
			]
		},

		'Retail': {
			'desktop_icons': ['POS', 'Item', 'Customer', 'Sales Invoice',  'Purchase Order', 'Warranty Claim',
			'Accounts', 'Buying', 'ToDo'],
			'remove_roles': ['Manufacturing User', 'Manufacturing Manager'],
			'properties': [
				{'doctype': 'Item', 'fieldname': 'manufacturing', 'property': 'hidden', 'value': 1},
				{'doctype': 'Customer', 'fieldname': 'credit_limit_section', 'property': 'hidden', 'value': 1},
			],
			'set_value': [
				['Stock Settings', None, 'show_barcode_field', 1]
			]
		},

		'Distribution': {
			'desktop_icons': ['Item', 'Customer', 'Supplier', 'Lead', 'Sales Order',
				 'Sales Invoice', 'CRM', 'Selling', 'Buying', 'Stock', 'Accounts', 'HR', 'ToDo'],
			'remove_roles': ['Manufacturing User', 'Manufacturing Manager'],
			'properties': [
				{'doctype': 'Item', 'fieldname': 'manufacturing', 'property': 'hidden', 'value': 1},
			],
			'set_value': [
				['Stock Settings', None, 'show_barcode_field', 1]
			]
		},

		'Services': {
			'desktop_icons': ['Project', 'Timesheet', 'Customer', 'Sales Order', 'Sales Invoice', 'Lead', 'Opportunity',
				'Expense Claim', 'Employee', 'HR', 'ToDo'],
			'remove_roles': ['Manufacturing User', 'Manufacturing Manager'],
			'properties': [
				{'doctype': 'Item', 'fieldname': 'is_stock_item', 'property': 'default', 'value': 0},
			],
			'set_value': [
				['Stock Settings', None, 'show_barcode_field', 0]
			]
		}
	}

def setup_domain(domain):
	domains = get_domains()

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

	if data.set_value:
		for args in data.set_value:
			doc = frappe.get_doc(args[0], args[1] or args[0])
			doc.set(args[2], args[3])
			doc.save()

	frappe.clear_cache()

def reset():
	from frappe.desk.page.setup_wizard.setup_wizard import add_all_roles_to
	add_all_roles_to('Administrator')

	frappe.db.sql('delete from `tabProperty Setter`')
