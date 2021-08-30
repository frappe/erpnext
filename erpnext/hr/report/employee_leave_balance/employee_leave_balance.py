# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, add_days
from frappe import _
from erpnext.hr.doctype.leave_application.leave_application import get_leaves_for_period, get_leave_balance_on
from itertools import groupby

def execute(filters=None):
	if filters.to_date <= filters.from_date:
		frappe.throw(_('"From Date" can not be greater than or equal to "To Date"'))

	columns = get_columns()
	data = get_data(filters)
	charts = get_chart_data(data)
	return columns, data, None, charts

def get_columns():
	columns = [{
		'label': _('Leave Type'),
		'fieldtype': 'Link',
		'fieldname': 'leave_type',
		'width': 200,
		'options': 'Leave Type'
	}, {
		'label': _('Employee'),
		'fieldtype': 'Link',
		'fieldname': 'employee',
		'width': 100,
		'options': 'Employee'
	}, {
		'label': _('Employee Name'),
		'fieldtype': 'Dynamic Link',
		'fieldname': 'employee_name',
		'width': 100,
		'options': 'employee'
	}, {
		'label': _('Opening Balance'),
		'fieldtype': 'float',
		'fieldname': 'opening_balance',
		'width': 130,
	}, {
		'label': _('Leave Allocated'),
		'fieldtype': 'float',
		'fieldname': 'leaves_allocated',
		'width': 130,
	}, {
		'label': _('Leave Taken'),
		'fieldtype': 'float',
		'fieldname': 'leaves_taken',
		'width': 130,
	}, {
		'label': _('Leave Expired'),
		'fieldtype': 'float',
		'fieldname': 'leaves_expired',
		'width': 130,
	}, {
		'label': _('Closing Balance'),
		'fieldtype': 'float',
		'fieldname': 'closing_balance',
		'width': 130,
	}]

	return columns

def get_data(filters):
	leave_types = frappe.db.get_list('Leave Type', pluck='name', order_by='name')
	conditions = get_conditions(filters)

	user = frappe.session.user
	department_approver_map = get_department_leave_approver_map(filters.get('department'))

	active_employees = frappe.get_list('Employee',
		filters=conditions,
		fields=['name', 'employee_name', 'department', 'user_id', 'leave_approver'])

	data = []

	for leave_type in leave_types:
		if len(active_employees) > 1:
			data.append({
				'leave_type': leave_type
			})
		else:
			row = frappe._dict({
				'leave_type': leave_type
			})

		for employee in active_employees:

			leave_approvers = department_approver_map.get(employee.department_name, []).append(employee.leave_approver)

			if (leave_approvers and len(leave_approvers) and user in leave_approvers) or (user in ["Administrator", employee.user_id]) \
				or ("HR Manager" in frappe.get_roles(user)):
				if len(active_employees) > 1:
					row = frappe._dict()
				row.employee = employee.name,
				row.employee_name = employee.employee_name

				leaves_taken = get_leaves_for_period(employee.name, leave_type,
					filters.from_date, filters.to_date) * -1

				new_allocation, expired_leaves = get_allocated_and_expired_leaves(filters.from_date, filters.to_date, employee.name, leave_type)


				opening = get_leave_balance_on(employee.name, leave_type, add_days(filters.from_date, -1)) #allocation boundary condition

				row.leaves_allocated = new_allocation
				row.leaves_expired = expired_leaves - leaves_taken if expired_leaves - leaves_taken > 0 else 0
				row.opening_balance = opening
				row.leaves_taken = leaves_taken

				# not be shown on the basis of days left it create in user mind for carry_forward leave
				row.closing_balance = (new_allocation + opening - (row.leaves_expired + leaves_taken))
				row.indent = 1
				data.append(row)

	return data

def get_conditions(filters):
	conditions={
		'status': 'Active',
	}
	if filters.get('employee'):
		conditions['name'] = filters.get('employee')

	if filters.get('company'):
		conditions['company'] = filters.get('company')

	if filters.get('department'):
		conditions['department'] = filters.get('department')

	return conditions

def get_department_leave_approver_map(department=None):

	# get current department and all its child
	department_list = frappe.get_list('Department',
						filters={
							'disabled': 0
						},
						or_filters={
							'name': department,
							'parent_department': department
						},
						fields=['name'],
						pluck='name'
					)
	# retrieve approvers list from current department and from its subsequent child departments
	approver_list = frappe.get_all('Department Approver',
						filters={
							'parentfield': 'leave_approvers',
							'parent': ('in', department_list)
						},
						fields=['parent', 'approver'],
						as_list=1
					)

	approvers = {}

	for k, v in approver_list:
		approvers.setdefault(k, []).append(v)

	return approvers

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

	for record in records:
		if record.to_date < getdate(to_date):
			expired_leaves += record.leaves

		if record.from_date >= getdate(from_date):
			new_allocation += record.leaves

	return new_allocation, expired_leaves

def get_chart_data(data):
	labels = []
	datasets = []
	employee_data = data

	if data and data[0].get('employee_name'):
		get_dataset_for_chart(employee_data, datasets, labels)

	chart = {
		'data': {
			'labels': labels,
			'datasets': datasets
		},
		'type': 'bar',
		'colors': ['#456789', '#EE8888', '#7E77BF']
	}

	return chart

def get_dataset_for_chart(employee_data, datasets, labels):
	leaves = []
	employee_data = sorted(employee_data, key=lambda k: k['employee_name'])

	for key, group in groupby(employee_data, lambda x: x['employee_name']):
		for grp in group:
			if grp.closing_balance:
				leaves.append(frappe._dict({
					'leave_type': grp.leave_type,
					'closing_balance': grp.closing_balance
				}))

		if leaves:
			labels.append(key)

	for leave in leaves:
		datasets.append({'name': leave.leave_type, 'values': [leave.closing_balance]})
