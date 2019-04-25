# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
from erpnext.hr.doctype.employee_group.test_employee_group import make_employee_group
from frappe.utils import now_datetime
import datetime
from datetime import timedelta

import frappe
import unittest

class TestServiceLevel(unittest.TestCase):
	pass

def make_service_level():
	employee_group = make_employee_group()
	make_holiday_list()

	# Default Service Level Agreement
	default_service_level = frappe.get_doc({
		"doctype": "Service Level",
		"service_level": "__Test Service Level",
		"holiday_list": "__Test Holiday List",
		"priority": "Medium",
		"employee_group": employee_group,
		"response_time": 4,
		"response_time_period": "Hour",
		"resolution_time": 6,
		"resolution_time_period": "Hour",
		"support_and_resolution": [
			{
				"workday": "Monday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Tuesday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Wednesday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Thursday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Friday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Saturday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Sunday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			}
		]
	})

	default_service_level_exists = frappe.db.exists("Service Level", "__Test Service Level")
	if not default_service_level_exists:
		default_service_level.insert()

	service_level = frappe.get_doc({
		"doctype": "Service Level",
		"service_level": "_Test Service Level",
		"holiday_list": "__Test Holiday List",
		"priority": "Medium",
		"employee_group": employee_group,
		"response_time": 2,
		"response_time_period": "Day",
		"resolution_time": 3,
		"resolution_time_period": "Day",
		"support_and_resolution": [
			{
				"workday": "Monday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Tuesday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Wednesday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Thursday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Friday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Saturday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			},
			{
				"workday": "Sunday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
			}
		]
	})
	service_level_exist = frappe.db.exists("Service Level", "_Test Service Level")
	if not service_level_exist:
		service_level.insert()
		return service_level.service_level
	else:
		return service_level_exist

def get_service_level():
	service_level = frappe.db.exists("Service Level", "_Test Service Level")
	return service_level

def make_holiday_list():
	holiday_list = frappe.db.exists("Holiday List", "__Test Holiday List")
	if not holiday_list:
		now = datetime.datetime.now()
		holiday_list = frappe.get_doc({
			"doctype": "Holiday List",
			"holiday_list_name": "__Test Holiday List",
			"from_date": "2019-01-01",
			"to_date": "2019-12-31",
			"holidays": [
				{
					"description": "Test Holiday 1",
					"holiday_date": "2019-03-05"
				},
				{
					"description": "Test Holiday 2",
					"holiday_date": "2019-03-07"
				},
				{
					"description": "Test Holiday 3",
					"holiday_date": "2019-02-11"
				},
			]
		}).insert()