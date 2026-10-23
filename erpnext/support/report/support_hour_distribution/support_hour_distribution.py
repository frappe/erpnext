# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, getdate

# start of each three hour slot
time_slots = {
	"12AM - 3AM": "00:00:00",
	"3AM - 6AM": "03:00:00",
	"6AM - 9AM": "06:00:00",
	"9AM - 12PM": "09:00:00",
	"12PM - 3PM": "12:00:00",
	"3PM - 6PM": "15:00:00",
	"6PM - 9PM": "18:00:00",
	"9PM - 12AM": "21:00:00",
}


def execute(filters=None):
	columns, data = [], []
	if not filters.get("periodicity"):
		filters["periodicity"] = "Daily"

	columns = get_columns()
	data, timeslot_wise_count = get_data(filters)
	chart = get_chart_data(timeslot_wise_count)
	return columns, data, None, chart


def get_data(filters):
	start_date = getdate(filters.from_date)
	data = []
	time_slot_wise_total_count = {}
	while start_date <= getdate(filters.to_date):
		hours_count = {"date": start_date}
		for key, value in time_slots.items():
			start_time = get_datetime("{} {}".format(start_date.strftime("%Y-%m-%d"), value))
			end_time = add_to_date(start_time, hours=3)
			hours_count[key] = get_hours_count(start_time, end_time, filters.get("company"))
			time_slot_wise_total_count[key] = time_slot_wise_total_count.get(key, 0) + hours_count[key]

		if hours_count:
			data.append(hours_count)

		start_date = add_to_date(start_date, days=1)

	return data, time_slot_wise_total_count


def get_hours_count(start_time, end_time, company=None):
	filters = [["creation", ">=", start_time], ["creation", "<", end_time]]
	if company:
		filters.append(["company", "=", company])

	return frappe.get_list("Issue", filters=filters, fields=[{"COUNT": "*", "as": "count"}])[0].count


def get_columns():
	columns = [{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 100}]

	for label in [
		"12AM - 3AM",
		"3AM - 6AM",
		"6AM - 9AM",
		"9AM - 12PM",
		"12PM - 3PM",
		"3PM - 6PM",
		"6PM - 9PM",
		"9PM - 12AM",
	]:
		columns.append({"fieldname": label, "label": _(label), "fieldtype": "Data", "width": 120})

	return columns


def get_chart_data(timeslot_wise_count):
	total_count = []
	timeslots = [
		"12AM - 3AM",
		"3AM - 6AM",
		"6AM - 9AM",
		"9AM - 12PM",
		"12PM - 3PM",
		"3PM - 6PM",
		"6PM - 9PM",
		"9PM - 12AM",
	]

	datasets = []
	for data in timeslots:
		total_count.append(timeslot_wise_count.get(data, 0))
	datasets.append({"values": total_count})

	chart = {"data": {"labels": timeslots, "datasets": datasets}}
	chart["type"] = "line"
	return chart
