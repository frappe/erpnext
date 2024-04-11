# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import click
import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.desk.page.setup_wizard.setup_wizard import add_all_roles_to
from frappe.utils import cint

import erpnext
from erpnext.setup.default_energy_point_rules import get_default_energy_point_rules
from erpnext.setup.doctype.incoterm.incoterm import create_incoterms

from .default_success_action import get_default_success_action

default_mail_footer = """<div style="padding: 7px; text-align: right; color: #888"><small>Sent via
	<a style="color: #888" href="http://erpnext.org">ERPNext</a></div>"""


def after_install():
	if not frappe.db.exists("Role", "Analytics"):
		frappe.get_doc({"doctype": "Role", "role_name": "Analytics"}).insert()

	set_single_defaults()
	create_print_setting_custom_fields()
	add_all_roles_to("Administrator")
	create_default_success_action()
	create_default_energy_point_rules()
	create_incoterms()
	create_default_role_profiles()
	add_company_to_session_defaults()
	add_standard_navbar_items()
	add_app_name()
	hide_workspaces()
	update_roles()
	frappe.db.commit()


def check_setup_wizard_not_completed():
	if cint(frappe.db.get_single_value("System Settings", "setup_complete") or 0):
		message = """ERPNext can only be installed on a fresh site where the setup wizard is not completed.
You can reinstall this site (after saving your data) using: bench --site [sitename] reinstall"""
		frappe.throw(message)  # nosemgrep


def check_frappe_version():
	def major_version(v: str) -> str:
		return v.split(".")[0]

	frappe_version = major_version(frappe.__version__)
	erpnext_version = major_version(erpnext.__version__)

	if frappe_version == erpnext_version:
		return

	click.secho(
		f"You're attempting to install ERPNext version {erpnext_version} with Frappe version {frappe_version}. "
		"This is not supported and will result in broken install. Switch to correct branch before installing.",
		fg="red",
	)

	raise SystemExit(1)


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
			"route": "https://docs.erpnext.com/",
			"is_standard": 1,
		},
		{
			"item_label": "User Forum",
			"item_type": "Route",
			"route": "https://discuss.frappe.io",
			"is_standard": 1,
		},
		{
			"item_label": "Frappe School",
			"item_type": "Route",
			"route": "https://frappe.school?utm_source=in_app",
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
		if item.get("item_label") not in current_labels:
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
	frappe.db.set_single_value("System Settings", "app_name", "ERPNext")


def hide_workspaces():
	for ws in ["Integration", "Settings"]:
		frappe.db.set_value("Workspace", ws, "public", 0)


def update_roles():
	website_user_roles = ("Customer", "Supplier")
	for role in website_user_roles:
		frappe.db.set_value("Role", role, "desk_access", 0)


def create_default_role_profiles():
	for role_profile_name, roles in DEFAULT_ROLE_PROFILES.items():
		role_profile = frappe.new_doc("Role Profile")
		role_profile.role_profile = role_profile_name
		for role in roles:
			role_profile.append("roles", {"role": role})

		role_profile.insert(ignore_permissions=True)


DEFAULT_ROLE_PROFILES = {
	"Inventory": [
		"Stock User",
		"Stock Manager",
		"Item Manager",
	],
	"Manufacturing": [
		"Stock User",
		"Manufacturing User",
		"Manufacturing Manager",
	],
	"Accounts": [
		"Accounts User",
		"Accounts Manager",
	],
	"Sales": [
		"Sales User",
		"Stock User",
		"Sales Manager",
	],
	"Purchase": [
		"Item Manager",
		"Stock User",
		"Purchase User",
		"Purchase Manager",
	],
}
