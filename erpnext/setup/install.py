# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.desk.page.setup_wizard.setup_wizard import add_all_roles_to
from frappe.utils import cint

from erpnext.accounts.doctype.cash_flow_mapper.default_cash_flow_mapper import DEFAULT_MAPPERS
from erpnext.setup.default_energy_point_rules import get_default_energy_point_rules
from erpnext.setup.doctype.incoterm.incoterm import create_incoterms

from .default_success_action import get_default_success_action

default_mail_footer = """<div style="padding: 7px; text-align: right; color: #888"><small>Sent via
	<a style="color: #888" href="http://erpnext.org">ERPNext</a></div>"""


def after_install():
	frappe.get_doc({"doctype": "Role", "role_name": "Analytics"}).insert()
	set_single_defaults()
	create_print_setting_custom_fields()
	add_all_roles_to("Administrator")
	create_default_cash_flow_mapper_templates()
	create_default_success_action()
	create_default_energy_point_rules()
	create_incoterms()
	add_company_to_session_defaults()
	add_standard_navbar_items()
	add_app_name()
	setup_log_settings()
	frappe.db.commit()


def check_setup_wizard_not_completed():
	if cint(frappe.db.get_single_value("System Settings", "setup_complete") or 0):
		message = """ERPNext can only be installed on a fresh site where the setup wizard is not completed.
You can reinstall this site (after saving your data) using: bench --site [sitename] reinstall"""
		frappe.throw(message)  # nosemgrep


def set_single_defaults():
	for dt in (
		"Accounts Settings",
		"Print Settings",
		"Buying Settings",
		"Selling Settings",
		"Stock Settings",
	):
		default_values = frappe.db.sql(
			"""select fieldname, `default` from `tabDocField`
			where parent=%s""",
			dt,
		)
		if default_values:
			try:
				doc = frappe.get_doc(dt, dt)
				for fieldname, value in default_values:
					doc.set(fieldname, value)
				doc.flags.ignore_mandatory = True
				doc.save()
			except frappe.ValidationError:
				pass

	frappe.db.set_default("date_format", "dd-mm-yyyy")

	setup_currency_exchange()


def setup_currency_exchange():
	ces = frappe.get_single("Currency Exchange Settings")
	try:
		ces.set("result_key", [])
		ces.set("req_params", [])

		ces.api_endpoint = "https://frankfurter.app/{transaction_date}"
		ces.append("result_key", {"key": "rates"})
		ces.append("result_key", {"key": "{to_currency}"})
		ces.append("req_params", {"key": "base", "value": "{from_currency}"})
		ces.append("req_params", {"key": "symbols", "value": "{to_currency}"})
		ces.save()
	except frappe.ValidationError:
		pass


def create_print_setting_custom_fields():
	create_custom_fields(
		{
			"Print Settings": [
				{
					"label": _("Compact Item Print"),
					"fieldname": "compact_item_print",
					"fieldtype": "Check",
					"default": "1",
					"insert_after": "with_letterhead",
				},
				{
					"label": _("Print UOM after Quantity"),
					"fieldname": "print_uom_after_quantity",
					"fieldtype": "Check",
					"default": "0",
					"insert_after": "compact_item_print",
				},
				{
					"label": _("Print taxes with zero amount"),
					"fieldname": "print_taxes_with_zero_amount",
					"fieldtype": "Check",
					"default": "0",
					"insert_after": "allow_print_for_cancelled",
				},
			]
		}
	)


def create_default_cash_flow_mapper_templates():
	for mapper in DEFAULT_MAPPERS:
		if not frappe.db.exists("Cash Flow Mapper", mapper["section_name"]):
			doc = frappe.get_doc(mapper)
			doc.insert(ignore_permissions=True)


def create_default_success_action():
	for success_action in get_default_success_action():
		if not frappe.db.exists("Success Action", success_action.get("ref_doctype")):
			doc = frappe.get_doc(success_action)
			doc.insert(ignore_permissions=True)


def create_default_energy_point_rules():

	for rule in get_default_energy_point_rules():
		# check if any rule for ref. doctype exists
		rule_exists = frappe.db.exists(
			"Energy Point Rule", {"reference_doctype": rule.get("reference_doctype")}
		)
		if rule_exists:
			continue
		doc = frappe.get_doc(rule)
		doc.insert(ignore_permissions=True)


def add_company_to_session_defaults():
	settings = frappe.get_single("Session Default Settings")
	settings.append("session_defaults", {"ref_doctype": "Company"})
	settings.save()


def add_standard_navbar_items():
	navbar_settings = frappe.get_single("Navbar Settings")

	erpnext_navbar_items = [
		{
			"item_label": "Documentation",
			"item_type": "Route",
			"route": "https://erpnext.com/docs/user/manual",
			"is_standard": 1,
		},
		{
			"item_label": "User Forum",
			"item_type": "Route",
			"route": "https://discuss.erpnext.com",
			"is_standard": 1,
		},
		{
			"item_label": "Report an Issue",
			"item_type": "Route",
			"route": "https://github.com/frappe/erpnext/issues",
			"is_standard": 1,
		},
	]

	current_navbar_items = navbar_settings.help_dropdown
	navbar_settings.set("help_dropdown", [])

	for item in erpnext_navbar_items:
		current_labels = [item.get("item_label") for item in current_navbar_items]
		if not item.get("item_label") in current_labels:
			navbar_settings.append("help_dropdown", item)

	for item in current_navbar_items:
		navbar_settings.append(
			"help_dropdown",
			{
				"item_label": item.item_label,
				"item_type": item.item_type,
				"route": item.route,
				"action": item.action,
				"is_standard": item.is_standard,
				"hidden": item.hidden,
			},
		)

	navbar_settings.save()


def add_app_name():
	frappe.db.set_value("System Settings", None, "app_name", "ERPNext")


def setup_log_settings():
	log_settings = frappe.get_single("Log Settings")
	log_settings.append("logs_to_clear", {"ref_doctype": "Repost Item Valuation", "days": 60})

	log_settings.save(ignore_permissions=True)
