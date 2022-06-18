# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import datetime

def execute(filters=None):
	if not filters: filters = {}
	columns = [
		{
   			"fieldname": "supplier",
  			"fieldtype": "Data",
  			"label": _("Supplier"),
  		},
		{
   			"fieldname": "date",
  			"fieldtype": "Data",
  			"label": _("Date"),
  		},
		{
			"label": _("Type Document"),
			"fieldname": "reference_doctype",
			"width": 240
		},
		{
			"label": _("Document Name"),
			"fieldname": "reference_name",
			"fieldtype": "Dynamic Link",
			"options": "reference_doctype",
			"width": 240
		},
		{
   			"fieldname": "amount",
  			"fieldtype": "Currency",
  			"label": _("Amount"),
  		},
		{
   			"fieldname": "outstanding_amount",
  			"fieldtype": "Currency",
  			"label":_("Outstanding Amount"),
  		},
		{
   			"fieldname": "due_date",
  			"fieldtype": "data",
  			"label": _("Due Date"),
  		},
		{
   			"fieldname": "days",
  			"fieldtype": "data",
  			"label": _("Days"),
  		}
	]
	data = []

	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")

	if filters.get("supplier"):	
		supplier = filters.get("supplier")
		conditions = get_conditions(filters, from_date, to_date, supplier)

		invoices = frappe.get_all("Purchase Invoice", ["*"], filters = conditions)

		group_arr = [{'indent': 0.0, "supplier": supplier}]
		data.extend(group_arr or [])

		registers = []

		for invoice in invoices:
			day = days(invoice.due_date)
			product_arr = {'indent': 1.0,"date": invoice.posting_date, "reference_doctype": "Purchase Invoice", "reference_name": invoice.name, "amount":invoice.rounded_total, "outstanding_amount": invoice.outstanding_amount, "due_date": invoice.due_date, "days": day}
			registers.append(product_arr)

		documents = frappe.get_all("Supplier Documents", ["*"], filters = conditions)	

		for document in documents:
			day = days(document.due_date)
			product_arr = {'indent': 1.0,"date": document.posting_date, "reference_doctype": "Supplier Documents", "reference_name": document.name, "amount":document.total, "outstanding_amount": document.outstanding_amount, "due_date": document.due_date, "days": day}
			registers.append(product_arr)
		
		data.extend(registers or [])
	else:
		suppliers = frappe.get_all("Supplier", ["*"])

		for supplier in suppliers:
			conditions = get_conditions(filters, from_date, to_date, supplier.name)

			invoices = frappe.get_all("Purchase Invoice", ["*"], filters = conditions)

			group_arr = [{'indent': 0.0, "supplier": supplier.name}]
			data.extend(group_arr or [])

			registers = []

			for invoice in invoices:
				day = days(invoice.due_date)
				product_arr = {'indent': 1.0,"date": invoice.posting_date, "reference_doctype": "Purchase Invoice", "reference_name": invoice.name, "amount":invoice.rounded_total, "outstanding_amount": invoice.outstanding_amount, "due_date": invoice.due_date, "days": day}
				registers.append(product_arr)

			documents = frappe.get_all("Supplier Documents", ["*"], filters = conditions)	

			for document in documents:
				day = days(document.due_date)
				product_arr = {'indent': 1.0,"date": document.posting_date, "reference_doctype": "Supplier Documents", "reference_name": document.name, "amount":document.total, "outstanding_amount": document.outstanding_amount, "due_date": document.due_date, "days": day}
				registers.append(product_arr)
			
			data.extend(registers or [])

	return columns, data

def days(date):
	today = datetime.now()
	today_str = today.strftime('%Y-%m-%d')
	date_str = date.strftime('%Y-%m-%d')
	today_convert = datetime.strptime(today_str, "%Y-%m-%d")
	date_convert = datetime.strptime(date_str, "%Y-%m-%d")
	diference = date_convert - today_convert

	days = diference.days

	# if today_convert > date_convert:
	# 	days = days * -1

	return days

def get_conditions(filters, from_date, to_date, supplier):
	conditions = ''

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	# conditions += ', "amount_bd": [">", "0"]'
	conditions += ', "supplier": "{}"'.format(supplier)
	conditions += ', "docstatus": ["!=", "0"]'
	conditions += '}'

	return conditions
