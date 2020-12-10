# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

def execute():
	all_tasks = frappe.get_all("Task")
	for task in all_tasks:
		task_doc = frappe.get_doc("Task", task.name)
		task_doc.update_depends_on()
		task_doc.save()