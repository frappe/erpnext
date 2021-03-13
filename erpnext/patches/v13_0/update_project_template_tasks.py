# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("projects", "doctype", "project_template")
	frappe.reload_doc("projects", "doctype", "project_template_task")
	frappe.reload_doc("projects", "doctype", "task")

	# Update property setter status if any
	property_setter = frappe.db.get_value('Property Setter', {'doc_type': 'Task',
		'field_name': 'status', 'property': 'options'})

	if property_setter:
		property_setter_doc = frappe.get_doc('Property Setter', {'doc_type': 'Task',
			'field_name': 'status', 'property': 'options'})
		property_setter_doc.value += "\nTemplate"
		property_setter_doc.save()

	for template_name in frappe.get_all('Project Template'):
		template = frappe.get_doc("Project Template", template_name.name)
		replace_tasks = False
		new_tasks = []
		for task in template.tasks:
			if task.subject:
				replace_tasks = True
				new_task = frappe.get_doc(dict(
					doctype = "Task",
					subject = task.subject,
					start = task.start,
					duration = task.duration,
					task_weight = task.task_weight,
					description = task.description,
					is_template = 1
				)).insert()
				new_tasks.append(new_task)

		if replace_tasks:
			template.tasks = []
			for tsk in new_tasks:
				template.append("tasks", {
					"task": tsk.name,
					"subject": tsk.subject
				})
			template.save()