# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

from erpnext.projects.doctype.task.test_task import create_task


class TestProjectTemplate(unittest.TestCase):
	pass

def make_project_template(project_template_name, project_tasks=[]):
	if not frappe.db.exists('Project Template', project_template_name):
		project_tasks = project_tasks or [
				create_task(subject="_Test Template Task 1", is_template=1, begin=0, duration=3),
				create_task(subject="_Test Template Task 2", is_template=1, begin=0, duration=2),
			]
		doc = frappe.get_doc(dict(
			doctype = 'Project Template',
			name = project_template_name
		))
		for task in project_tasks:
			doc.append("tasks",{
				"task": task.name
			})
		doc.insert()

	return frappe.get_doc('Project Template', project_template_name)
