# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint

@frappe.whitelist()
def get_feed(start, page_length, name):
	"""get feed"""
	result = frappe.db.sql("""select name, owner, modified, creation,
			reference_doctype, reference_name, subject
		from `tabPatient Medical Record`
		where patient=%(patient)s
		order by creation desc
		limit %(start)s, %(page_length)s""",
		{
			"start": cint(start),
			"page_length": cint(page_length),
			"patient": name
		}, as_dict=True)

	return result
