# Copyright (c) 2018, ESS LLP and contributors
# For license information, please see license.txt


import json

import frappe
from frappe.utils import cint


@frappe.whitelist()
def get_feed(name, document_types=None, date_range=None, start=0, page_length=20):
	"""get feed"""
	filters = get_filters(name, document_types, date_range)

	result = frappe.db.get_all(
		"Patient Medical Record",
		fields=["name", "owner", "communication_date", "reference_doctype", "reference_name", "subject"],
		filters=filters,
		order_by="communication_date DESC",
		limit=cint(page_length),
		start=cint(start),
	)

	return result


def get_filters(name, document_types=None, date_range=None):
	filters = {"patient": name}
	if document_types:
		document_types = json.loads(document_types)
		if len(document_types):
			filters["reference_doctype"] = ["IN", document_types]

	if date_range:
		try:
			date_range = json.loads(date_range)
			if date_range:
				filters["communication_date"] = ["between", [date_range[0], date_range[1]]]
		except json.decoder.JSONDecodeError:
			pass

	return filters


@frappe.whitelist()
def get_feed_for_dt(doctype, docname):
	"""get feed"""
	result = frappe.db.get_all(
		"Patient Medical Record",
		fields=["name", "owner", "communication_date", "reference_doctype", "reference_name", "subject"],
		filters={"reference_doctype": doctype, "reference_name": docname},
		order_by="communication_date DESC",
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
