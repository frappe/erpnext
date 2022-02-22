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
			"label": _("Base"),
			"fieldname": "base",
			"width": 120
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
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
	dates = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)

	retentions = frappe.get_all("Supplier Retention", ["*"], filters = conditions)

	for retention in retentions:
		references = frappe.get_all("Withholding Reference", ["*"], filters = {"parent": retention.name})

		for reference in references:
			percentage_str = str(retention.percentage_total)
			percentage = "{}%".format(percentage_str)
			amount = reference.net_total * (retention.percentage_total/100) 
			row = [retention.name, retention.posting_date, retention.supplier, retention.rtn, retention.cai, retention.due_date, percentage, reference.reference_doctype, reference.reference_name, reference.net_total, amount, retention.owner]
			data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += '}'

	return conditions