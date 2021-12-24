from __future__ import unicode_literals

import frappe


def get_context(context):
	context.no_cache = 1

	timelog = frappe.get_doc('Time Log', frappe.form_dict.timelog)

	context.doc = timelog
