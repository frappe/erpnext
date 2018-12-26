# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
from erpnext.hr.doctype.employee_group.test_employee_group import make_employee_group
from erpnext.hr.doctype.holiday_list.test_holiday_list import make_holiday_list

import frappe
import unittest

class TestServiceLevel(unittest.TestCase):

	def test_service_level(self):
		test_make_service_level = make_service_level()
		test_get_service_level = get_service_level()
		self.assertEquals(test_make_service_level, test_get_service_level)

def make_service_level():
	employee_group = make_employee_group()
	make_holiday_list()
	service_level = frappe.get_doc({
		"doctype": "Service Level",
		"service_level": "_Test Service Level",
		"holiday_list": "_Test Holiday List",
		"priority": "Medium",
		"employee_group": employee_group,
		"response_time": "5",
		"response_time_period": "Hour/s",
		"resolution_time": "2",
		"resolution_time_period": "Day/s",
		"support_and_resolution": [
			{
				"workday": "Monday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"response_time": "5",
				"response_time_period": "Hour/s",
				"resolution_time": "2",
				"resolution_time_period": "Day/s"
			},
			{
				"workday": "Tuesday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"response_time": "5",
				"response_time_period": "Hour/s",
				"resolution_time": "2",
				"resolution_time_period": "Day/s"
			},
			{
				"workday": "Wednesday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"response_time": "5",
				"response_time_period": "Hour/s",
				"resolution_time": "2",
				"resolution_time_period": "Day/s"
			},
			{
				"workday": "Thursday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"response_time": "5",
				"response_time_period": "Hour/s",
				"resolution_time": "2",
				"resolution_time_period": "Day/s"
			},
			{
				"workday": "Friday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"response_time": "5",
				"response_time_period": "Hour/s",
				"resolution_time": "2",
				"resolution_time_period": "Day/s"
			},
			{
				"workday": "Saturday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"response_time": "5",
				"response_time_period": "Hour/s",
				"resolution_time": "2",
				"resolution_time_period": "Day/s"
			},
			{
				"workday": "Sunday",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"response_time": "5",
				"response_time_period": "Hour/s",
				"resolution_time": "2",
				"resolution_time_period": "Day/s"
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