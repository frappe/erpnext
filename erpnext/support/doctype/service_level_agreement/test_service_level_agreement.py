# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.support.doctype.service_level.test_service_level import make_service_level

class TestServiceLevelAgreement(unittest.TestCase):
	pass

def make_service_level_agreement():
	make_service_level()

	# Default Service Level Agreement
	default_service_level_agreement = frappe.get_doc({
		"doctype": "Service Level Agreement",
		"sla_name": "Default Service Level Agreement",
		"default_service_level_agreement": 1,
		"service_level": "__Test Service Level",
		"holiday_list": "__Test Holiday List",
		"employee_group": "_Test Employee Group",
		"start_date": frappe.utils.getdate(),
		"end_date": frappe.utils.add_to_date(frappe.utils.getdate(), days=100),
		"priorities": [
			{
				"priority": "Low",
				"response_time": 4,
				"response_time_period": "Hour",
				"resolution_time": 6,
				"resolution_time_period": "Hour",
			},
			{
				"priority": "Medium",
				"response_time": 4,
				"response_time_period": "Hour",
				"resolution_time": 6,
				"resolution_time_period": "Hour",
			},
			{
				"priority": "High",
				"response_time": 4,
				"response_time_period": "Hour",
				"resolution_time": 6,
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

	default_service_level_agreement_exists = frappe.db.exists("Service Level Agreement", "Default Service Level Agreement")
	if not default_service_level_agreement_exists:
		default_service_level_agreement.insert(ignore_permissions=True)

	customer = frappe.get_doc({
		"doctype": "Customer",
		"customer_name": "_Test Customer",
		"customer_group": "Commercial",
		"customer_type": "Individual",
		"territory": "Rest Of The World"
	})
	if not frappe.db.exists("Customer", "_Test Customer"):
		customer.insert(ignore_permissions=True)
	else:
		customer = frappe.get_doc("Customer", "_Test Customer")

	service_level_agreement = frappe.get_doc({
		"doctype": "Service Level Agreement",
		"sla_name": "_Test Service Level Agreement",
		"customer": customer.customer_name,
		"service_level": "_Test Service Level",
		"holiday_list": "__Test Holiday List",
		"employee_group": "_Test Employee Group",
		"start_date": frappe.utils.getdate(),
		"end_date": frappe.utils.add_to_date(frappe.utils.getdate(), days=100),
		"priorities": [
			{
				"priority": "Low",
				"response_time": 2,
				"response_time_period": "Day",
				"resolution_time": 3,
				"resolution_time_period": "Day",
			},
			{
				"priority": "Medium",
				"response_time": 2,
				"response_time_period": "Day",
				"resolution_time": 3,
				"resolution_time_period": "Day",
			},
			{
				"priority": "High",
				"response_time": 2,
				"response_time_period": "Day",
				"resolution_time": 3,
				"resolution_time_period": "Day",
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

	service_level_agreement_exists = frappe.db.exists("Service Level Agreement", "_Test Service Level Agreement")
	if not service_level_agreement_exists:
		service_level_agreement.insert(ignore_permissions=True)
		return service_level_agreement.name
	else:
		return service_level_agreement_exists

def get_service_level_agreement():
	service_level_agreement = frappe.db.exists("Service Level Agreement", "_Test Service Level Agreement")
	return service_level_agreement