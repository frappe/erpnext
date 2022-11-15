# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
import datetime

def execute(filters=None):
	if not filters: filters = {}
	columns = [
		{
			"label": _("Supplier Retention"),
			"fieldname": "supplier_retention",
			"fieldtype": "Link",
			"options": "Supplier Retention",
			"width": 240
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"width": 240
		},
		{
			"label": _("Date"),
			"fieldname": "date",
			"fieldtype": "Date",
			"width": 240
		},
		{
			"label": _("Supplier"),
			"fieldname": "supplier",
			"width": 240
		},
		{
			"label": _("RTN"),
			"fieldname": "rtn",
			"width": 240
		},
		{
			"label": _("CAI"),
			"fieldname": "cai",
			"width": 240
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 240
		},
		{
			"label": _("Due Date"),
			"fieldname": "due_date",
			"fieldtype": "Date",
			"width": 240
		},
		{
			"label": _("% Retention"),
			"fieldname": "pocentage_retention",
			"width": 240
		},
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"width": 240
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 240
		},
		{
			"label": _("Reference Date"),
			"fieldname": "reference_date",
			"fieldtype": "Date",
			"width": 240
		},
		{
			"label": _("Transaction No"),
			"fieldname": "transaction_no",
			"width": 240
		},
		{
			"label": _("Reference CAI"),
			"fieldname": "reference_cai",
			"width": 240
		},
		{
			"label": _("Supplier Invoice No"),
			"fieldname": "bill_no",
			"fieldtype": "Data",
			"width": 240
		},
		{
			"label": _("Base"),
			"fieldname": "base",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Created By"),
			"fieldname": "created_by",
			"width": 240
		},
	]
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)

	retentions = frappe.get_all("Supplier Retention", ["*"], filters = conditions)

	if filters.get("reason"):
		for retention in retentions:
			is_reason = False
			reasons = frappe.get_all("Reason And Percentage", ["*"], filters = {"parent": retention.name})

			for reason in reasons:
				if reason.reason == filters.get("reason"):
					is_reason = True
			
			if is_reason:
				data += build_data(retention)
	else:	
		for retention in retentions:
			data += build_data(retention)

	return data

def build_data(retention):
	data = []
	
	references = frappe.get_all("Withholding Reference", ["*"], filters = {"parent": retention.name})

	for reference in references:
		percentage_str = str(retention.percentage_total)
		percentage = "{}%".format(percentage_str)
		amount = reference.net_total * (retention.percentage_total/100) 
		bill_no = ""
		transaction_number = ""
		date = retention.due_date
		cai_reference = ""

		if reference.reference_doctype == "Purchase Invoice":
			invoice = frappe.get_doc("Purchase Invoice", reference.reference_name)
			transaction_number = invoice.bill_no
			date = invoice.posting_date
			cai_reference = reference.cai 
		else:
			if reference.reference_doctype == "Supplier Documents":
				document = frappe.get_doc("Supplier Documents", reference.reference_name)
				transaction_number = reference.transaction_number
				date = document.posting_date
				cai_reference = reference.cai

		row = [retention.name, retention.status, retention.posting_date, retention.supplier, retention.rtn, retention.cai, date, retention.due_date, percentage, reference.reference_doctype, reference.reference_name, date, transaction_number, cai_reference, bill_no, reference.net_total, amount, retention.owner]
		data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += '}'

	return conditions