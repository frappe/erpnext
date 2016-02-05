# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_employees(filters)
	return columns, data


def get_columns():
	return [
		_("Employee") + ":Link/Employee:120",
		_("Name") + ":Data:200",
		_("Date") + ":Date:100",
		_("Status") + ":Data:70",
		_("Holiday") + ":Data:200"
	]


def get_employees(filters):
	holidays = frappe.get_all("Holiday", fields=["holiday_date", "description"],
				filters=[["holiday_date", ">=",
				filters.from_date],
				["holiday_date", "<=", filters.to_date]])
	holiday_names = {}
	holidays_list = []

	for holiday in holidays:
		holidays_list.append(holiday.holiday_date)
		holiday_names[holiday.holiday_date] = holiday.description
	if(holidays_list):
		employee_list = frappe.db.sql("""select
				employee, employee_name, att_date, status
			from tabAttendance
			where
				att_date in ({0})""".format(', '.join(["%s"] * len(holidays_list))),
				holidays_list, as_list=True)

		for employee_data in employee_list:
			employee_data.append(holiday_names[employee_data[2]])

		return employee_list
	else:
		return []
