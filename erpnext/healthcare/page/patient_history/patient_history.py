# -*- coding: utf-8 -*-
# Copyright (c) 2018, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint
from erpnext.healthcare.utils import render_docs_as_html

@frappe.whitelist()
def get_feed(name):
	"""get feed"""
	result = frappe.db.sql("""select name, owner, modified, creation,
			reference_doctype, reference_name, subject
		from `tabPatient Medical Record`
		where patient=%(patient)s
		order by creation desc""",
		{
			"patient": name
		}, as_dict=True)

	for dict_item in result:
		if dict_item.reference_doctype != "Vital Signs":
			practitioner = frappe.db.get_value(dict_item.reference_doctype, dict_item.reference_name, 'practitioner')
			practitioner_user = frappe.db.get_value("Healthcare Practitioner", practitioner, "user_id")
			dict_item.update({'practitioner': practitioner, 'practitioner_user': practitioner_user})

	return result

@frappe.whitelist()
def get_feed_for_dt(doctype, docname):
	"""get feed"""
	result = frappe.db.sql("""select name, owner, modified, creation,
			reference_doctype, reference_name, subject
		from `tabPatient Medical Record`
		where reference_name=%(docname)s and reference_doctype=%(doctype)s
		order by creation desc""",
		{
			"docname": docname,
			"doctype": doctype
		}, as_dict=True)

	return result
