# Copyright (c) 2018, Frappe Technologies and contributors
# For license information, please see license.txt


import frappe
from frappe import _

from erpnext import get_region


def check_deletion_permission(doc, method):
	region = get_region(doc.company)
	if region in ["Nepal"] and doc.docstatus != 0:
		frappe.throw(_("Deletion is not permitted for country {0}").format(region))


def create_transaction_log(doc, method):
	"""
	Appends the transaction to a chain of hashed logs for legal resons.
	Called on submit of Sales Invoice and Payment Entry.
	"""
	region = get_region()
	if region not in ["Germany"]:
		return

	data = str(doc.as_dict())

	frappe.get_doc(
		{
			"doctype": "Transaction Log",
			"reference_doctype": doc.doctype,
			"document_name": doc.name,
			"data": data,
		}
	).insert(ignore_permissions=True)
