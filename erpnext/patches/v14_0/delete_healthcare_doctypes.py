import frappe


def execute():
	if "healthcare" in frappe.get_installed_apps():
		return

	reports = frappe.get_all("Report", {"module": "healthcare", "is_standard": "Yes"}, pluck='name')
	for report in reports:
		frappe.delete_doc("Report", report, ignore_missing=True)

	print_formats = frappe.get_all("Print Format", {"module": "healthcare", "standard": "Yes"}, pluck='name')
	for print_format in print_formats:
		frappe.delete_doc("Print Format", print_format, ignore_missing=True, force=True)

	forms = frappe.get_all("Web Form", {"module": "healthcare", "is_standard": "Yes"}, pluck='name')
	for form in forms:
		frappe.delete_doc("Web Form", form, ignore_missing=True, force=True)

	dashboards = frappe.get_all("Dashboard", {"module": "healthcare", "is_standard": "Yes"}, pluck='name')
	for dashboard in dashboards:
		frappe.delete_doc("Dashboard", dashboard, ignore_missing=True, force=True)

	dashboards = frappe.get_all("Dashboard Chart", {"module": "healthcare", "is_standard": "Yes"}, pluck='name')
	for dashboard in dashboards:
		frappe.delete_doc("Dashboard Chart", dashboard, ignore_missing=True, force=True)

	cards = frappe.get_all("Number Card", {"module": "healthcare", "is_standard": "Yes"}, pluck='name')
	for card in cards:
		frappe.delete_doc("Number Card", card, ignore_missing=True, force=True)

	titles = ['Lab Test', 'Prescription', 'Patient Appointment']
	items = frappe.get_all('Portal Menu Item', filters=[['title', 'in', titles]], pluck='name')
	for item in items:
		frappe.delete_doc("Portal Menu Item", item, ignore_missing=True, force=True)

	doctypes = frappe.get_all("DocType", {"module": "healthcare"}, pluck='name')
	for doctype in doctypes:
		frappe.delete_doc("DocType", doctype, ignore_missing=True)

	frappe.delete_doc("Module Def", "Healthcare", ignore_missing=True, force=True)
