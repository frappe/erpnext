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
   			"fieldname": "date",
  			"fieldtype": "Data",
  			"label": "Date",
  		},
		{
			"label": _("Invoice"),
			"fieldname": "invoice",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 120
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 120
		},
		{
   			"fieldname": "rtn",
  			"fieldtype": "Data",
  			"label": "Customer RTN",
  		},
		{
   			"fieldname": "cai",
  			"fieldtype": "Data",
  			"label": "CAI",
  		},
		{
			"label": _("Patient"),
			"fieldname": "patient",
			"width": 120
		},
		{
			"label": _("Discount Amount"),
			"fieldname": "discount_amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Grand Total"),
			"fieldname": "grand_total",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"width": 120
		},
		{
			"label": _("Terms and Conditions"),
			"fieldname": "terms_and_condition",
			"fieldtype": "Link",
			"options": "Terms and Conditions",
			"width": 120
		},
		{
			"label": _("User"),
			"fieldname": "user",
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

	salary_slips = frappe.get_all("Sales Invoice", ["*"], filters = conditions,  order_by = "name asc")

	for salary_slip in salary_slips:		
		row = [salary_slip.posting_date, salary_slip.name, salary_slip.customer, salary_slip.rtn, salary_slip.cai, salary_slip.patient_name, salary_slip.discount_amount, salary_slip.grand_total, _(salary_slip.status), salary_slip.tc_name, salary_slip.cashier]
		data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "company": "{}"'.format(filters.get("company"))
	if filters.get("tc_name"): conditions += ', "tc_name": "{}"'.format(filters.get("tc_name"))
	if filters.get("customer"): conditions += ', "customer": "{}"'.format(filters.get("customer"))
	if filters.get("prefix"): conditions += ', "naming_series": "{}"'.format(filters.get("prefix"))
	conditions += '}'

	return conditions