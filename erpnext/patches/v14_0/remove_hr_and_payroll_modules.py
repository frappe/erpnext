import frappe


def execute():
	if "hrms" in frappe.get_installed_apps():
		return

	frappe.delete_doc("Module Def", "HR", ignore_missing=True, force=True)
	frappe.delete_doc("Module Def", "Payroll", ignore_missing=True, force=True)

	frappe.delete_doc("Workspace", "HR", ignore_missing=True, force=True)
	frappe.delete_doc("Workspace", "Payroll", ignore_missing=True, force=True)

	print_formats = frappe.get_all(
		"Print Format", {"module": ("in", ["HR", "Payroll"]), "standard": "Yes"}, pluck="name"
	)
	for print_format in print_formats:
		frappe.delete_doc("Print Format", print_format, ignore_missing=True, force=True)

	reports = frappe.get_all(
		"Report", {"module": ("in", ["HR", "Payroll"]), "is_standard": "Yes"}, pluck="name"
	)
	for report in reports:
		frappe.delete_doc("Report", report, ignore_missing=True, force=True)

	# reports moved from Projects, Accounts, and Regional module to HRMS app
	for report in [
		"Project Profitability",
		"Employee Hours Utilization Based On Timesheet",
		"Unpaid Expense Claim",
		"Professional Tax Deductions",
		"Provident Fund Deductions",
	]:
		frappe.delete_doc("Report", report, ignore_missing=True)

	dashboards = frappe.get_all(
		"Dashboard", {"module": ("in", ["HR", "Payroll"]), "is_standard": 1}, pluck="name"
	)
	for dashboard in dashboards:
		frappe.delete_doc("Dashboard", dashboard, ignore_missing=True, force=True)

	doctypes = frappe.get_all(
		"DocType", {"module": ("in", ["HR", "Payroll"]), "custom": 0}, pluck="name"
	)
	for doctype in doctypes:
		frappe.delete_doc("DocType", doctype, ignore_missing=True)

	frappe.delete_doc("DocType", "Salary Slip Loan", ignore_missing=True)
	frappe.delete_doc("DocType", "Salary Component Account", ignore_missing=True)

	notifications = frappe.get_all(
		"Notification", {"module": ("in", ["HR", "Payroll"]), "is_standard": 1}, pluck="name"
	)
	for notifcation in notifications:
		frappe.delete_doc("Notification", notifcation, ignore_missing=True)
