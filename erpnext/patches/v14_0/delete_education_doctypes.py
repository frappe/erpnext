import click
import frappe


def execute():
	if "education" in frappe.get_installed_apps():
		return

	frappe.delete_doc("Workspace", "Education", ignore_missing=True, force=True)

	pages = frappe.get_all("Page", {"module": "education"}, pluck="name")
	for page in pages:
		frappe.delete_doc("Page", page, ignore_missing=True, force=True)

	reports = frappe.get_all("Report", {"module": "education", "is_standard": "Yes"}, pluck="name")
	for report in reports:
		frappe.delete_doc("Report", report, ignore_missing=True, force=True)

	print_formats = frappe.get_all(
		"Print Format", {"module": "education", "standard": "Yes"}, pluck="name"
	)
	for print_format in print_formats:
		frappe.delete_doc("Print Format", print_format, ignore_missing=True, force=True)

	frappe.reload_doc("website", "doctype", "website_settings")
	forms = frappe.get_all("Web Form", {"module": "education", "is_standard": 1}, pluck="name")
	for form in forms:
		frappe.delete_doc("Web Form", form, ignore_missing=True, force=True)

	dashboards = frappe.get_all("Dashboard", {"module": "education", "is_standard": 1}, pluck="name")
	for dashboard in dashboards:
		frappe.delete_doc("Dashboard", dashboard, ignore_missing=True, force=True)

	dashboards = frappe.get_all(
		"Dashboard Chart", {"module": "education", "is_standard": 1}, pluck="name"
	)
	for dashboard in dashboards:
		frappe.delete_doc("Dashboard Chart", dashboard, ignore_missing=True, force=True)

	frappe.reload_doc("desk", "doctype", "number_card")
	cards = frappe.get_all("Number Card", {"module": "education", "is_standard": 1}, pluck="name")
	for card in cards:
		frappe.delete_doc("Number Card", card, ignore_missing=True, force=True)

	doctypes = frappe.get_all("DocType", {"module": "education", "custom": 0}, pluck="name")
	for doctype in doctypes:
		frappe.delete_doc("DocType", doctype, ignore_missing=True)

	frappe.delete_doc("Module Def", "Education", ignore_missing=True, force=True)

	click.secho(
		"Education Module is moved to a separate app"
		"Please install the app to continue using the module: https://github.com/frappe/education",
		fg="yellow",
	)
