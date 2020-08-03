from __future__ import unicode_literals

import frappe
import json
import pprint
from erpnext.projects.doctype.task.task import get_children
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