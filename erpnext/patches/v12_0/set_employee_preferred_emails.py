import frappe


def execute():
	employees = frappe.get_all("Employee")
	for employee in employees:
		employee_doc = frappe.get_doc("Employee", employee)
		employee_doc.set_preferred_email()
		employee_doc.save()
