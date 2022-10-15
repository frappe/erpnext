# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	
	columns = [
		{
			"fieldname": "entry",
			"label": _("Payment Entry"),
			"fieldtype": "Link",
			"options": "Payment Entry",
			"width": 300
		},
		{
			"fieldname": "serie",
			"label": _("Serie"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "party",
			"label": _("Party"),
			"fieldtype": "Data",
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
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 120
		},
		{
			"fieldname": "paid_amount",
			"label": _("Paid Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"fieldname": "mode_of_payment",
			"label": _("Mode of Payment"),
			"fieldtype": "Link",
			"options": "Mode of Payment",
			"width": 120
		},
		{
			"fieldname": "reason_payment",
			"label": _("Reason For Payment"),
			"fieldtype": "Data",
			"width": 120
		}
	]
	
	data = return_data(filters)

	return columns, data

def return_data(filters):
	data = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)
	entries = frappe.get_all("Payment Entry", ["*"], filters = conditions)

	for entry in entries:	
		is_serial, references = verificate_serial(filters, entry.naming_series, entry.name)
		if is_serial:
			for reference in references:
				row = [entry.name, entry.naming_series, entry.party, reference.reference_doctype, reference.reference_name, entry.company, reference.allocated_amount, entry.mode_of_payment, entry.reason_payment]
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
	conditions += ', "docstatus": 1'
	# conditions += ', "reason_payment": "Advancement"'
	conditions += '}'

	return conditions