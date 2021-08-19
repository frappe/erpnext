# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

@frappe.whitelist()
def get_all_nodes(parent, parent_name, method, company):
	'''Recursively gets all data from nodes'''
	method = frappe.get_attr(method)

	if method not in frappe.whitelisted:
		frappe.throw(_('Not Permitted'), frappe.PermissionError)

	data = method(parent, company)
	result = [dict(parent=parent, parent_name=parent_name, data=data)]

	nodes_to_expand = [{'id': d.get('id'), 'name': d.get('name')} for d in data if d.get('expandable')]

	while nodes_to_expand:
		parent = nodes_to_expand.pop(0)
		data = method(parent.get('id'), company)
		result.append(dict(parent=parent.get('id'), parent_name=parent.get('name'), data=data))
		for d in data:
			if d.get('expandable'):
				nodes_to_expand.append({'id': d.get('id'), 'name': d.get('name')})

	return result
