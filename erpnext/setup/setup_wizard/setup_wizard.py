# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _

from erpnext.setup.demo import setup_demo_data
from erpnext.setup.setup_wizard.operations import install_fixtures as fixtures


def get_setup_stages(args=None):
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


def stage_fixtures(args):
	fixtures.install(args.get("country"))


def setup_company(args):
	fixtures.install_company(args)


def setup_defaults(args):
	fixtures.install_defaults(frappe._dict(args))


def setup_demo(args):  # nosemgrep
	setup_demo_data(args.get("company_name"))


# Only for programmatical use
def setup_complete(args=None):
	stage_fixtures(args)
	setup_company(args)
	setup_defaults(args)
