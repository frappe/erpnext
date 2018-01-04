# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import add_to_date, getdate, get_datetime

time_slots = {
	'12AM - 3AM': '00:00:00-03:00:00',
	'3AM - 6AM': '03:00:00-06:00:00',
	'6AM - 9AM': '06:00:00-09:00:00',
	'9AM - 12PM': '09:00:00-12:00:00',
	'12PM - 3PM': '12:00:00-15:00:00',
	'3PM - 6PM': '15:00:00-18:00:00',
	'6PM - 9PM': '18:00:00-21:00:00',
	'9PM - 12AM': '21:00:00-23:00:00'
}

def execute(filters=None):
	columns, data = [], []
	if not filters.get('periodicity'):
		filters['periodicity'] = 'Daily'

	columns = get_columns()
	data, timeslot_wise_count = get_data(filters)
	chart = get_chart_data(timeslot_wise_count)
	return columns, data, None, chart

def get_data(filters):
	start_date = getdate(filters.from_date)
	data = []
	time_slot_wise_total_count = {}
	while(start_date <= getdate(filters.to_date)):
		hours_count = {'date': start_date}
		for key, value in time_slots.items():
			start_time, end_time = value.split('-')
			start_time = get_datetime("{0} {1}".format(start_date.strftime("%Y-%m-%d"), start_time))
			end_time = get_datetime("{0} {1}".format(start_date.strftime("%Y-%m-%d"), end_time))
			hours_count[key] = get_hours_count(start_time, end_time)
			time_slot_wise_total_count[key] = time_slot_wise_total_count.get(key, 0) + hours_count[key]

		if hours_count:
			data.append(hours_count)

		start_date = add_to_date(start_date, days=1)

	return data, time_slot_wise_total_count

def get_hours_count(start_time, end_time):
	data = frappe.db.sql(""" select count(*) from `tabIssue` where creation
		between %(start_time)s and %(end_time)s""", {
			'start_time': start_time,
			'end_time': end_time
		}, as_list=1) or []

	return data[0][0] if len(data) > 0 else 0

def get_columns():
	columns = [{
		"fieldname": "date",
		"label": _("Date"),
		"fieldtype": "Date",
		"width": 100
	}]

	for label in ['12AM - 3AM', '3AM - 6AM', '6AM - 9AM',
		'9AM - 12PM', '12PM - 3PM', '3PM - 6PM', '6PM - 9PM', '9PM - 12AM']:
		columns.append({
			"fieldname": label,
			"label": _(label),
			"fieldtype": "Data",
			"width": 120
		})

	return columns

def get_chart_data(timeslot_wise_count):
	total_count = []
	timeslots = ['12AM - 3AM', '3AM - 6AM', '6AM - 9AM',
		'9AM - 12PM', '12PM - 3PM', '3PM - 6PM', '6PM - 9PM', '9PM - 12AM']

	datasets = []
	for data in timeslots:
		total_count.append(timeslot_wise_count.get(data, 0))
	datasets.append({'values': total_count})

	chart = {
		"data": {
			'labels': timeslots,
			'datasets': datasets
		}
	}
	chart["type"] = "line"
	return chart
