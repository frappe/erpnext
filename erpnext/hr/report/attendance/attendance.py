# # Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# # For license information, please see license.txt

# from __future__ import unicode_literals
# import frappe

# def execute(filters=None):
# 	columns, data = [], []
# 	return columns, data



# encoding: utf-8
# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate, getdate, flt, add_days, get_first_day, get_last_day
from datetime import date
import calendar
import datetime


def last_day_of_month(any_day):
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
    return next_month - datetime.timedelta(days=next_month.day)


def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data
	
def get_columns(filters):
	return [
		_("Employee") + ":Link/Employee:120",
		_("Employee Name") + "::120",
		_("Day") + "::120",
		_("Date") + "::120",
		_("Check in") + "::120",
		_("Check out") + "::120",
		]



def get_data(filters):
	li_list=[]

	this_year = filters.year
	this_month = filters.month
	date_format = str(this_year)+"-"+str(this_month)+"-01"
	selected_start_date = get_first_day(getdate(date_format))
	selected_end_date = get_last_day(getdate(date_format))

	if filters.employee:
		li_list=frappe.db.sql("select * from `tabAttendance` where employee='{0}' and attendance_date > '{1}' and attendance_date < '{2}' and docstatus=1".format(filters.employee,str(selected_start_date),str(selected_end_date)),as_dict=1)
	else:
		li_list=frappe.db.sql("select * from `tabAttendance` where attendance_date > '{0}' and attendance_date < '{1}'  and docstatus=1".format(str(selected_start_date),str(selected_end_date)),as_dict=1)


	data = []

	for att in li_list:
		row = [
		att.employee,
		att.employee_name,
		calendar.day_name[att.attendance_date.weekday()],
		att.attendance_date,
		att.attendance,
		att.departure,
		]
		data.append(row)
	return data




