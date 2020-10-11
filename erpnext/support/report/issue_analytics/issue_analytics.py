# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from six import iteritems
from frappe import _, scrub
from frappe.utils import getdate, flt
from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.report.stock_analytics.stock_analytics import get_period_date_ranges

def execute(filters=None):
	return IssueAnalytics(filters).run()

class IssueAnalytics(object):
	def __init__(self, filters=None):
		"""Issue Analytics Report"""
		self.filters = frappe._dict(filters or {})
		self.periodic_daterange = get_period_date_ranges(self.filters)

	def run(self):
		self.get_columns()
		self.get_data()
		self.get_chart_data()

		chart = []
		return self.columns, self.data, None, self.chart

	def get_columns(self):
		self.columns = []

		if self.filters.based_on == 'Customer':
			self.columns.append({
				'label': _('Customer'),
				'options': 'Customer',
				'fieldname': 'customer',
				'fieldtype': 'Link',
				'width': 200
			})

		elif self.filters.based_on == 'Assigned To':
			self.columns.append({
				'label': _('User'),
				'fieldname': 'user',
				'fieldtype': 'Link',
				'options': 'User',
				'width': 200
			})

		elif self.filters.based_on == 'Issue Type':
			self.columns.append({
				'label': _('Issue Type'),
				'fieldname': 'issue_type',
				'fieldtype': 'Link',
				'options': 'Issue Type',
				'width': 200
			})

		elif self.filters.based_on == 'Issue Priority':
			self.columns.append({
				'label': _('Issue Priority'),
				'fieldname': 'priority',
				'fieldtype': 'Link',
				'options': 'Issue Priority',
				'width': 200
			})

		for entry, end_date in self.periodic_daterange:
			period = self.get_period(end_date)
			self.columns.append({
				'label': _(period),
				'fieldname': scrub(period),
				'fieldtype': 'Int',
				'width': 120
			})

	def get_data(self):
		if self.filters.based_on == 'Customer':
			self.get_customer_wise_issues()

		elif self.filters.based_on == 'Assigned To':
			self.get_assignment_wise_issues()

		elif self.filters.based_on == 'Issue Type':
			self.get_issue_type_wise_issues()

		elif self.filters.based_on == 'Issue Priority':
			self.get_priority_wise_issues()

		self.get_rows()

	def get_period(self, date):
		months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

		if self.filters.range == 'Weekly':
			period = 'Week ' + str(date.isocalendar()[1])
		elif self.filters.range == 'Monthly':
			period = str(months[date.month - 1])
		elif self.filters.range == 'Quarterly':
			period = 'Quarter ' + str(((date.month - 1) // 3) + 1)
		else:
			year = get_fiscal_year(date)
			period = str(year[0])

		return period

	def get_customer_wise_issues(self):
		filters = self.get_common_filters()

		self.entries = frappe.db.get_all('Issue',
			fields=['customer', 'name', 'opening_date'],
			filters=filters
		)

	def get_assignment_wise_issues(self):
		filters = self.get_common_filters()
		self.entries = frappe.db.get_all('Issue',
			fields=['_assign', 'name', 'opening_date'],
			filters=filters
		)

	def get_issue_type_wise_issues(self):
		filters = self.get_common_filters()
		self.entries = frappe.db.get_all('Issue',
			fields=['issue_type', 'name', 'opening_date'],
			filters=filters
		)

	def get_priority_wise_issues(self):
		filters = self.get_common_filters()
		self.entries = frappe.db.get_all('Issue',
			fields=['priority', 'name', 'opening_date'],
			filters=filters
		)

	def get_common_filters(self):
		filters = {}
		filters['opening_date'] = ('between', [self.filters.from_date, self.filters.to_date])

		return filters

	def get_rows(self):
		self.data = []
		self.get_periodic_data()

		for entity, period_data in iteritems(self.issue_periodic_data):
			if self.filters.based_on == 'Customer':
				row = {'customer': entity}
			elif self.filters.based_on == 'Assigned To':
				row = {'user': entity}
			elif self.filters.based_on == 'Issue Type':
				row = {'issue_type': entity}
			elif self.filters.based_on == 'Issue Priority':
				row = {'priority': entity}

			total = 0
			for entry, end_date in self.periodic_daterange:
				period = self.get_period(end_date)
				amount = flt(period_data.get(period, 0.0))
				row[scrub(period)] = amount
				total += amount

			row['total'] = total

			self.data.append(row)

	def get_periodic_data(self):
		self.issue_periodic_data = frappe._dict()

		for d in self.entries:
			period = self.get_period(d.get('opening_date'))
			if self.filters.based_on == 'Customer':
				self.issue_periodic_data.setdefault(d.customer, frappe._dict()).setdefault(period, 0.0)
				self.issue_periodic_data[d.customer][period] += 1

			elif self.filters.based_on == 'Assigned To':
				if d._assign:
					for entry in json.loads(d._assign):
						self.issue_periodic_data.setdefault(entry, frappe._dict()).setdefault(period, 0.0)
						self.issue_periodic_data[entry][period] += 1

			elif self.filters.based_on == 'Issue Type':
				self.issue_periodic_data.setdefault(d.issue_type, frappe._dict()).setdefault(period, 0.0)
				self.issue_periodic_data[d.issue_type][period] += 1

			elif self.filters.based_on == 'Issue Priority':
				self.issue_periodic_data.setdefault(d.priority, frappe._dict()).setdefault(period, 0.0)
				self.issue_periodic_data[d.priority][period] += 1

	def get_chart_data(self):
		length = len(self.columns)
		labels = [d.get('label') for d in self.columns[1:length]]
		self.chart = {
			'data': {
				'labels': labels,
				'datasets': []
			},
			'type': 'line'
		}