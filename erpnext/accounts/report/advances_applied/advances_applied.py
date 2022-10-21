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
			"label": _("Identificador"),
			"fieldname": "identifier",
			"fieldtype": "Link",
			"options": "Payment Entry",
			"width": 240
		},
		{
			"label": _("Name"),
			"fieldname": "name",
			"width": 240
		},
		{
			"label": _("Payment Type"),
			"fieldname": "payment_type",
			"width": 240
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"width": 240
		},
		{
			"label": _("Mode of payment"),
			"fieldname": "mode_of_payment",
			"width": 240
		},
		{
			"label": _("Party Type"),
			"fieldname": "party_type",
			"width": 240
		},
		{
			"label": _("Party"),
			"fieldname": "party",
			"width": 240
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
			"label": _("Amount Document"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": 120
		},
	]
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)

	advances = frappe.get_all("Payment Entry", ["*"], filters = conditions)

	for advance in advances:
		is_serial, references = verificate_serial(filters, advance.naming_series, advance.name)
		if is_serial:
			amount = 0
			if filters.get("applied") == 1:
				amount = advance.total_allocated_amount
				for reference in references:
					row =  [advance.name, advance.party, advance.payment_type, advance.posting_date, advance.mode_of_payment, advance.party_type, advance.party, reference.reference_doctype, reference.reference_name, reference.allocated_amount, amount]
					data.append(row)
			else:
				amount = advance.unallocated_amount
				row = [advance.name, advance.party, advance.payment_type, advance.posting_date, advance.mode_of_payment, advance.party_type, advance.party, "", "", 0, amount]
				data.append(row)
		
	return data

def verificate_serial(filters, naming_series, name):
	serial_split = naming_series.split("-")
	serialString = serial_split[0] + "-" + serial_split[1]

	is_serial = False
	references =  frappe.get_all("Payment Entry Reference", ["*"], filters = {"parent": name})
		
	if serialString == filters.get("secuence"):
		if len(references) > 0:
			is_serial = True
		
	return is_serial, references

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += ', "docstatus": ["!=", 2]'
	if filters.get("applied") == 1:
		conditions += ', "total_allocated_amount": [">", "0"]'
	else:
		conditions += ', "unallocated_amount": [">", "0"]'
	conditions += '}'

	return conditions