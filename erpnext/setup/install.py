# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import print_function, unicode_literals

import frappe
from erpnext.accounts.doctype.cash_flow_mapper.default_cash_flow_mapper import DEFAULT_MAPPERS
from .default_success_action import get_default_success_action
from frappe import _
from frappe.utils import cint
from frappe.desk.page.setup_wizard.setup_wizard import add_all_roles_to
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from erpnext.setup.default_energy_point_rules import get_default_energy_point_rules

default_mail_footer = """<div style="padding: 7px; text-align: right; color: #888"><small>Sent via
	<a style="color: #888" href="http://erpnext.org">ERPNext</a></div>"""


def after_install():
	frappe.get_doc({'doctype': "Role", "role_name": "Analytics"}).insert()
	set_single_defaults()
	create_compact_item_print_custom_field()
	create_print_uom_after_qty_custom_field()
	create_print_zero_amount_taxes_custom_field()
	add_all_roles_to("Administrator")
	create_default_cash_flow_mapper_templates()
	create_default_success_action()
	create_default_energy_point_rules()
	add_company_to_session_defaults()
	add_standard_navbar_items()
	add_app_name()
	frappe.db.commit()


def check_setup_wizard_not_completed():
	if cint(frappe.db.get_single_value('System Settings', 'setup_complete') or 0):
		message = """ERPNext can only be installed on a fresh site where the setup wizard is not completed.
You can reinstall this site (after saving your data) using: bench --site [sitename] reinstall"""
		frappe.throw(message)


def set_single_defaults():
	for dt in ('Accounts Settings', 'Print Settings', 'HR Settings', 'Buying Settings',
		'Selling Settings', 'Stock Settings'):
		default_values = frappe.db.sql("""select fieldname, `default` from `tabDocField`
			where parent=%s""", dt)
		if default_values:
			try:
				b = frappe.get_doc(dt, dt)
				for fieldname, value in default_values:
					b.set(fieldname, value)
				b.save()
			except frappe.MandatoryError:
				pass
			except frappe.ValidationError:
				pass

	frappe.db.set_default("date_format", "dd-mm-yyyy")


def create_compact_item_print_custom_field():
	create_custom_field('Print Settings', {
		'label': _('Compact Item Print'),
		'fieldname': 'compact_item_print',
		'fieldtype': 'Check',
		'default': 1,
		'insert_after': 'with_letterhead'
	})


def create_print_uom_after_qty_custom_field():
	create_custom_field('Print Settings', {
		'label': _('Print UOM after Quantity'),
		'fieldname': 'print_uom_after_quantity',
		'fieldtype': 'Check',
		'default': 0,
		'insert_after': 'compact_item_print'
	})


def create_print_zero_amount_taxes_custom_field():
	create_custom_field('Print Settings', {
		'label': _('Print taxes with zero amount'),
		'fieldname': 'print_taxes_with_zero_amount',
		'fieldtype': 'Check',
		'default': 0,
		'insert_after': 'allow_print_for_cancelled'
	})


def create_default_cash_flow_mapper_templates():
	for mapper in DEFAULT_MAPPERS:
		if not frappe.db.exists('Cash Flow Mapper', mapper['section_name']):
			doc = frappe.get_doc(mapper)
			doc.insert(ignore_permissions=True)

def create_default_success_action():
	for success_action in get_default_success_action():
		if not frappe.db.exists('Success Action', success_action.get("ref_doctype")):
			doc = frappe.get_doc(success_action)
			doc.insert(ignore_permissions=True)

def create_default_energy_point_rules():

	for rule in get_default_energy_point_rules():
		# check if any rule for ref. doctype exists
		rule_exists = frappe.db.exists('Energy Point Rule', {
			'reference_doctype': rule.get('reference_doctype')
		})
		if rule_exists: continue
		doc = frappe.get_doc(rule)
		doc.insert(ignore_permissions=True)

def add_company_to_session_defaults():
	settings = frappe.get_single("Session Default Settings")
	settings.append("session_defaults", {
		"ref_doctype": "Company"
	})
	settings.save()

def add_standard_navbar_items():
	navbar_settings = frappe.get_single("Navbar Settings")

	erpnext_navbar_items = [
		{
			'item_label': 'Documentation',
			'item_type': 'Route',
			'route': 'https://erpnext.com/docs/user/manual',
			'is_standard': 1
		},
		{
			'item_label': 'User Forum',
			'item_type': 'Route',
			'route': 'https://discuss.erpnext.com',
			'is_standard': 1
		},
		{
			'item_label': 'Report an Issue',
			'item_type': 'Route',
			'route': 'https://github.com/frappe/erpnext/issues',
			'is_standard': 1
		}
	]

	current_nabvar_items = navbar_settings.help_dropdown
	navbar_settings.set('help_dropdown', [])

	for item in erpnext_navbar_items:
		navbar_settings.append('help_dropdown', item)

	for item in current_nabvar_items:
		navbar_settings.append('help_dropdown', {
			'item_label': item.item_label,
			'item_type': item.item_type,
			'route': item.route,
			'action': item.action,
			'is_standard': item.is_standard,
			'hidden': item.hidden
		})

	navbar_settings.save()

def add_app_name():
	settings = frappe.get_doc("System Settings")
	settings.app_name = _("ERPNext")