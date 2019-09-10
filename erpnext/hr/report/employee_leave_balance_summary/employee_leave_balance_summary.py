# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
from erpnext.hr.doctype.leave_application.leave_application import get_leaves_for_period

from erpnext.hr.report.employee_leave_balance.employee_leave_balance import get_total_allocated_leaves

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
		'width': 160,
	}, {
		'label': _('Leaves Taken'),
		'fieldtype': 'float',
		'fieldname': 'leaves_taken',
		'width': 160,
	}, {
		'label': _('Closing Balance'),
		'fieldtype': 'float',
		'fieldname': 'closing_balance',
		'width': 160,
	}]

	return columns

def get_data(filters):
	leave_types = frappe.db.sql_list("SELECT `name` FROM `tabLeave Type` ORDER BY `name` ASC")

	conditions = {
		'status': 'Active',
	}

	if filters.get('employee'):
		conditions['name'] = filters.get('employee')

	active_employees = frappe.get_all('Employee',
		filters=conditions,
		fields=['name', 'employee_name', 'department', 'user_id'])

	data = []

	for leave_type in leave_types:
		data.append({
			'leave_type': leave_type
		})
		for employee in active_employees:
			row = frappe._dict({
				'employee': employee.name,
				'employee_name': employee.employee_name
			})

			leaves_taken = get_leaves_for_period(employee.name, leave_type,
				filters.from_date, filters.to_date) * -1

			opening = get_total_allocated_leaves(employee.name, leave_type, filters.from_date, filters.to_date)
			closing = flt(opening) - flt(leaves_taken)

			row.opening_balance = opening
			row.leaves_taken = leaves_taken
			row.closing_balance = closing
			row.indent = 1
			data.append(row)

	return data
