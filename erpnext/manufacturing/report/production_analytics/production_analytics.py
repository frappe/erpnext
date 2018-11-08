# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate
from erpnext.selling.report.sales_analytics.sales_analytics import (get_period_date_ranges,get_period)

def execute(filters=None):
	columns = get_columns(filters)
	data, chart = get_data(filters,columns)
	return columns, data,None ,chart

def get_columns(filters):

	columns =[
		{
			"label": _("Status"),
			"fieldname": "Status",
			"fieldtype": "Data",
			"width": 140
		}]

	ranges = get_period_date_ranges(period=filters["range"], year_start_date = filters["from_date"],year_end_date=filters["to_date"])

	for dummy, end_date in ranges:

		label = field_name = get_period(end_date,filters["range"])

		columns.append(
			{
			"label": _(label),
			"fieldname": field_name,
			"fieldtype": "Float",
			"width": 120
		},
		)

	return columns

def get_data_list(filters,entry):

	data_list = {
		"All Work Orders" : {},
		"Not Started" : {},
		"Overdue" : {},
		"Pending" : {},
		"Completed" : {}
	}

	ranges = get_period_date_ranges(period=filters["range"], year_start_date = filters["from_date"],year_end_date=filters["to_date"])

	for from_date,end_date in ranges:
		period = get_period(end_date,filters["range"])
		for d in entry:
			if getdate(d.creation) <= getdate(from_date) or getdate(d.creation) <= getdate(end_date) :
				data_list = update_data_list(data_list,"All Work Orders",period)

				if d.status == 'Completed':
					if getdate(d.actual_end_date) < getdate(from_date) or getdate(d.modified) < getdate(from_date):
						data_list = update_data_list(data_list, "Completed",period)

					elif getdate(d.actual_start_date) < getdate(from_date) :
						data_list = update_data_list(data_list, "Pending", period)

					elif getdate(d.planned_start_date) < getdate(from_date) :
						data_list = update_data_list(data_list, "Overdue", period)
						
					else:
						data_list = update_data_list(data_list, "Not Started", period)

				elif d.status == 'In Process':
					if getdate(d.actual_start_date) < getdate(from_date) :
						data_list = update_data_list(data_list, "Pending", period)

					elif getdate(d.planned_start_date) < getdate(from_date) :
						data_list = update_data_list(data_list, "Overdue", period)

					else:
						data_list = update_data_list(data_list, "Not Started", period)

				elif d.status == 'Not Started':
					if getdate(d.planned_start_date) < getdate(from_date) :
						data_list = update_data_list(data_list, "Overdue", period)

					else:
						data_list = update_data_list(data_list, "Not Started", period)
	return data_list

def update_data_list(data_list, status, period):
	if data_list.get(status).get(period):
		data_list[status][period] += 1
	else:
		data_list[status][period] = 1

	return data_list

def get_data(filters,columns):

	data = []

	entry = frappe.get_all("Work Order",
		fields=["creation", "modified", "actual_start_date", "actual_end_date", "planned_start_date", "planned_end_date", "status"],
		filters={"docstatus" : 1, "company" : filters["company"] })

	data_list = get_data_list(filters,entry)

	labels = ["All Work Orders", "Not Started", "Overdue", "Pending", "Completed"]

	chart_data = get_chart_data(data_list,columns)

	ranges = get_period_date_ranges(period=filters["range"], year_start_date = filters["from_date"],year_end_date=filters["to_date"])

	for label in labels:
		work = {}
		work["Status"] = label
		for dummy,end_date in ranges:
			period = get_period(end_date,filters["range"])
			if data_list.get(label).get(period):
				work[period] = data_list.get(label).get(period)
			else:
				work[period] = 0.0
		data.append(work)

	return data, chart_data

def get_chart_data(data_list,columns):

	labels = [d.get("label") for d in columns[1:]]

	all_data, not_start, overdue, pending, completed = [], [], [] , [], []
	datasets = []

	for d in labels:
		all_data.append(data_list.get("All Work Orders").get(d))
		not_start.append(data_list.get("Not Started").get(d))
		overdue.append(data_list.get("Overdue").get(d))
		pending.append(data_list.get("Pending").get(d))
		completed.append(data_list.get("Completed").get(d))

	datasets.append({'name':'All Work Orders', 'values': all_data})
	datasets.append({'name':'Not Started', 'values': not_start})
	datasets.append({'name':'Overdue', 'values': overdue})
	datasets.append({'name':'Pending', 'values': pending})
	datasets.append({'name':'Completed', 'values': completed})

	chart = {
		"data": {
			'labels': labels,
			'datasets':datasets
		}
	}

	chart["type"] = "line"

	return chart





