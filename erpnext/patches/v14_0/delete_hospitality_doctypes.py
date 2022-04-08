import frappe


def execute():
	modules = ["Hotels", "Restaurant"]

	for module in modules:
		frappe.delete_doc("Module Def", module, ignore_missing=True, force=True)

		frappe.delete_doc("Workspace", module, ignore_missing=True, force=True)

		reports = frappe.get_all("Report", {"module": module, "is_standard": "Yes"}, pluck="name")
		for report in reports:
			frappe.delete_doc("Report", report, ignore_missing=True, force=True)

		dashboards = frappe.get_all("Dashboard", {"module": module, "is_standard": 1}, pluck="name")
		for dashboard in dashboards:
			frappe.delete_doc("Dashboard", dashboard, ignore_missing=True, force=True)

		doctypes = frappe.get_all("DocType", {"module": module, "custom": 0}, pluck="name")
		for doctype in doctypes:
			frappe.delete_doc("DocType", doctype, ignore_missing=True)

	custom_fields = [
		{"dt": "Sales Invoice", "fieldname": "restaurant"},
		{"dt": "Sales Invoice", "fieldname": "restaurant_table"},
		{"dt": "Price List", "fieldname": "restaurant_menu"},
	]

	for field in custom_fields:
		custom_field = frappe.db.get_value("Custom Field", field)
		frappe.delete_doc("Custom Field", custom_field, ignore_missing=True)
