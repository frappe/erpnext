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
			"field_name":field_name,
			"fieldtype": "Data",
			"width": 120
		},
		)

	return columns

def get_data_list(filters,entry):

	data_list = {}

	data_list.setdefault("all_work_orders",{})
	data_list.setdefault("not_started",{})
	data_list.setdefault("overdue",{})
	data_list.setdefault("pending",{})
	data_list.setdefault("completed",{})

	ranges = get_period_date_ranges(period=filters["range"], year_start_date = filters["from_date"],year_end_date=filters["to_date"])

	for from_date,end_date in ranges:
		period = get_period(end_date,filters["range"])
		for d in entry:
			if getdate(d.creation) <= getdate(from_date) or getdate(d.creation) <= getdate(end_date) :
				if data_list.get("all_work_orders").get(period):
					data_list["all_work_orders"][period] += 1
				else:
					data_list["all_work_orders"][period] = 1

				if d.status == 'Completed':
					if getdate(d.actual_end_date) < getdate(from_date) or getdate(d.modified) < getdate(from_date):
						if data_list.get("completed").get(period):
							data_list["completed"][period] += 1
						else:
							data_list["completed"][period] = 1
					elif getdate(d.actual_start_date) < getdate(from_date) :
						if data_list.get("pending").get(period):
							data_list["pending"][period] += 1
						else:
							data_list["pending"][period] = 1
					elif getdate(d.planned_start_date) < getdate(from_date) :
						if data_list.get("overdue").get(period):
							data_list["overdue"][period] += 1
						else:
							data_list["overdue"][period] = 1
					else:
						if data_list.get("not_started").get(period):
							data_list["not_started"][period] += 1
						else:
							data_list["not_started"][period] = 1

				elif d.status == 'In Process':
					if getdate(d.actual_start_date) < getdate(from_date):
						if data_list.get("pending").get(period):
							data_list["pending"][period] += 1
						else:
							data_list["pending"][period] = 1
					elif getdate(d.planned_start_date) < getdate(from_date):
						if data_list.get("overdue").get(period):
							data_list["overdue"][period] += 1
						else:
							data_list["overdue"][period] = 1
					else:
						if data_list.get("not_started").get(period):
							data_list["not_started"][period] += 1
						else:
							data_list["not_started"][period] = 1

				elif d.status == 'Not Started':
					if getdate(d.planned_start_date) < getdate(from_date):
						if data_list.get("overdue").get(period):
							data_list["overdue"][period] += 1
						else:
							data_list["overdue"][period] = 1
					else:
						if data_list.get("not_started").get(period):
							data_list["not_started"][period] += 1
						else:
							data_list["not_started"][period] = 1

	return data_list



def get_data(filters,columns):

	data = []

	entry = frappe.get_all("Work Order",
					fields=["creation", "modified", "actual_start_date", "actual_end_date", "planned_start_date", "planned_end_date", "status"],
					filters={"docstatus" : 1, "company" : filters["company"] })

	data_list = get_data_list(filters,entry)

	labels = [
		{
			"name":"All Work Orders",
			"fieldname":"all_work_orders"
		},
		{
			"name":"Not Started",
			"fieldname":"not_started"
		},
		{
			"name":"Overdue(Not Started)",
			"fieldname":"overdue"
		},
		{
			"name":"Pending",
			"fieldname":"pending"
		},
		{
			"name":"Completed",
			"fieldname":"completed"
		},
	]

	chart_data = get_chart_data(data_list,columns)

	ranges = get_period_date_ranges(period=filters["range"], year_start_date = filters["from_date"],year_end_date=filters["to_date"])

	for label in labels:
		work = {}
		work["Status"] = label.get("name")
		for dummy,end_date in ranges:
			period = get_period(end_date,filters["range"])
			if data_list.get(label.get("fieldname")).get(period):
				work[period] = data_list.get(label.get("fieldname")).get(period)
			else:
				work[period] = 0.0
		data.append(work)

	return data, chart_data

def get_chart_data(data_list,columns):

	labels = [d.get("label") for d in columns[1:]]

	all_data, not_start, overdue, pending, completed = [], [], [] , [], []
	datasets = []

	for d in labels:
		all_data.append(data_list.get("all_work_orders").get(d))
		not_start.append(data_list.get("not_started").get(d))
		overdue.append(data_list.get("overdue").get(d))
		pending.append(data_list.get("pending").get(d))
		completed.append(data_list.get("completed").get(d))

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





