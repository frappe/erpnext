# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
from frappe.utils.data import get_datetime, add_days

import frappe
import unittest

# test_records = frappe.get_test_records('Maintenance Schedule')

class TestMaintenanceSchedule(unittest.TestCase):
	def test_events_should_be_created_and_deleted(self):
		ms = make_maintenance_schedule()
		ms.generate_schedule()
		ms.submit()

		all_events = get_events(ms)
		self.assertTrue(len(all_events) > 0)

		ms.cancel()
		events_after_cancel = get_events(ms)
		self.assertTrue(len(events_after_cancel) == 0)

def get_events(ms):
	return frappe.get_all("Event Participants", filters={
			"reference_doctype": ms.doctype,
			"reference_docname": ms.name,
			"parenttype": "Event"
		})

def make_maintenance_schedule():
	ms = frappe.new_doc("Maintenance Schedule")
	ms.company = "_Test Company"
	ms.customer = "_Test Customer"
	ms.transaction_date = get_datetime()

	ms.append("items", {
		"item_code": "_Test Item",
		"start_date": get_datetime(),
		"end_date": add_days(get_datetime(), 32),
		"periodicity": "Weekly",
		"no_of_visits": 4,
		"sales_person": "Sales Team",
	})
	ms.insert(ignore_permissions=True)

	return ms
