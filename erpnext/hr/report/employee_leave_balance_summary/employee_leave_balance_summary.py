# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _

from erpnext.hr.doctype.leave_application.leave_application import get_leave_details
from erpnext.hr.report.employee_leave_balance.employee_leave_balance import (
	get_department_leave_approver_map,
)


def execute(filters=None):
	leave_types = frappe.db.sql_list("select name from `tabLeave Type` order by name asc")

	columns = get_columns(leave_types)
	data = get_data(filters, leave_types)

	return columns, data


def get_columns(leave_types):
	columns = [
		_("Employee") + ":Link/Employee:150",
		_("Employee Name") + "::200",
		_("Department") + ":Link/Department:150",
	]

	for leave_type in leave_types:
		columns.append(_(leave_type) + ":Float:160")

	return columns


def get_conditions(filters):
	conditions = {
		"company": filters.company,
	}
	if filters.get("employee_status"):
		conditions.update({"status": filters.get("employee_status")})
	if filters.get("department"):
		conditions.update({"department": filters.get("department")})
	if filters.get("employee"):
		conditions.update({"employee": filters.get("employee")})

	return conditions


def get_data(filters, leave_types):
	user = frappe.session.user
	conditions = get_conditions(filters)

	active_employees = frappe.get_all(
		"Employee",
		filters=conditions,
		fields=["name", "employee_name", "department", "user_id", "leave_approver"],
	)

	department_approver_map = get_department_leave_approver_map(filters.get("department"))

	data = []
	for employee in active_employees:
		leave_approvers = department_approver_map.get(employee.department_name, [])
		if employee.leave_approver:
			leave_approvers.append(employee.leave_approver)

		row = [employee.name, employee.employee_name, employee.department]
		available_leave = get_leave_details(employee.name, filters.date)
		for leave_type in leave_types:
			remaining = 0
			if leave_type in available_leave["leave_allocation"]:
				# opening balance
				remaining = available_leave["leave_allocation"][leave_type]["remaining_leaves"]

			row += [remaining]

		data.append(row)

	return data
