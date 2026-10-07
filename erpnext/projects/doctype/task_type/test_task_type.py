# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.projects.doctype.task.test_task import create_task
from erpnext.tests.utils import ERPNextTestSuite


class TestTaskType(ERPNextTestSuite):
	def test_task_weight_set_on_the_task_is_kept(self):
		task_type = frappe.get_doc({"doctype": "Task Type", "name": "_Test Task Type", "weight": 1}).insert()
		task = create_task("_Test Weighted Task", save=False)
		task.type = task_type.name
		task.insert()
		self.assertEqual(task.task_weight, 1)

		task.task_weight = 5
		task.save()
		self.assertEqual(task.task_weight, 5)

	def test_negative_weight_is_refused(self):
		task_type = frappe.get_doc({"doctype": "Task Type", "name": "_Test Negative Task Type", "weight": -2})
		self.assertRaises(frappe.NonNegativeError, task_type.insert)

		task = create_task("_Test Negative Weight Task", save=False)
		task.task_weight = -2
		self.assertRaises(frappe.NonNegativeError, task.insert)
