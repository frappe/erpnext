# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate
from six import iteritems

def execute(filters=None):
	return EmployeeHoursReport(filters).run()

class EmployeeHoursReport:
	'''Employee Hours Utilisation Report Based On Timesheet'''
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})

		self.from_date = getdate(self.filters.from_date)
		self.to_date = getdate(self.filters.to_date)

		self.validate_dates()
	
	def validate_dates(self):
		self.day_span = (self.to_date - self.from_date).days

		if self.day_span < 0:
			frappe.throw(_('From Date must come before To Date'))

	def run(self):
		self.generate_columns()
		self.generate_data()
		self.generate_report_summary()
		self.generate_chart_data()

		return self.columns, self.data, None, self.chart, self.report_summary

	def generate_columns(self):
		self.columns = [
			{
				'label': _('Employee'),
				'options': 'Employee',
				'fieldname': 'employee',
				'fieldtype': 'Link',
				'width': 200
			},
			{
				'label': _('Total Hours'),
				'fieldname': 'total_hours',
				'fieldtype': 'Float',
				'width': 150
			},
			{
				'label': _('Billed Hours'),
				'fieldname': 'billed_hours',
				'fieldtype': 'Float',
				'width': 150
			},
			{
				'label': _('Non-Billed Hours'),
				'fieldname': 'non_billed_hours',
				'fieldtype': 'Float',
				'width': 150
			},
			{
				'label': _('Untracked Hours'),
				'fieldname': 'untracked_hours',
				'fieldtype': 'Float',
				'width': 150
			},
			{
				'label': _('% Utilization'),
				'fieldname': 'per_util',
				'fieldtype': 'Percentage',
				'width': 200
			}
		]
	
	def generate_data(self):
		self.generate_filtered_time_logs()
		self.generate_stats_by_employee()
		self.calculate_utilisations()

		self.data = []

		for emp, data in iteritems(self.stats_by_employee):
			row = frappe._dict()
			row['employee'] = emp
			row.update(data)
			self.data.append(row)

		#  Sort by descending order of percentage utilisation
		self.data.sort(key=lambda x: x['per_util'], reverse=True)

	def generate_filtered_time_logs(self):
		additional_filters = ''

		if self.filters.employee:
			additional_filters += f"AND tt.employee = '{self.filters.employee}'"
		
		if self.filters.project:
			additional_filters += f"AND ttd.project = '{self.filters.project}'"

		if self.filters.company:
			additional_filters += f"AND tt.company = '{self.filters.company}'"

		self.filtered_time_logs = frappe.db.sql('''
			SELECT tt.employee AS employee, ttd.hours AS hours, ttd.billable AS billable, ttd.project AS project
			FROM `tabTimesheet Detail` AS ttd 
			JOIN `tabTimesheet` AS tt 
				ON ttd.parent = tt.name
			WHERE tt.start_date BETWEEN '{0}' AND '{1}'
			AND tt.end_date BETWEEN '{0}' AND '{1}'
			{2};  
		'''.format(self.filters.from_date, self.filters.to_date, additional_filters))

	def generate_stats_by_employee(self):
		self.stats_by_employee = frappe._dict()

		for emp, hours, billable, project in self.filtered_time_logs:
			self.stats_by_employee.setdefault(
				emp, frappe._dict()
			).setdefault('billed_hours', 0.0)

			self.stats_by_employee[emp].setdefault('non_billed_hours', 0.0)

			if billable:
				self.stats_by_employee[emp]['billed_hours'] += flt(hours, 2)
			else:
				self.stats_by_employee[emp]['non_billed_hours'] += flt(hours, 2)

	def calculate_utilisations(self):
		# (9.0) Will be fetched from HR settings
		TOTAL_HOURS = flt(9.0 * self.day_span, 2)
		for emp, data in iteritems(self.stats_by_employee):
			data['total_hours'] = TOTAL_HOURS
			data['untracked_hours'] = flt(TOTAL_HOURS - data['billed_hours'] - data['non_billed_hours'], 2)

			# To handle overtime edge-case
			if data['untracked_hours'] < 0:
				data['untracked_hours'] = 0.0
				
			data['per_util'] = flt(((data['billed_hours'] + data['non_billed_hours']) / TOTAL_HOURS) * 100, 2)
	
	def generate_report_summary(self):
		self.report_summary = []

		if not self.data:
			return 

		avg_utilisation = 0.0
		total_billed, total_non_billed = 0.0, 0.0
		total_untracked = 0.0

		for row in self.data:
			avg_utilisation += row['per_util']
			total_billed += row['billed_hours']
			total_non_billed += row['non_billed_hours']
			total_untracked += row['untracked_hours']

		avg_utilisation /= len(self.data)
		avg_utilisation = flt(avg_utilisation, 2)

		THRESHOLD_PERCENTAGE = 70.0
		self.report_summary = [
			{
				'value': f'{avg_utilisation}%',
				'indicator': 'Red' if avg_utilisation < THRESHOLD_PERCENTAGE else 'Green',
				'label': _('Average Utilisation'),
				'datatype': 'Percentage'
			},
			{
				'value': total_billed,
				'label': _('Total Billed Hours'),
				'datatype': 'Float'
			},
			{
				'value': total_non_billed,
				'label': _('Total Non-Billed Hours'),
				'datatype': 'Float'
			},
			{
				'value': total_untracked,
				'label': _('Total Untracked Hours'),
				'datatype': 'Float'
			}
		]

	def generate_chart_data(self):
		self.chart = {}

		labels = []
		billed_hours = []
		non_billed_hours = []
		untracked_hours = []


		for row in self.data:
			emp_name = frappe.db.get_value(
				'Employee', row['employee'], 'employee_name'
			)
			labels.append(emp_name)
			billed_hours.append(row.get('billed_hours'))
			non_billed_hours.append(row.get('non_billed_hours'))
			untracked_hours.append(row.get('untracked_hours'))
		
		self.chart = {
			'data': {
				'labels': labels[:30],
				'datasets': [
					{
						'name': _('Billed Hours'),
						'values': billed_hours[:30]
					},
					{
						'name': _('Non-Billed Hours'),
						'values': non_billed_hours[:30]
					},
					{
						'name': _('Untracked Hours'),
						'values': untracked_hours[:30]
					}
				]
			},
			'type': 'bar',
			'barOptions': {
				'stacked': True
			}
		}
