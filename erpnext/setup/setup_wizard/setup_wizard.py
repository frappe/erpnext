# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils.telemetry import capture

from erpnext.setup.demo import setup_demo_data
from erpnext.setup.setup_wizard.operations import install_fixtures as fixtures


def get_setup_stages(args=None):  # nosemgrep
	stages = [
		{
			"status": _("Installing presets"),
			"fail_msg": _("Failed to install presets"),
			"tasks": [{"fn": stage_fixtures, "args": args, "fail_msg": _("Failed to install presets")}],
		},
		{
			"status": _("Setting up company"),
			"fail_msg": _("Failed to setup company"),
			"tasks": [{"fn": setup_company, "args": args, "fail_msg": _("Failed to setup company")}],
		},
		{
			"status": _("Setting defaults"),
			"fail_msg": _("Failed to set defaults"),
			"tasks": [
				{"fn": setup_defaults, "args": args, "fail_msg": _("Failed to setup defaults")},
			],
		},
		{
			"status": _("Personalizing your setup"),
			"fail_msg": _("Failed to personalize your setup"),
			"tasks": [
				{"fn": capture_user_persona, "args": args, "fail_msg": _("Failed to personalize your setup")}
			],
		},
	]

	if args.get("setup_demo"):
		stages.append(
			{
				"status": _("Creating demo data"),
				"fail_msg": _("Failed to create demo data"),
				"tasks": [{"fn": setup_demo, "args": args, "fail_msg": _("Failed to create demo data")}],
			}
		)

	return stages


def capture_user_persona(args):  # nosemgrep
	"""Send the persona answers captured on the setup slide to telemetry."""
	if not args:
		return

	capture(
		"user_persona_submitted",
		"erpnext",
		properties={
			"implementing_for": args.get("persona_implementing_for"),
			"company_size": args.get("persona_company_size"),
			"industry": args.get("persona_industry"),
			"current_system": args.get("persona_current_system"),
			"module_accounting": bool(args.get("module_accounting")),
			"module_stock": bool(args.get("module_stock")),
			"module_manufacturing": bool(args.get("module_manufacturing")),
			"module_projects": bool(args.get("module_projects")),
			"country": args.get("country"),
			"language": args.get("language"),
		},
	)


def stage_fixtures(args):  # nosemgrep
	fixtures.install(args.get("country"))


def setup_company(args):  # nosemgrep
	fixtures.install_company(args)


def setup_defaults(args):  # nosemgrep
	fixtures.install_defaults(frappe._dict(args))


def setup_demo(args):  # nosemgrep
	setup_demo_data(args.get("company_name"))


# Only for programmatical use
def setup_complete(args=None):  # nosemgrep
	stage_fixtures(args)
	setup_company(args)
	setup_defaults(args)
