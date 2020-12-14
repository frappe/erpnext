# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class ProjectTemplate(Document):

	def validate(self):
		self.validate_dependencies()

	def validate_dependencies(self):
		for task in self.tasks:
			task_details = frappe.get_doc("Task", task.task)
			if task_details.depends_on:
				for dependency_task in task_details.depends_on:
					if not self.check_dependent_task_presence(dependency_task.task):
						task_details_format = """<a href="#Form/Task/{0}">{0}</a>""".format(task_details.name)
						dependency_task_format = """<a href="#Form/Task/{0}">{0}</a>""".format(dependency_task.task)
						frappe.throw(_("Task {0} depends on Task {1}. Please add Task {1} to the Tasks list.").format(frappe.bold(task_details_format), frappe.bold(dependency_task_format)))
	
	def check_dependent_task_presence(self, task):
		for task_details in self.tasks:
			if task_details.task == task:
				return True
		return False
