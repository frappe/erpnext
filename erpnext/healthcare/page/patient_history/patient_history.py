# -*- coding: utf-8 -*-
# Copyright (c) 2018, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint
from erpnext.healthcare.utils import render_docs_as_html

@frappe.whitelist()
def get_feed(name, start=0, page_length=20):
	"""get feed"""
	result = frappe.db.sql("""select name, owner, creation,
		reference_doctype, reference_name, subject
		from `tabPatient Medical Record`
		where patient=%(patient)s
		order by creation desc
		limit %(start)s, %(page_length)s""",
		{
			"patient": name,
			"start": cint(start),
			"page_length": cint(page_length)
		}, as_dict=True)
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
