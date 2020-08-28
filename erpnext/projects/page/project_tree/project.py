from __future__ import unicode_literals

import frappe
import json
from frappe.desk.reportview import get_form_params, compress, execute

@frappe.whitelist()
def get_projects_data(params):
	args = get_form_params(json.loads(params))
	data = compress(execute(**args), args=args)

	return data

@frappe.whitelist()
def get_tasks(params):
	args = get_form_params(json.loads(params))

	args.get("fields").append('`tabTask`.`is_group` as expandable')
	data = compress(execute(**args), args=args)

	return data

@frappe.whitelist()
def get_tasks_for_portal(params):
	args = get_form_params(json.loads(params))

	args.get("fields").append('`tabTask`.`is_group` as expandable')
	args.get("fields").append('`tabTask`.`parent` as expandable')
	data = compress(execute(**args), args=args)

	values = []
	allowed_tasks = frappe.get_list('Task User', fields=['parent'], filters={'user': args.get('user')})

	allowed_tasks = [d.parent for d in allowed_tasks]

	if data:
		for task in data.get('values'):
			# external user in task
			if task[0] in allowed_tasks:
				values.append(task)

			# external user in parent task
			elif task[10] in allowed_tasks:
				values.append(task)

		data['values'] = values

	return data

@frappe.whitelist()
def get_meta():

	return {
		"project": frappe.get_meta("Project"),
		"task": frappe.get_meta("Task")
	}