import click
import frappe


def execute():
	if "erpnext_france" in frappe.get_installed_apps():
		return
	click.secho(
		"Feature for region France will be remove in version-15 and moved to a separate app\n"
		"Please install the app to continue using the regionnal France features: https://github.com/scopen-coop/erpnext_france.git",
		fg="yellow",
	)
