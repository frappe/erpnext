# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from erpnext.hr.doctype.leave_application.leave_application \
	import get_leave_balance_on, get_leaves_for_period

from erpnext.hr.report.employee_leave_balance_summary.employee_leave_balance_summary \
	import get_department_leave_approver_map

def execute(filters=None):
	leave_types = frappe.db.sql_list("select name from `tabLeave Type` order by name asc")

	columns = get_columns(leave_types)
	data = get_data(filters, leave_types)

	return columns, data

def get_columns(leave_types):
	columns = [
		_("Employee") + ":Link.Employee:150",
		_("Employee Name") + "::200",
		_("Department") +"::150"
	]

	for leave_type in leave_types:
		columns.append(_(leave_type) + " " + _("Opening") + ":Float:160")
		columns.append(_(leave_type) + " " + _("Taken") + ":Float:160")
		columns.append(_(leave_type) + " " + _("Balance") + ":Float:160")
		columns.append(_(leave_type) + " " + _("Allocated") + ":Float:160")
		columns.append(_(leave_type) + " " + _("Expired") + ":Float:160")

	return columns

def get_conditions(filters):
	conditions = {
		"status": "Active",
		"company": filters.company,
	}
	if filters.get("department"):
		conditions.update({"department": filters.get("department")})
	if filters.get("employee"):
		conditions.update({"employee": filters.get("employee")})

	return conditions

def get_data(filters, leave_types):
	user = frappe.session.user
	conditions = get_conditions(filters)

	if filters.to_date <= filters.from_date:
		frappe.throw(_("From date can not be greater than than To date"))

	active_employees = frappe.get_all("Employee",
		filters=conditions,
		fields=["name", "employee_name", "department", "user_id", "leave_approver"])

	department_approver_map = get_department_leave_approver_map(filters.get('department'))

	data = []
	for employee in active_employees:
		leave_approvers = department_approver_map.get(employee.department_name, [])
		if employee.leave_approver:
			leave_approvers.append(employee.leave_approver)

		if (len(leave_approvers) and user in leave_approvers) or (user in ["Administrator", employee.user_id]) or ("HR Manager" in frappe.get_roles(user)):
			row = [employee.name, employee.employee_name, employee.department]

			for leave_type in leave_types:
				# leaves taken
				leaves_taken = get_leaves_for_period(employee.name, leave_type,
					filters.from_date, filters.to_date) * -1

				# opening balance
				opening = get_leave_balance_on(employee.name, leave_type, filters.from_date)

				# closing balance
				closing = max(opening - leaves_taken, 0)

				new_allocation , expired_leaves = get_allocated_and_expired_leaves(filters.from_date, filters.to_date, employee.name, leave_type)

				row += [opening, leaves_taken, closing, new_allocation, expired_leaves]

			data.append(row)
	return data

def get_allocated_and_expired_leaves(from_date, to_date, employee, leave_type):

	from frappe.utils import getdate

	new_allocation = 0
	expired_leaves = 0

	records= frappe.db.sql("""
		SELECT
			employee, leave_type, from_date, to_date, leaves, transaction_name,
			is_carry_forward, is_expired
		FROM `tabLeave Ledger Entry`
		WHERE employee=%(employee)s AND leave_type=%(leave_type)s
			AND docstatus=1 AND leaves>0
			AND (from_date between %(from_date)s AND %(to_date)s
				OR to_date between %(from_date)s AND %(to_date)s
				OR (from_date < %(from_date)s AND to_date > %(to_date)s))
	""", {
		"from_date": from_date,
		"to_date": to_date,
		"employee": employee,
		"leave_type": leave_type
	}, as_dict=1)

	for record in records:
		if record.to_date <= getdate(to_date):
			expired_leaves += record.leaves

		if record.from_date >= getdate(from_date):
			new_allocation += record.leaves

	return new_allocation, expired_leaves
