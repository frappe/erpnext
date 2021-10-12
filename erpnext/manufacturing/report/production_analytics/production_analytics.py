# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _, scrub
from frappe.utils import getdate

from erpnext.stock.report.stock_analytics.stock_analytics import get_period, get_period_date_ranges


def execute(filters=None):
	columns = get_columns(filters)
	data, chart = get_data(filters, columns)
	return columns, data, None , chart

def get_columns(filters):
	columns =[
		{
			"label": _("Status"),
			"fieldname": "Status",
			"fieldtype": "Data",
			"width": 140
		}]

	ranges = get_period_date_ranges(filters)

	for dummy, end_date in ranges:

		period = get_period(end_date, filters)

		columns.append({
			"label": _(period),
			"fieldname": scrub(period),
			"fieldtype": "Float",
			"width": 120
		})

	return columns

def get_periodic_data(filters, entry):
	periodic_data = {
		"All Work Orders": {},
		"Not Started": {},
		"Overdue": {},
		"Pending": {},
		"Completed": {}
	}

	ranges = get_period_date_ranges(filters)

	for from_date, end_date in ranges:
		period = get_period(end_date, filters)
		for d in entry:
			if getdate(d.creation) <= getdate(from_date) or getdate(d.creation) <= getdate(end_date) :
				periodic_data = update_periodic_data(periodic_data, "All Work Orders", period)
				if d.status == 'Completed':
					if getdate(d.actual_end_date) < getdate(from_date) or getdate(d.modified) < getdate(from_date):
						periodic_data = update_periodic_data(periodic_data, "Completed", period)
					elif getdate(d.actual_start_date) < getdate(from_date) :
						periodic_data = update_periodic_data(periodic_data, "Pending", period)
					elif getdate(d.planned_start_date) < getdate(from_date) :
						periodic_data = update_periodic_data(periodic_data, "Overdue", period)
					else:
						periodic_data = update_periodic_data(periodic_data, "Not Started", period)

				elif d.status == 'In Process':
					if getdate(d.actual_start_date) < getdate(from_date) :
						periodic_data = update_periodic_data(periodic_data, "Pending", period)
					elif getdate(d.planned_start_date) < getdate(from_date) :
						periodic_data = update_periodic_data(periodic_data, "Overdue", period)
					else:
						periodic_data = update_periodic_data(periodic_data, "Not Started", period)

				elif d.status == 'Not Started':
					if getdate(d.planned_start_date) < getdate(from_date) :
						periodic_data = update_periodic_data(periodic_data, "Overdue", period)
					else:
						periodic_data = update_periodic_data(periodic_data, "Not Started", period)

	return periodic_data

def update_periodic_data(periodic_data, status, period):
	if periodic_data.get(status).get(period):
		periodic_data[status][period] += 1
	else:
		periodic_data[status][period] = 1

	return periodic_data

def get_data(filters, columns):
	data = []
	entry = frappe.get_all("Work Order",
		fields=["creation", "modified", "actual_start_date", "actual_end_date", "planned_start_date", "planned_end_date", "status"],
		filters={"docstatus": 1, "company": filters["company"] })

	periodic_data = get_periodic_data(filters,entry)

	labels = ["All Work Orders", "Not Started", "Overdue", "Pending", "Completed"]
	chart_data = get_chart_data(periodic_data,columns)
	ranges = get_period_date_ranges(filters)

	for label in labels:
		work = {}
		work["Status"] = label
		for dummy,end_date in ranges:
			period = get_period(end_date, filters)
			if periodic_data.get(label).get(period):
				work[scrub(period)] = periodic_data.get(label).get(period)
			else:
				work[scrub(period)] = 0.0
		data.append(work)

	return data, chart_data

def get_chart_data(periodic_data, columns):
	labels = [d.get("label") for d in columns[1:]]

	all_data, not_start, overdue, pending, completed = [], [], [] , [], []
	datasets = []

	for d in labels:
		all_data.append(periodic_data.get("All Work Orders").get(d))
		not_start.append(periodic_data.get("Not Started").get(d))
		overdue.append(periodic_data.get("Overdue").get(d))
		pending.append(periodic_data.get("Pending").get(d))
		completed.append(periodic_data.get("Completed").get(d))

	datasets.append({'name':'All Work Orders', 'values': all_data})
	datasets.append({'name':'Not Started', 'values': not_start})
	datasets.append({'name':'Overdue', 'values': overdue})
	datasets.append({'name':'Pending', 'values': pending})
	datasets.append({'name':'Completed', 'values': completed})

	chart = {
		"data": {
			'labels': labels,
			'datasets': datasets
		}
	}
	chart["type"] = "line"

	return chart
