from __future__ import unicode_literals
import erpnext.education.utils as utils
import frappe

no_cache = 1

def get_context(context):
	context.education_settings = frappe.get_single("Education Settings")
	course = frappe.get_doc('Course', frappe.form_dict['name'])
	context.course = course
	context.topics = course.get_topics()