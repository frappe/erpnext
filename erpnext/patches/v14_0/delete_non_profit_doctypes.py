import frappe


def execute():
	frappe.delete_doc("Module Def", "Non Profit", ignore_missing=True, force=True)

	frappe.delete_doc("Workspace", "Non Profit", ignore_missing=True, force=True)

	print_formats = frappe.get_all("Print Format", {"module": "Non Profit", "standard": "Yes"}, pluck='name')
	for print_format in print_formats:
		frappe.delete_doc("Print Format", print_format, ignore_missing=True, force=True)

	print_formats = ['80G Certificate for Membership', '80G Certificate for Donation']
	for print_format in print_formats:
		frappe.delete_doc("Print Format", print_format, ignore_missing=True, force=True)

	reports = frappe.get_all("Report", {"module": "Non Profit", "is_standard": "Yes"}, pluck='name')
	for report in reports:
		frappe.delete_doc("Report", report, ignore_missing=True, force=True)

	dashboards = frappe.get_all("Dashboard", {"module": "Non Profit", "is_standard": 1}, pluck='name')
	for dashboard in dashboards:
		frappe.delete_doc("Dashboard", dashboard, ignore_missing=True, force=True)

	doctypes = frappe.get_all("DocType", {"module": "Non Profit", "custom": 0}, pluck='name')
	for doctype in doctypes:
		frappe.delete_doc("DocType", doctype, ignore_missing=True)

	doctypes = ['Tax Exemption 80G Certificate', 'Tax Exemption 80G Certificate Detail']
	for doctype in doctypes:
		frappe.delete_doc("DocType", doctype, ignore_missing=True)

	custom_fields = [
		{"dt": "Member", "fieldname": "pan_number"},
		{"dt": "Donor", "fieldname": "pan_number"},
	]
	for field in custom_fields:
		custom_field = frappe.db.get_value("Custom Field", field)
		frappe.delete_doc("Custom Field", custom_field, ignore_missing=True)
