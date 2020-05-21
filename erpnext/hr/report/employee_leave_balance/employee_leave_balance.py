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
		_("Employee") + ":Link.Employee:150",
		_("Employee Name") + "::200",
		_("Department") +"::150"
	]

	for leave_type in leave_types:
		columns.append(_(leave_type) + " " + _("Opening") + ":Float:160")
		columns.append(_(leave_type) + " " + _("Allocated") + ":Float:160")
		columns.append(_(leave_type) + " " + _("Expired") + ":Float:160")
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


				row += calculate_leaves_details(filters, leave_type, employee)

			data.append(row)
	return data

def calculate_leaves_details(filters, leave_type, employee):
	ledger_entries = get_leave_ledger_entries(filters.from_date, filters.to_date, employee.name, leave_type)

	#Leaves Deducted consist of both expired and leaves taken
	leaves_deducted = get_leaves_for_period(employee.name, leave_type,
		filters.from_date, filters.to_date) * -1

	# removing expired leaves
	leaves_taken = leaves_deducted - remove_expired_leave(ledger_entries)

	opening = get_leave_balance_on(employee.name, leave_type, filters.from_date)

	new_allocation , expired_allocation = get_allocated_and_expired_leaves(ledger_entries, filters.from_date, filters.to_date)

	#removing leaves taken from expired_allocation
	expired_leaves = max(expired_allocation - leaves_taken, 0)

	#Formula for calculating  closing balance
	closing = max(opening + new_allocation - (leaves_taken + expired_leaves), 0)

	return [opening, new_allocation, expired_leaves, leaves_taken, closing]


def remove_expired_leave(records):
	expired_within_period = 0
	for record in records:
		if record.is_expired:
			expired_within_period += record.leaves
	return expired_within_period * -1


def get_allocated_and_expired_leaves(records, from_date, to_date):

	from frappe.utils import getdate

	new_allocation = 0
	expired_leaves = 0

	for record in records:
		if record.to_date <= getdate(to_date) and record.leaves>0:
			expired_leaves += record.leaves

		if record.from_date >= getdate(from_date) and record.leaves>0:
			new_allocation += record.leaves

	return new_allocation, expired_leaves

def get_leave_ledger_entries(from_date, to_date, employee, leave_type):
	records= frappe.db.sql("""
		SELECT
			employee, leave_type, from_date, to_date, leaves, transaction_name, transaction_type
			is_carry_forward, is_expired
		FROM `tabLeave Ledger Entry`
		WHERE employee=%(employee)s AND leave_type=%(leave_type)s
			AND docstatus=1
			AND (from_date between %(from_date)s AND %(to_date)s
				OR to_date between %(from_date)s AND %(to_date)s
				OR (from_date < %(from_date)s AND to_date > %(to_date)s))
	""", {
		"from_date": from_date,
		"to_date": to_date,
		"employee": employee,
		"leave_type": leave_type
	}, as_dict=1)

	return records

def get_department_leave_approver_map(department=None):
	conditions=''
	if department:
		conditions="and (department_name = '%(department)s' or parent_department = '%(department)s')"%{'department': department}

	# get current department and all its child
	department_list = frappe.db.sql_list(""" SELECT name FROM `tabDepartment` WHERE disabled=0 {0}""".format(conditions)) #nosec

	# retrieve approvers list from current department and from its subsequent child departments
	approver_list = frappe.get_all('Department Approver', filters={
		'parentfield': 'leave_approvers',
		'parent': ('in', department_list)
	}, fields=['parent', 'approver'], as_list=1)

	approvers = {}

	for k, v in approver_list:
		approvers.setdefault(k, []).append(v)

	return approvers