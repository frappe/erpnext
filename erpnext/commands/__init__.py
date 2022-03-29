# Copyright (c) 2015, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import click
import frappe
from frappe.commands import get_site, pass_context


def call_command(cmd, context):
	return click.Context(cmd, obj=context).forward(cmd)


@click.command("make-demo")
@click.option("--site", help="site name")
@click.option("--domain", default="Manufacturing")
@click.option("--days", default=100, help="Run the demo for so many days. Default 100")
@click.option(
	"--resume", default=False, is_flag=True, help="Continue running the demo for given days"
)
@click.option("--reinstall", default=False, is_flag=True, help="Reinstall site before demo")
@pass_context
def make_demo(context, site, domain="Manufacturing", days=100, resume=False, reinstall=False):
	"Reinstall site and setup demo"
	from frappe.commands.site import _reinstall
	from frappe.installer import install_app

	site = get_site(context)

	if resume:
		with frappe.init_site(site):
			frappe.connect()
			from erpnext.demo import demo

			demo.simulate(days=days)
	else:
		if reinstall:
			_reinstall(site, yes=True)
		with frappe.init_site(site=site):
			frappe.connect()
			if not "erpnext" in frappe.get_installed_apps():
				install_app("erpnext")

			# import needs site
			from erpnext.demo import demo

			demo.make(domain, days)


commands = [make_demo]
