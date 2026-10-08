import frappe
from frappe.query_builder.functions import Coalesce, NullIf
from pypika.terms import Bracket


def execute():
	timesheet = frappe.qb.DocType("Timesheet")
	employee = frappe.qb.DocType("Employee")
	employee_user = (
		frappe.qb.from_(employee).select(employee.user_id).where(employee.name == timesheet.employee)
	)

	(
		frappe.qb.update(timesheet)
		.set(timesheet.user, Coalesce(NullIf(Bracket(employee_user), ""), timesheet.owner))
		.where(timesheet.user.isnull() | (timesheet.user == ""))
	).run()
