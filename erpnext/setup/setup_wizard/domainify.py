# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def get_domain(domain):
	'''Written as a function to prevent data mutation effects'''
	data = {
		'Manufacturing': {
			'desktop_icons': ['Item', 'BOM', 'Customer', 'Supplier', 'Sales Order',
				'Production Order',  'Stock Entry', 'Purchase Order', 'Task', 'Buying', 'Selling',
				 'Accounts', 'HR', 'ToDo'],
			'remove_roles': ['Academics User', 'Instructor'],
			'properties': [
				{'doctype': 'Item', 'fieldname': 'manufacturing', 'property': 'collapsible_depends_on', 'value': 'is_stock_item'},
			],
			'set_value': [
				['Stock Settings', None, 'show_barcode_field', 1]
			],
			'default_portal_role': 'Customer'
		},

		'Retail': {
			'desktop_icons': ['POS', 'Item', 'Customer', 'Sales Invoice',  'Purchase Order',
			'Warranty Claim', 'Accounts', 'Task', 'Buying', 'ToDo'],
			'remove_roles': ['Manufacturing User', 'Manufacturing Manager', 'Academics User', 'Instructor'],
			'properties': [
				{'doctype': 'Item', 'fieldname': 'manufacturing', 'property': 'hidden', 'value': 1},
				{'doctype': 'Customer', 'fieldname': 'credit_limit_section', 'property': 'hidden', 'value': 1},
			],
			'set_value': [
				['Stock Settings', None, 'show_barcode_field', 1]
			],
			'default_portal_role': 'Customer'
		},

		'Distribution': {
			'desktop_icons': ['Item', 'Customer', 'Supplier', 'Lead', 'Sales Order', 'Task',
				 'Sales Invoice', 'CRM', 'Selling', 'Buying', 'Stock', 'Accounts', 'HR', 'ToDo'],
			'remove_roles': ['Manufacturing User', 'Manufacturing Manager', 'Academics User', 'Instructor'],
			'set_value': [
				['Stock Settings', None, 'show_barcode_field', 1]
			],
			'default_portal_role': 'Customer'
		},

		'Services': {
			'desktop_icons': ['Project', 'Timesheet', 'Customer', 'Sales Order', 'Sales Invoice',
				'Lead', 'Opportunity', 'Task', 'Expense Claim', 'Employee', 'HR', 'ToDo'],
			'remove_roles': ['Manufacturing User', 'Manufacturing Manager', 'Academics User', 'Instructor'],
			'properties': [
				{'doctype': 'Item', 'fieldname': 'is_stock_item', 'property': 'default', 'value': 0},
			],
			'set_value': [
				['Stock Settings', None, 'show_barcode_field', 0]
			],
			'default_portal_role': 'Customer'
		},
		'Education': {
			'desktop_icons': ['Student', 'Program', 'Course', 'Student Group', 'Instructor',
				'Fees',  'Task', 'ToDo', 'Schools'],
			'allow_roles': ['Academics User', 'Accounts User', 'Accounts Manager', 'Item Manager',
				'Website Manager', 'HR User', 'HR Manager', 'Purchase User', 'Purchase Manager',
				'Student', 'Projects User', 'Instructor'],
			'default_portal_role': 'Student'
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
	update_module_def_restrict_to_domain()

	if data.get('default_portal_role'):
		frappe.db.set_value('Portal Settings', None, 'default_role', data.get('default_portal_role'))

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
		frappe.db.sql('delete from `tabHas Role` where role=%s', role)
		frappe.set_value('Role', role, 'disabled', 1)

	if data.remove_roles:
		for role in data.remove_roles:
			remove_role(role)

	if data.allow_roles:
		# remove all roles other than allowed roles
		active_domains = frappe.get_active_domains()
		data.allow_roles += ['Administrator', 'Guest', 'System Manager', 'All']
		for role in frappe.get_all('Role', filters = {"restrict_to_domain": ("not in", active_domains)}):
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

def update_module_def_restrict_to_domain():
	""" set the restrict to domain for the module def """

	module_def_restrict_to_domain_mapper = {
		"Schools": 'Education'
	}

	lang = frappe.db.get_single_value("System Settings", "language") or "en"
	for module, domain in module_def_restrict_to_domain_mapper.iteritems():
		if frappe.db.exists("Domain", _(domain, lang)):
			frappe.db.set_value("Module Def", module, "restrict_to_domain", _(domain, lang))
		elif frappe.db.exists("Domain", domain):
			frappe.db.set_value("Module Def", module, "restrict_to_domain", domain)
		else:
			pass
