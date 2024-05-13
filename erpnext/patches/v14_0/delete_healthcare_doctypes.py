import frappe


def execute():
	if "healthcare" in frappe.get_installed_apps():
		return

	frappe.delete_doc("Workspace", "Healthcare", ignore_missing=True, force=True)

	pages = frappe.get_all("Page", {"module": "healthcare"}, pluck="name")
	for page in pages:
		frappe.delete_doc("Page", page, ignore_missing=True, force=True)

	reports = frappe.get_all("Report", {"module": "healthcare", "is_standard": "Yes"}, pluck="name")
	for report in reports:
		frappe.delete_doc("Report", report, ignore_missing=True, force=True)

	print_formats = frappe.get_all("Print Format", {"module": "healthcare", "standard": "Yes"}, pluck="name")
	for print_format in print_formats:
		frappe.delete_doc("Print Format", print_format, ignore_missing=True, force=True)

	frappe.reload_doc("website", "doctype", "website_settings")
	forms = frappe.get_all("Web Form", {"module": "healthcare", "is_standard": 1}, pluck="name")
	for form in forms:
		frappe.delete_doc("Web Form", form, ignore_missing=True, force=True)

	dashboards = frappe.get_all("Dashboard", {"module": "healthcare", "is_standard": 1}, pluck="name")
	for dashboard in dashboards:
		frappe.delete_doc("Dashboard", dashboard, ignore_missing=True, force=True)

	dashboards = frappe.get_all("Dashboard Chart", {"module": "healthcare", "is_standard": 1}, pluck="name")
	for dashboard in dashboards:
		frappe.delete_doc("Dashboard Chart", dashboard, ignore_missing=True, force=True)

	frappe.reload_doc("desk", "doctype", "number_card")
	cards = frappe.get_all("Number Card", {"module": "healthcare", "is_standard": 1}, pluck="name")
	for card in cards:
		frappe.delete_doc("Number Card", card, ignore_missing=True, force=True)

	titles = ["Lab Test", "Prescription", "Patient Appointment", "Patient"]
	items = frappe.get_all("Portal Menu Item", filters=[["title", "in", titles]], pluck="name")
	for item in items:
		frappe.delete_doc("Portal Menu Item", item, ignore_missing=True, force=True)

	doctypes = frappe.get_all("DocType", {"module": "healthcare", "custom": 0}, pluck="name")
	for doctype in doctypes:
		frappe.delete_doc("DocType", doctype, ignore_missing=True)

	frappe.delete_doc("Module Def", "Healthcare", ignore_missing=True, force=True)

	custom_fields = {
		"Sales Invoice": ["patient", "patient_name", "ref_practitioner"],
		"Sales Invoice Item": ["reference_dt", "reference_dn"],
		"Stock Entry": ["inpatient_medication_entry"],
		"Stock Entry Detail": ["patient", "inpatient_medication_entry_child"],
	}
	for doc, fields in custom_fields.items():
		filters = {"dt": doc, "fieldname": ["in", fields]}
		records = frappe.get_all("Custom Field", filters=filters, pluck="name")
		for record in records:
			frappe.delete_doc("Custom Field", record, ignore_missing=True, force=True)
