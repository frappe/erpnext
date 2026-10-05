# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.projects.doctype.task.test_task import create_task


class TestTaskType(FrappeTestCase):
	def test_task_weight_set_on_the_task_is_kept(self):
		task_type = frappe.get_doc({"doctype": "Task Type", "name": "_Test Task Type", "weight": 1}).insert()
		task = create_task("_Test Weighted Task", save=False)
		task.type = task_type.name
		task.insert()
		self.assertEqual(task.task_weight, 1)

		task.task_weight = 5
		task.save()
		self.assertEqual(task.task_weight, 5)
