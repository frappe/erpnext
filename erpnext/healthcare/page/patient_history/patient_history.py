# -*- coding: utf-8 -*-
# Copyright (c) 2018, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.utils import cint
from erpnext.healthcare.utils import render_docs_as_html

@frappe.whitelist()
def get_feed(name, document_types=None, start=0, page_length=20):
	"""get feed"""
	filters = {'patient': name}
	if document_types:
		document_types = json.loads(document_types)
		filters['reference_doctype'] = ['IN', document_types]

	result = frappe.db.get_all('Patient Medical Record',
		fields=['name', 'owner', 'creation',
			'reference_doctype', 'reference_name', 'subject'],
		filters=filters,
		order_by='creation DESC',
		limit=cint(page_length),
		start=cint(start)
	)

	return result

@frappe.whitelist()
def get_feed_for_dt(doctype, docname):
	"""get feed"""
	result = frappe.db.get_all('Patient Medical Record',
		fields=['name', 'owner', 'creation',
			'reference_doctype', 'reference_name', 'subject'],
		filters={
			'reference_doctype': doctype,
			'reference_name': docname
		},
		order_by='creation DESC'
	)

	return result

@frappe.whitelist()
def get_patient_history_doctypes():
	document_types = []
	settings = frappe.get_single("Patient History Settings")

	for entry in settings.standard_doctypes:
		document_types.append(entry.document_type)

	for entry in settings.custom_doctypes:
		document_types.append(entry.document_type)

	return document_types