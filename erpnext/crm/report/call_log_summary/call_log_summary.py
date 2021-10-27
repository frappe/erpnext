# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# License: MIT. See LICENSE

import frappe
from frappe import _
from frappe.utils import getdate, cint, add_months, add_days, formatdate, get_datetime
import math
import json
from datetime import date
from dateutil.relativedelta import relativedelta

def execute(filters=None):
	return CallLogSummary(filters).run()
	columns, data = [], []
	return columns, data

class CallLogSummary():
	def __init__(self, filters):
		self.filters = frappe._dict(filters or {})

	def run(self):
		self.validate_filters()
		columns = self.get_columns()
		data = self.prepare_data_and_column(columns, self.get_data())
		chart = self.get_chart_data(columns, data)
		columns.insert(0, {
            'fieldname': 'user',
            'label': _('{0} Owner').format(self.filters.reference_document_type),
            'fieldtype': 'Link',
            'options': 'User',
			'width': 200
        })

		print("``````````````````````````````")
		print(chart)
		print("``````````````````````````````")
		return columns, data, None, chart

	def get_columns(self):
		return self.get_period_list()

	def get_data(self):
		return frappe.db.sql(self.get_query(), as_dict=True)

	def get_chart_data(self, columns, data):
		labels = ['Jan', 'Feb', 'Mar']
		datasets = [
			{ 'values': [18, 40, 30] }
		]
		chart = {
			'data':{
				'labels': labels,
				'datasets': datasets
			},
			'type':'bar'
		}
		return chart

	def get_query(self):
		filters = self.filters

		join_field = """dl.parenttype = 'Call Log' 
			AND dl.link_doctype = '{0}' 
			AND cl.name = dl.parent 
			AND (cl.creation BETWEEN '{1}' AND '{2}')
			""".format(filters.reference_document_type, filters.from_date, filters.to_date)

		if filters.reference_document_name:
			join_field += " AND dl.link_name = '{0}'".format(filters.reference_document_name)

		if filters.type:
			join_field += " AND cl.type = '{0}'".format(filters.type)

		if len(filters.status):
			join_field += " AND cl.status IN ('{0}')".format("','".join(filters.status))

		join = "dt.name = dl.link_name"

		if filters.company:
			join += " AND dt.company = '{0}'".format(filters.company)

		query = """SELECT cl.type as type, 
			cl.status as status, 
			DATE(cl.creation) as creation, 
			dt._assign as assign, 
			dt.name as name
    		FROM ((`tabDynamic Link` dl 
			INNER JOIN `tabCall Log` cl ON {0})
    		INNER JOIN `tab{1}` dt ON {2})
			""".format(join_field, filters.reference_document_type, join)

		return query

	def prepare_data_and_column(self, columns, data):
		period_dict = dict()
		for column in columns:
			period_dict[column.fieldname] = 0

		prepared_data = frappe._dict()
		
		for row in data:
			for user in json.loads(row.assign):
				if user not in prepared_data:
					prepared_data[user] = period_dict.copy()
					prepared_data[user]['user'] = user
				for column in columns:
					if column.from_date <= row.creation <= column.to_date:
						prepared_data[user][column.fieldname] = prepared_data[user][column.fieldname] + 1 
						break

		data = []
		for row in prepared_data:
			data.append(prepared_data[row])
		# print(data)
		return data

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

			to_date = add_days(to_date, -1)

			if to_date <= year_end_date:
				period.to_date = to_date
				period_list.append(period)

		# updating column fields
		for opts in period_list:
			fieldname = opts.to_date.strftime("%b_%Y").lower()
			if self.filters.frequency == "Monthly":
				label = formatdate(opts.to_date, "MMM YYYY")
			else:
				label = self.get_label(self.filters.frequency, opts.from_date, opts.to_date)

			opts.update({
				"fieldname": fieldname.replace(" ", "_").replace("-", "_"),
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