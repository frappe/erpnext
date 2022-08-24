# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	columns = [
		{
			"fieldname": "date",
			"label": _("Date"),
			"fieldtype": "Data",
			"width": 240
		},
		{
			"fieldname": "document_number",
			"label": _("No Document"),
			"fieldtype": "Link",
			"options": "Supplier Retention",
			"width": 300
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 300
		},
		{
			"fieldname": "supplier_rtn",
			"label": _("Supplier RTN"),
			"fieldtype": "Data",
			"width": 240
		},		
		{
			"fieldname": "retention_type",
			"label": _("Retention Type"),
			"fieldtype": "Data",
			"width": 240
		},
		{
			"fieldname": "base",
			"label": _("Base"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"fieldname": "retention_porcentage",
			"label": _("% Retention"),
			"fieldtype": "Data",
			"width": 240
		},
		{
			"fieldname": "amount",
			"label": _("Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"label": _("Reference Doctype"),
			"fieldname": "reference_doctype",
			"width": 240
		},
		{
			"label": _("Reference Name"),
			"fieldname": "reference_name",
			"fieldtype": "Dynamic Link",
			"options": "reference_doctype",
			"width": 240
		},
		{
			"fieldname": "cai",
			"label": _("CAI"),
			"fieldtype": "Data",
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
	
	for retention in retentions:
		reasons = frappe.get_all("Reason And Percentage", ["*"], filters = { "parent": retention.name})

		retention_reason = reasons[0].reason
		retention_percentage = reasons[0].percentage

		references = frappe.get_all("Withholding Reference", ["*"], filters = {"parent": retention.name})

		for reference in references:
			retention_percentage_int = int(retention_percentage)
			reference_percentage = reference.net_total * (retention_percentage_int/100)
			if filters.get("reason_for_retention"):
				if filters.get("reason_for_retention") == retention_reason:
					row = [retention.posting_date, retention.name, retention.supplier, retention.rtn, retention_reason, reference.net_total, retention_percentage, reference_percentage, reference.reference_doctype, reference.reference_name, retention.cai]
					data.append(row)
			else:
				row = [retention.posting_date, retention.name, retention.supplier, retention.rtn, retention_reason, reference.net_total, retention_percentage, reference_percentage, reference.reference_doctype, reference.reference_name, retention.cai]
				data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += ', "supplier": "{}"'.format(filters.get("supplier"))
	conditions += ', "docstatus": 1'
	conditions += '}'

	return conditions