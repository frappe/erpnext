import click
import frappe


def execute():
	if (
		not frappe.db.exists("Company", {"country": "India"})
		or "india_compliance" in frappe.get_installed_apps()
	):
		return

	click.secho(
		"India-specific regional features have been moved to a separate app"
		" and will be removed from ERPNext in Version 14."
		" Please install India Compliance after upgrading to Version 14:\n"
		"https://github.com/resilient-tech/india-compliance",
		fg="yellow",
	)
