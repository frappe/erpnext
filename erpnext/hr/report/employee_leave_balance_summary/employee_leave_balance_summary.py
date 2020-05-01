# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
from erpnext.hr.doctype.leave_application.leave_application import get_leaves_for_period, get_leave_balance_on
from erpnext.hr.report.employee_leave_balance.employee_leave_balance import calculate_leaves_details , get_department_leave_approver_map

def execute(filters=None):
	if filters.to_date <= filters.from_date:
		frappe.throw(_('From date can not be greater than than To date'))

	columns = get_columns()
	data = get_data(filters)

	return columns, data

def get_columns():
	columns = [{
		'label': _('Leave Type'),
		'fieldtype': 'Link',
		'fieldname': 'leave_type',
		'width': 300,
		'options': 'Leave Type'
	}, {
		'label': _('Employee'),
		'fieldtype': 'Link',
		'fieldname': 'employee',
		'width': 100,
		'options': 'Employee'
	}, {
		'label': _('Employee Name'),
		'fieldtype': 'Data',
		'fieldname': 'employee_name',
		'width': 100,
	}, {
		'label': _('Opening Balance'),
		'fieldtype': 'float',
		'fieldname': 'opening_balance',
		'width': 120,
	}, {
		'label': _('New Allocation'),
		'fieldtype': 'Float',
		'fieldname': 'new_allocation',
		'width': 120,
	}, {
		'label': _('Expired Leaves'),
		'fieldtype': 'Float',
		'fieldname': 'expired_leaves',
		'width': 120,
	}, {
		'label': _('Leaves Taken'),
		'fieldtype': 'float',
		'fieldname': 'leaves_taken',
		'width': 120,
	}, {
		'label': _('Closing Balance'),
		'fieldtype': 'float',
		'fieldname': 'closing_balance',
		'width': 120,
	}]

	return columns

def get_data(filters):
	leave_types = frappe.db.sql_list("SELECT `name` FROM `tabLeave Type` ORDER BY `name` ASC")

	conditions = get_conditions(filters)

	user = frappe.session.user
	department_approver_map = get_department_leave_approver_map(filters.get('department'))

	active_employees = frappe.get_list('Employee',
		filters=conditions,
		fields=['name', 'employee_name', 'department', 'user_id', 'leave_approver'])

	data = []

	for leave_type in leave_types:
		data.append({
			'leave_type': leave_type
		})
		for employee in active_employees:

			leave_approvers = department_approver_map.get(employee.department_name, []).append(employee.leave_approver)

			if (leave_approvers and len(leave_approvers) and user in leave_approvers) or (user in ["Administrator", employee.user_id]) \
				or ("HR Manager" in frappe.get_roles(user)):
				row = frappe._dict({
					'employee': employee.name,
					'employee_name': employee.employee_name
				})

				leave_details = calculate_leaves_details(filters, leave_type, employee)
				row.opening_balance = flt(leave_details[0])
				row.new_allocation = flt(leave_details[1])
				row.expired_leaves = flt(leave_details[2])
				row.leaves_taken = flt(leave_details[3])
				row.closing_balance = flt(leave_details[4])

				data.append(row)

	return data

def get_conditions(filters):
	conditions={
		'status': 'Active',
	}
	if filters.get('employee'):
		conditions['name'] = filters.get('employee')

	if filters.get('employee'):
		conditions['name'] = filters.get('employee')

	return conditions

