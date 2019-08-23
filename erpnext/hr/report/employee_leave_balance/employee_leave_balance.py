# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from erpnext.hr.doctype.leave_application.leave_application \
	import get_leave_balance_on, get_leaves_for_period


def execute(filters=None):
	leave_types = frappe.db.sql_list("select name from `tabLeave Type` order by name asc")

	columns = get_columns(leave_types)
	data = get_data(filters, leave_types)

	return columns, data

def get_columns(leave_types):
	columns = [
		_("Employee") + ":Link/Employee:150",
		_("Employee Name") + "::200",
		_("Department") +"::150"
	]

	for leave_type in leave_types:
		columns.append(_(leave_type) + " " + _("Opening") + ":Float:160")
		columns.append(_(leave_type) + " " + _("Taken") + ":Float:160")
		columns.append(_(leave_type) + " " + _("Balance") + ":Float:160")

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
		fields=["name", "employee_name", "department", "user_id"])

	data = []
	for employee in active_employees:
		leave_approvers = get_approvers(employee.department)
		if (len(leave_approvers) and user in leave_approvers) or (user in ["Administrator", employee.user_id]) or ("HR Manager" in frappe.get_roles(user)):
			row = [employee.name, employee.employee_name, employee.department]

			for leave_type in leave_types:
				# leaves taken
				leaves_taken = get_leaves_for_period(employee.name, leave_type,
					filters.from_date, filters.to_date) * -1

				# opening balance
				opening = get_total_allocated_leaves(employee.name, leave_type, filters.from_date, filters.to_date)

				# closing balance
				closing = flt(opening) - flt(leaves_taken)

				row += [opening, leaves_taken, closing]

			data.append(row)

	return data

def get_approvers(department):
	if not department:
		return []

	approvers = []
	# get current department and all its child
	department_details = frappe.db.get_value("Department", {"name": department}, ["lft", "rgt"], as_dict=True)
	department_list = frappe.db.sql("""select name from `tabDepartment`
		where lft >= %s and rgt <= %s order by lft desc
		""", (department_details.lft, department_details.rgt), as_list = True)

	# retrieve approvers list from current department and from its subsequent child departments
	for d in department_list:
		approvers.extend([l.leave_approver for l in frappe.db.sql("""select approver from `tabDepartment Approver` \
			where parent = %s and parentfield = 'leave_approvers'""", (d), as_dict=True)])

	return approvers

def get_total_allocated_leaves(employee, leave_type, from_date, to_date):
	''' Returns leave allocation between from date and to date '''
	leave_allocation_records = frappe.db.get_all('Leave Ledger Entry', filters={
			'docstatus': 1,
			'is_expired': 0,
			'leave_type': leave_type,
			'employee': employee,
			'transaction_type': 'Leave Allocation'
		}, or_filters={
			'from_date': ['between', (from_date, to_date)],
			'to_date': ['between', (from_date, to_date)]
		}, fields=['SUM(leaves) as leaves'])

	return flt(leave_allocation_records[0].get('leaves')) if leave_allocation_records else flt(0)