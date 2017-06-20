from __future__ import unicode_literals

import frappe

def get_context(context):
	patient = frappe.get_value("Patient",{"email": frappe.session.user}, "name")
	frappe.form_dict.name = patient
	frappe.form_dict.new = 0
	context.doc = frappe.get_doc("Patient", patient)
