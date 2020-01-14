from __future__ import unicode_literals
import frappe

from frappe import _

def get_context(context):
	context.no_cache = 1

	task = frappe.get_doc('Task', frappe.form_dict.task)
	
	context.comments = frappe.get_all('Communication', filters={'reference_name': task.name, 'comment_type': 'comment'},
	fields=['subject', 'sender_full_name', 'communication_date'])
	
	context.doc = task