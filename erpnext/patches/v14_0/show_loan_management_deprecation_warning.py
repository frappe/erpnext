import click
import frappe


def execute():
	if "lending" in frappe.get_installed_apps():
		return

	click.secho(
		"Loan Management module has been moved to a separate app"
		" and will be removed from ERPNext in Version 15."
		" Please install the Lending app when upgrading to Version 15"
		" to continue using the Loan Management module:\n"
		"https://github.com/frappe/lending",
		fg="yellow",
	)
