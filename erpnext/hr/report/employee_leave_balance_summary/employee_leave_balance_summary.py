# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
from erpnext.hr.doctype.leave_application.leave_application \
	import get_leave_balance_on, get_leaves_for_period

from erpnext.hr.report.employee_leave_balance.employee_leave_balance \
	import get_total_allocated_leaves

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)

	return columns, data

def get_columns():
	columns = []
	columns.append(_('Leave Type') )
	columns.append(_('Employee'))
	columns.append(_('Employee Name'))
	columns.append(_('Opening Balance') + ':Float:160')
	columns.append(_('Leaves Taken') + ':Float:160')
	columns.append(_('Closing Balance') + ':Float:160')

	return columns

def get_data(filters):
	leave_types = frappe.db.sql_list("SELECT `name` FROM `tabLeave Type` ORDER BY `name` ASC")

	if filters.to_date <= filters.from_date:
		frappe.throw(_('From date can not be greater than than To date'))

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
		for employee in active_employees:
			row = [leave_type, employee.name, employee.employee_name]

			leaves_taken = get_leaves_for_period(employee.name, leave_type,
				filters.from_date, filters.to_date) * -1

			opening = get_total_allocated_leaves(employee.name, leave_type, filters.from_date, filters.to_date)
			closing = flt(opening) - flt(leaves_taken)

			row += [opening, leaves_taken, closing]
			data.append(row)

	return data
