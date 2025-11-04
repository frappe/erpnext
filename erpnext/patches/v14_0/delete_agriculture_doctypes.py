import frappe


def execute():
	if "agriculture" in frappe.get_installed_apps():
		return

	frappe.delete_doc("Module Def", "Agriculture", ignore_missing=True, force=True)

	frappe.delete_doc("Workspace", "Agriculture", ignore_missing=True, force=True)

	reports = frappe.get_all("Report", {"module": "agriculture", "is_standard": "Yes"}, pluck="name")
	for report in reports:
		frappe.delete_doc("Report", report, ignore_missing=True, force=True)

	dashboards = frappe.get_all("Dashboard", {"module": "agriculture", "is_standard": 1}, pluck="name")
	for dashboard in dashboards:
		frappe.delete_doc("Dashboard", dashboard, ignore_missing=True, force=True)

	doctypes = frappe.get_all("DocType", {"module": "agriculture", "custom": 0}, pluck="name")
	for doctype in doctypes:
		frappe.delete_doc("DocType", doctype, ignore_missing=True)

	frappe.delete_doc("Module Def", "Agriculture", ignore_missing=True, force=True)
