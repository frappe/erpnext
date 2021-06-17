# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
from frappe.utils.data import add_days, today, formatdate
from erpnext.maintenance.doctype.maintenance_schedule.maintenance_schedule import make_maintenance_visit

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
	
	def test_make_schedule(self):
		ms = make_maintenance_schedule()
		ms.save()
		i = ms.items[0]
		expected_dates = []
		expected_end_date = add_days(i.start_date, i.no_of_visits * 7)
		self.assertEqual(i.end_date, expected_end_date)

		i.no_of_visits = 2
		ms.save()
		expected_end_date = add_days(i.start_date, i.no_of_visits * 7)
		self.assertEqual(i.end_date, expected_end_date)

		items = ms.get_pending_data(data_type = "items")
		items = items.split('\n')
		items.pop(0)
		expected_items = ['_Test Item']
		self.assertTrue(items, expected_items)

		# "dates" contains all generated schedule dates
		dates = ms.get_pending_data(data_type = "date", item_name = i.item_name)
		dates = dates.split('\n')
		dates.pop(0)
		expected_dates.append(formatdate(add_days(i.start_date, 7), "dd-MM-yyyy"))
		expected_dates.append(formatdate(add_days(i.start_date, 14), "dd-MM-yyyy"))

		# test for generated schedule dates
		self.assertEqual(dates, expected_dates)

		ms.submit()
		s_id = ms.get_pending_data(data_type = "id", item_name = i.item_name, s_date = expected_dates[1])
		test = make_maintenance_visit(source_name = ms.name, item_name = "_Test Item", s_id = s_id)
		visit = frappe.new_doc('Maintenance Visit')
		visit = test
		visit.maintenance_schedule = ms.name
		visit.maintenance_schedule_detail = s_id
		visit.completion_status = "Partially Completed"
		visit.set('purposes', [{
			'item_code': i.item_code,
			'description': "test",
			'work_done': "test",
			'service_person': "Sales Team",
		}])
		visit.save()
		visit.submit()
		ms = frappe.get_doc('Maintenance Schedule', ms.name)

		#checks if visit status is back updated in schedule
		self.assertTrue(ms.schedules[1].completion_status, "Partially Completed")
	
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
	ms.transaction_date = today()

	ms.append("items", {
		"item_code": "_Test Item",
		"start_date": today(),
		"periodicity": "Weekly",
		"no_of_visits": 4,
		"sales_person": "Sales Team",
	})
	ms.insert(ignore_permissions=True)

	return ms
