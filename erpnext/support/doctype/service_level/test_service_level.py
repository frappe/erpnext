# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
from erpnext.hr.doctype.employee_group.test_employee_group import make_employee_group
from erpnext.support.doctype.issue_priority.test_issue_priority import make_priorities

import frappe
import unittest

class TestServiceLevel(unittest.TestCase):

	def test_service_level(self):
		employee_group = make_employee_group()
		make_holiday_list()
		make_priorities()

		# Default Service Level
		test_make_service_level = create_service_level("__Test Service Level", "__Test Holiday List", employee_group, 4, 6)
		get_make_service_level = get_service_level("__Test Service Level")

		self.assertEqual(test_make_service_level.name, get_make_service_level.name)
		self.assertEqual(test_make_service_level.holiday_list, get_make_service_level.holiday_list)
		self.assertEqual(test_make_service_level.employee_group, get_make_service_level.employee_group)

		# Service Level
		test_make_service_level = create_service_level("_Test Service Level", "__Test Holiday List", employee_group, 2, 3)
		get_make_service_level = get_service_level("_Test Service Level")

		self.assertEqual(test_make_service_level.name, get_make_service_level.name)
		self.assertEqual(test_make_service_level.holiday_list, get_make_service_level.holiday_list)
		self.assertEqual(test_make_service_level.employee_group, get_make_service_level.employee_group)


def create_service_level(service_level, holiday_list, employee_group, response_time, resolution_time):
	sl = frappe.get_doc({
		"doctype": "Service Level",
		"service_level": service_level,
		"holiday_list": holiday_list,
		"employee_group": employee_group,
		"priorities": [
			{
				"priority": "Low",
				"response_time": response_time,
				"response_time_period": "Hour",
				"resolution_time": resolution_time,
				"resolution_time_period": "Hour",
			},
			{
				"priority": "Medium",
				"response_time": response_time,
				"default_priority": 1,
				"response_time_period": "Hour",
				"resolution_time": resolution_time,
				"resolution_time_period": "Hour",
			},
			{
				"priority": "High",
				"response_time": response_time,
				"response_time_period": "Hour",
				"resolution_time": resolution_time,
				"resolution_time_period": "Hour",
			}
		],
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

	sl_exists = frappe.db.exists("Service Level", {"service_level": service_level})

	if not sl_exists:
		sl.insert()
		return sl
	else:
		return frappe.get_doc("Service Level", {"service_level": service_level})

def get_service_level(service_level):
	return frappe.get_doc("Service Level", service_level)

def make_holiday_list():
	holiday_list = frappe.db.exists("Holiday List", "__Test Holiday List")
	if not holiday_list:
		now = frappe.utils.now_datetime()
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

def create_service_level_for_sla():
	employee_group = make_employee_group()
	make_holiday_list()
	make_priorities()

	# Default Service Level
	create_service_level("__Test Service Level", "__Test Holiday List", employee_group, 4, 6)

	# Service Level
	create_service_level("_Test Service Level", "__Test Holiday List", employee_group, 2, 3)
