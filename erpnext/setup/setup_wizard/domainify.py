# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from __future__ import unicode_literals
import frappe

def get_domain(domain):
	'''Written as a function to prevent data mutation effects'''
	data = {
		'Manufacturing': {
			'desktop_icons': ['Item', 'BOM', 'Customer', 'Supplier', 'Sales Order',
				'Production Order',  'Stock Entry', 'Purchase Order', 'Task', 'Buying', 'Selling',
				 'Accounts', 'HR', 'ToDo'],
			'remove_roles': ['Academics User'],
			'properties': [
				{'doctype': 'Item', 'fieldname': 'manufacturing', 'property': 'collapsible_depends_on', 'value': 'is_stock_item'},
			],
			'set_value': [
				['Stock Settings', None, 'show_barcode_field', 1]
			],
			'remove_sidebar_items': ['/announcement', '/course', '/examination', '/fees']
		},

		'Retail': {
			'desktop_icons': ['POS', 'Item', 'Customer', 'Sales Invoice',  'Purchase Order', 'Warranty Claim',
			'Accounts', 'Buying', 'ToDo'],
			'remove_roles': ['Manufacturing User', 'Manufacturing Manager', 'Academics User'],
			'properties': [
				{'doctype': 'Item', 'fieldname': 'manufacturing', 'property': 'hidden', 'value': 1},
				{'doctype': 'Customer', 'fieldname': 'credit_limit_section', 'property': 'hidden', 'value': 1},
			],
			'set_value': [
				['Stock Settings', None, 'show_barcode_field', 1]
			],
			'remove_sidebar_items': ['/announcement', '/course', '/examination', '/fees']
		},

		'Distribution': {
			'desktop_icons': ['Item', 'Customer', 'Supplier', 'Lead', 'Sales Order',
				 'Sales Invoice', 'CRM', 'Selling', 'Buying', 'Stock', 'Accounts', 'HR', 'ToDo'],
			'remove_roles': ['Manufacturing User', 'Manufacturing Manager', 'Academics User'],
			'properties': [
				{'doctype': 'Item', 'fieldname': 'manufacturing', 'property': 'hidden', 'value': 1},
			],
			'set_value': [
				['Stock Settings', None, 'show_barcode_field', 1]
			],
			'remove_sidebar_items': ['/announcement', '/course', '/examination', '/fees']
		},

		'Services': {
			'desktop_icons': ['Project', 'Timesheet', 'Customer', 'Sales Order', 'Sales Invoice', 'Lead', 'Opportunity',
				'Expense Claim', 'Employee', 'HR', 'ToDo'],
			'remove_roles': ['Manufacturing User', 'Manufacturing Manager', 'Academics User'],
			'properties': [
				{'doctype': 'Item', 'fieldname': 'is_stock_item', 'property': 'default', 'value': 0},
			],
			'set_value': [
				['Stock Settings', None, 'show_barcode_field', 0]
			],
			'remove_sidebar_items': ['/announcement', '/course', '/examination', '/fees']
		},
		'Education': {
			'desktop_icons': ['Student', 'Program', 'Course', 'Student Group', 'Instructor',
				'Fees',  'ToDo', 'Schools'],
			'allow_roles': ['Academics User', 'Accounts User', 'Accounts Manager', 'Website Manager'],
			'allow_sidebar_items': ['/announcement', '/course', '/examination', '/fees']
		},
	}
	if not domain in data:
		raise 'Invalid Domain {0}'.format(domain)
	return frappe._dict(data[domain])

def setup_domain(domain):
	'''Setup roles, desktop icons, properties, values, portal sidebar menu based on domain'''
	data = get_domain(domain)
	setup_roles(data)
	setup_desktop_icons(data)
	setup_properties(data)
	set_values(data)
	setup_sidebar_items(data)
	frappe.clear_cache()

def setup_desktop_icons(data):
	'''set desktop icons form `data.desktop_icons`'''
	from frappe.desk.doctype.desktop_icon.desktop_icon import set_desktop_icons
	if data.desktop_icons:
		set_desktop_icons(data.desktop_icons)

def setup_properties(data):
	if data.properties:
		for args in data.properties:
			frappe.make_property_setter(args)

def setup_roles(data):
	'''Add, remove roles from `data.allow_roles` or `data.remove_roles`'''
	def remove_role(role):
		frappe.db.sql('delete from tabUserRole where role=%s', role)

	if data.remove_roles:
		for role in data.remove_roles:
			remove_role(role)

	if data.allow_roles:
		# remove all roles other than allowed roles
		data.allow_roles += ['Administrator', 'Guest', 'System Manager']
		for role in frappe.get_all('Role'):
			if not (role.name in data.allow_roles):
				remove_role(role.name)

def set_values(data):
	'''set values based on `data.set_value`'''
	if data.set_value:
		for args in data.set_value:
			doc = frappe.get_doc(args[0], args[1] or args[0])
			doc.set(args[2], args[3])
			doc.save()

def setup_sidebar_items(data):
	'''Enable / disable sidebar items'''
	if data.allow_sidebar_items:
		# disable all
		frappe.db.sql('update `tabPortal Menu Item` set enabled=0')

		# enable
		frappe.db.sql('''update `tabPortal Menu Item` set enabled=1
			where route in ({0})'''.format(', '.join(['"{0}"'.format(d) for d in data.allow_sidebar_items])))

	if data.remove_sidebar_items:
		# disable all
		frappe.db.sql('update `tabPortal Menu Item` set enabled=1')

		# enable
		frappe.db.sql('''update `tabPortal Menu Item` set enabled=0
			where route in ({0})'''.format(', '.join(['"{0}"'.format(d) for d in data.remove_sidebar_items])))


def reset():
	from frappe.desk.page.setup_wizard.setup_wizard import add_all_roles_to
	add_all_roles_to('Administrator')

	frappe.db.sql('delete from `tabProperty Setter`')
