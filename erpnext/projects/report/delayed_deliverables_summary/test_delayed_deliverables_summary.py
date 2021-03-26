from __future__ import unicode_literals
import unittest
import frappe
import datetime
from frappe.utils import nowdate, add_days, add_months
from erpnext.projects.doctype.task.test_task import create_task
from erpnext.projects.report.delayed_deliverables_summary.delayed_deliverables_summary import execute

class TestInpatientMedicationOrders(unittest.TestCase):
	@classmethod
	def setUp(self):
		task1 = create_task("_Test Task 98", add_days(nowdate(), -10), nowdate())
		task2 = create_task("_Test Task 99", add_days(nowdate(), -10), add_days(nowdate(), -1))
		
		task1.status = "Completed"
		task1.completed_on = add_days(nowdate(), -1)
		task1.save()

	def test_delayed_deliverables_summary(self):
		filters = frappe._dict({
			"from_date": add_months(nowdate(), -1),
			"to_date": nowdate(),
			"priority": "Low",
			"status": "Open"
		})
		expected_data = [
			{
				"subject": "_Test Task 99",
				"exp_start_date": datetime.date(2021, 3, 16),
				"exp_end_date": datetime.date(2021, 3, 25),
				"status": "Open",
				"priority": "Low",
				"delay": 1
			},
			{
				"subject": "_Test Task 98",
				"exp_start_date": datetime.date(2021, 3, 16),
				"exp_end_date": datetime.date(2021, 3, 26),
				"status": "Completed",
				"priority": "Low",
				"completed_on": datetime.date(2021, 3, 25),
				"delay": -1
			}
		]
		report = execute(filters)
		data = list(filter(lambda x: x.subject == "_Test Task 99", report[1]))[0]
		
		for key in ["subjet", "exp_start_date", "exp_end_date", "status", "priority", "delay"]:
			self.assertEqual(expected_data[0].get(key), data.get(key))

		filters.status = "Completed"
		report = execute(filters)
		data = list(filter(lambda x: x.subject == "_Test Task 98", report[1]))[0]

		for key in ["subjet", "exp_start_date", "exp_end_date", "status", "priority", "completed_on", "delay"]:
			self.assertEqual(expected_data[1].get(key), data.get(key))

	def tearDown(self):
		for task in ["_Test Task 98", "_Test Task 99"]:
			frappe.get_doc("Task", {"subject": task}).delete()