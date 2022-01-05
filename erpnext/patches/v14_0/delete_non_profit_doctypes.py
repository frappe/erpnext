import frappe


def execute():
	frappe.delete_doc("Module Def", "Non Profit", ignore_missing=True, force=True)

	frappe.delete_doc("Workspace", "Non Profit", ignore_missing=True, force=True)

	reports = frappe.get_all("Report", {"module": "Non Profit", "is_standard": "Yes"}, pluck='name')
	for report in reports:
		frappe.delete_doc("Report", report, ignore_missing=True, force=True)

	dashboards = frappe.get_all("Dashboard", {"module": "Non Profit", "is_standard": 1}, pluck='name')
	for dashboard in dashboards:
		frappe.delete_doc("Dashboard", dashboard, ignore_missing=True, force=True)

	doctypes = frappe.get_all("DocType", {"module": "Non Profit", "custom": 0}, pluck='name')
	for doctype in doctypes:
		frappe.delete_doc("DocType", doctype, ignore_missing=True)
