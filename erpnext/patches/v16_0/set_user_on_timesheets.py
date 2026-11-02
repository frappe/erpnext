import frappe
from frappe.query_builder.functions import NullIf
from pypika.terms import Bracket, Case


def execute():
	timesheet = frappe.qb.DocType("Timesheet")
	employee = frappe.qb.DocType("Employee")
	employee_user = (
		frappe.qb.from_(employee).select(employee.user_id).where(employee.name == timesheet.employee)
	)
	user = (
		Case()
		.when(timesheet.employee.isnull() | (timesheet.employee == ""), timesheet.owner)
		.else_(NullIf(Bracket(employee_user), ""))
	)

	(
		frappe.qb.update(timesheet)
		.set(timesheet.user, user)
		.where(timesheet.user.isnull() | (timesheet.user == ""))
	).run()
