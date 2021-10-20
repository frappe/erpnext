# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# License: MIT. See LICENSE

import frappe
from frappe import _
from frappe.utils import getdate, cint, add_months, add_days, formatdate
import math

from datetime import date
from dateutil.relativedelta import relativedelta

def execute(filters=None):
	print("`````````````````````````````````")
	print(filters)
	print("`````````````````````````````````")
	return CallLogSummary(filters).run()
	columns, data = [], []
	return columns, data

class CallLogSummary():
	def __init__(self, filters):
		
		self.filters = frappe._dict(filters or {})

	def run(self):
		self.validate_filters()
		self.get_columns()
		# self.get_data()
		# self.get_chart_data()

		return [], []

	def get_columns(self):
		print(self.get_period_list())
		pass

	def get_data(self):
		pass

	def validate_filters(self):
		if not self.filters.from_date or not self.filters.to_date:
			frappe.throw(_("{0} and {1} are mandatory").format(frappe.bold("From Date"), frappe.bold("To Date")))

		if self.filters.to_date < self.filters.from_date:
			frappe.throw(_("{0} cannot be less than {1}").format(frappe.bold("To Date"), frappe.bold("From Date")))

	def get_period_list(self):
		year_start_date = getdate(self.filters.from_date)
		year_end_date = getdate(self.filters.to_date)

		months_to_add = {
			"Yearly": 12,
			"Half-Yearly": 6,
			"Quarterly": 3,
			"Monthly": 1
		}[self.filters.frequency]

		period_list = []

		start_date = year_start_date
		months = self.get_months(year_start_date, year_end_date)

		for i in range(cint(math.ceil(months / months_to_add))):
			period = frappe._dict({
				"from_date": start_date
			})

			to_date = add_months(start_date, months_to_add)
			start_date = to_date

			# Subtract one day from to_date, as it may be first day in next fiscal year or month
			to_date = add_days(to_date, -1)

			if to_date <= year_end_date:
				# the normal case
				period.to_date = to_date
			else:
				# if a fiscal year ends before a 12 month period
				period.to_date = year_end_date

			period_list.append(period)

			if period.to_date == year_end_date:
				break

		# common processing
		for opts in period_list:
			key = opts.to_date.strftime("%b_%Y").lower()
			if self.filters.frequency == "Monthly":
				label = formatdate(opts.to_date, "MMM YYYY")
			else:
				label = get_label(self.filters.frequency, opts.from_date, opts.to_date)

			opts.update({
				"key": key.replace(" ", "_").replace("-", "_"),
				"label": label,
				"year_start_date": year_start_date,
				"year_end_date": year_end_date
			})

		return period_list

	def get_label(self, frequency, from_date, to_date):
		if frequency == "Yearly":
			if formatdate(from_date, "YYYY") == formatdate(to_date, "YYYY"):
				label = formatdate(from_date, "YYYY")
			else:
				label = formatdate(from_date, "YYYY") + "-" + formatdate(to_date, "YYYY")
		else:
			label = formatdate(from_date, "MMM YY") + "-" + formatdate(to_date, "MMM YY")

		return label

	def get_months(self, start_date, end_date):
		diff = (12 * end_date.year + end_date.month) - (12 * start_date.year + start_date.month)
		return diff + 1

	def get_month_list(self):
		month_list= []
		current_date = date.today()
		month_number = date.today().month

		for month in range(month_number,13):
			month_list.append(current_date.strftime('%B'))
			current_date = current_date + relativedelta(months=1)

		return month_list