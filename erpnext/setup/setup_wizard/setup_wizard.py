# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils.telemetry import capture

from erpnext.setup.setup_wizard.operations import install_fixtures as fixtures


def get_setup_stages(args=None):  # nosemgrep
	stages = [
		{
			"status": _("Setting up the basics"),
			"fail_msg": _("We couldn't set up the basics"),
			"tasks": [{"fn": stage_fixtures, "args": args, "fail_msg": _("We couldn't set up the basics")}],
		},
		{
			"status": _("Creating your company"),
			"fail_msg": _("We couldn't create your company"),
			"tasks": [{"fn": setup_company, "args": args, "fail_msg": _("We couldn't create your company")}],
		},
		{
			"status": _("Applying recommended settings"),
			"fail_msg": _("We couldn't apply the recommended settings"),
			"tasks": [
				{
					"fn": setup_defaults,
					"args": args,
					"fail_msg": _("We couldn't apply the recommended settings"),
				},
			],
		},
		{
			"status": _("Personalizing your setup"),
			"fail_msg": _("We couldn't personalize your setup"),
			"tasks": [
				{
					"fn": capture_user_persona,
					"args": args,
					"fail_msg": _("We couldn't personalize your setup"),
				}
			],
		},
	]

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


# Only for programmatical use
def setup_complete(args=None):  # nosemgrep
	stage_fixtures(args)
	setup_company(args)
	setup_defaults(args)
