import unittest

import frappe
from frappe.utils import add_days, add_months, nowdate

from erpnext.projects.doctype.task.test_task import create_task
from erpnext.projects.report.delayed_tasks_summary.delayed_tasks_summary import execute


class TestDelayedTasksSummary(unittest.TestCase):
	@classmethod
	def setUp(self):
		task1 = create_task("_Test Task 98", add_days(nowdate(), -10), nowdate())
		create_task("_Test Task 99", add_days(nowdate(), -10), add_days(nowdate(), -1))

		task1.status = "Completed"
		task1.completed_on = add_days(nowdate(), -1)
		task1.save()

	def test_delayed_tasks_summary(self):
		filters = frappe._dict(
			{
				"from_date": add_months(nowdate(), -1),
				"to_date": nowdate(),
				"priority": "Low",
				"status": "Open",
			}
		)
		expected_data = [
			{"subject": "_Test Task 99", "status": "Open", "priority": "Low", "delay": 1},
			{"subject": "_Test Task 98", "status": "Completed", "priority": "Low", "delay": -1},
		]
		report = execute(filters)
		data = list(filter(lambda x: x.subject == "_Test Task 99", report[1]))[0]

		for key in ["subject", "status", "priority", "delay"]:
			self.assertEqual(expected_data[0].get(key), data.get(key))

		filters.status = "Completed"
		report = execute(filters)
		data = list(filter(lambda x: x.subject == "_Test Task 98", report[1]))[0]

		for key in ["subject", "status", "priority", "delay"]:
			self.assertEqual(expected_data[1].get(key), data.get(key))

	def tearDown(self):
		for task in ["_Test Task 98", "_Test Task 99"]:
			frappe.get_doc("Task", {"subject": task}).delete()
