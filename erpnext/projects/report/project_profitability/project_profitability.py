# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe

def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns()
	charts = get_chart_data(data)
	return columns, data, None, charts

def get_data(filters):
	conditions = get_conditions(filters)
	standard_working_hours = frappe.db.get_single_value('HR Settings', 'standard_working_hours')
	sql = ''' 
			SELECT 
				*
			FROM 
				(SELECT
					si.customer_name,tabTimesheet.title,
					tabTimesheet.employee,si.base_grand_total
					si.name as voucher_no,ss.base_gross_pay,ss.total_working_days,
					tabTimesheet.end_date,tabTimesheet.total_billed_hours,
					tabTimesheet.name as timesheet,
					tabTimesheet.total_billed_hours/(ss.total_working_days * {0}) as utilization
					FROM 
						`tabSalary Slip Timesheet` as sst join `tabTimesheet` on tabTimesheet.name = sst.time_sheet
						join `tabSales Invoice Timesheet` as sit on sit.time_sheet = tabTimesheet.name
						join `tabSales Invoice` as si on si.name = sit.parent and si.status != 'Cancelled'
						join `tabSalary Slip` as ss on ss.name = sst.parent and ss.status != 'Cancelled' '''.format(standard_working_hours)
	if conditions:
		sql += '''
				where
					{0}) as t'''.format(conditions)
	data = frappe.db.sql(sql,filters, as_dict=True)
	data = perform_calculations(data)
	return data

def perform_calculations(data):
	data.fractional_cost = data.base_gross_pay * data.utilization
	data.profit = data.base_grand_total - data.base_gross_pay
	return data

def get_conditions(filters):
	conditions = []
	if filters.get('company'):
		conditions.append('tabTimesheet.company="{0}"'.format(filters.get('company')))
	if filters.get('customer_name'):
		conditions.append('si.customer_name="{0}"'.format(filters.get('customer_name')))
	if filters.get('start_date'):
		conditions.append('tabTimesheet.start_date>="{0}"'.format(filters.get('start_date')))
	if filters.get('end_date'):
		conditions.append('tabTimesheet.end_date<="{0}"'.format(filters.get('end_date')))
	if filters.get('employee'):
		conditions.append('tabTimesheet.employee="{0}"'.format(filters.get('employee')))
	
	conditions = ' and '.join(conditions)
	return conditions

def get_chart_data(data):
	if not data:
		return None

	labels = []
	utilization = []

	for entry in data:
		labels.append(entry.get('title') + ' - ' + str(entry.get('end_date')))
		utilization.append(entry.get('utilization'))
	charts = {
		'data': {
			'labels': labels,
			'datasets': [
				{
					'name': 'Utilization',
					'values': utilization
				}
			]
		},
		'type': 'bar',
		'colors': ['#84BDD5']
	}
	return charts

def get_columns():
	return [
		{
			'fieldname': 'customer_name',
			'label': _('Customer'),
			'fieldtype': 'Link',
			'options': 'Customer',
			'width': 150
		},
		{
			'fieldname': 'employee',
			'label': _('Employee'),
			'fieldtype': 'Link',
			'options': 'Employee',
			'width': 150
		},
		{
			'fieldname': 'employee_name',
			'label': _('Employee Name'),
			'fieldtype': 'Data',
			'width': 120
		},
		{
			'fieldname': 'voucher_no',
			'label': _('Sales Invoice'),
			'fieldtype': 'Link',
			'options': 'Sales Invoice',
			'width': 200
		},
		{
			'fieldname': 'timesheet',
			'label': _('Timesheet'),
			'fieldtype': 'Link',
			'options': 'Timesheet',
			'width': 150
		},
		{
			'fieldname': 'grand_total',
			'label': _('Bill Amount'),
			'fieldtype': 'Currency',
			'options': 'currency',
			'width': 120
		},
		{
			'fieldname': 'gross_pay',
			'label': _('Cost'),
			'fieldtype': 'Currency',
			'options': 'currency',
			'width': 120
		},
		{
			'fieldname': 'profit',
			'label': _('Profit'),
			'fieldtype': 'Currency',
			'options': 'currency',
			'width': 120
		},
		{
			'fieldname': 'utilization',
			'label': _('Utilization'),
			'fieldtype': 'Percentage',
			'width': 120
		},
		{
			'fieldname': 'fractional_cost',
			'label': _('Fractional Cost'),
			'fieldtype': 'Int',
			'width': 100
		},
		{
			'fieldname': 'total_billed_hours',
			'label': _('Total Billed Hours'),
			'fieldtype': 'Int',
			'width': 100
		},
		{
			'fieldname': 'start_date',
			'label': _('Start Date'),
			'fieldtype': 'Date',
			'width': 120
		},
		{
			'fieldname': 'end_date',
			'label': _('End Date'),
			'fieldtype': 'Date',
			'width': 120
		}
	]
