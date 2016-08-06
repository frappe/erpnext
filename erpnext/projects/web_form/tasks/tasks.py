from __future__ import unicode_literals

import frappe

def get_context(context):
	if frappe.form_dict.project:
		context.parents = [{'title': frappe.form_dict.project, 'route': '/projects?project='+ frappe.form_dict.project}]
		context.success_url = "/projects?project=" + frappe.form_dict.project
		
	elif context.doc and context.doc.get('project'):
		context.parents = [{'title': context.doc.project, 'route': '/projects?project='+ context.doc.project}]
		context.success_url = "/projects?project=" + context.doc.project
