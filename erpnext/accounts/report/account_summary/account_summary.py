# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe import _
import frappe
import datetime
import dateutil.parser

def execute(filters=None):
	columns = get_columns(filters)
	customers = get_customer_data(filters)
	data = get_data(customers, filters)
	return columns, data


def get_columns(filters):
	columns = [
		{
			"label": _("Customer"),
			"fieldtype": "Data",
			"fieldname": "customer",
			"width": 250
		},
		{
			"label": _("Invoice No."),
			"fieldtype": "Data",
			"fieldname": "invoice_no",
			"width": 100
		},
		{
			"label": _("Inv. Date"),
			"fieldtype": "Date",
			"fieldname": "invoice_date",
			"width": 100
		},
		{
			"label": _("Invoice Amount"),
			"fieldtype": "Currency",
			"fieldname": "amount",
			"width": 100
		},
		{
			"label": _("Paid"),
			"fieldtype": "Currency",
			"fieldname": "paid",
			"width": 100
		},
		{
			"label": _("Outstanding"),
			"fieldtype": "Currency",
			"fieldname": "outstanding",
			"width": 100
		},
		{
			"label": _("Days"),
			"fieldtype": "Int",
			"fieldname": "days",
			"width": 100
		}
	]

	return columns

def get_data(customers, filters):

	report_from_date = filters.get("report_from_date")
	report_to_date = filters.get("report_to_date")

	print(report_from_date)
	print(report_to_date)

	customer_header_row = {
		"customer": "",
		"invoice_no": "",
		"invoice_date": "",
		"amount": 0.0,
		"paid": 0.0,
		"outstanding": 0.0,
		"has_value": True,
		"indent":0
	}

	customer_invoice_row = {
		"customer": "",
		"invoice_no": "",
		"invoice_date": "",
		"amount": 0.0,
		"paid": 0.0,
		"outstanding": 0.0,
		"has_value": True,
		"days":0,
		"indent":1
	}

	grand_total = {
		"customer": "Grand Total",
		"amount": 0.0,
		"paid": 0.0,
		"outstanding": 0.0,
		"has_value": True,
		"indent":0
	}

	empty_row = {}

	data = []

	customer_query = """select customer, sum(rounded_total) as rounded_total,sum(rounded_total-outstanding_amount) as paid ,sum(outstanding_amount) as outstanding_amount 
	from `tabSales Invoice`
	where docstatus=1 and creation between CAST(%s AS DATE) AND CAST(%s AS DATE)
	GROUP BY customer order by outstanding_amount desc;"""


	invoice_query = """select name,invoice_no,creation,customer,rounded_total as rounded_total,rounded_total-outstanding_amount as paid,outstanding_amount as outstanding_amount, status, (CASE WHEN status = 'Overdue' THEN (TIMESTAMPDIFF(DAY,creation,NOW())) ELSE 0 END) days
	from `tabSales Invoice` 
	where docstatus=1 and creation between CAST(%s AS DATE) AND CAST(%s AS DATE)
	and customer = %s order by (CASE WHEN status = 'Overdue' THEN (TIMESTAMPDIFF(DAY,creation,NOW())) ELSE 0 END) desc;"""

	

	
	for customer in frappe.db.sql(customer_query, (report_from_date, report_to_date), as_dict=1):
		customer_header_new_row = customer_header_row.copy()
		customer_header_new_row['customer'] = customer.customer
		customer_header_new_row['amount'] = customer.rounded_total
		customer_header_new_row['paid'] = customer.paid
		customer_header_new_row['outstanding'] = customer.outstanding_amount

		grand_total['amount'] = grand_total['amount'] + customer_header_new_row['amount']
		grand_total['paid'] = grand_total['paid'] + customer_header_new_row['paid']
		grand_total['outstanding'] = grand_total['outstanding'] + customer_header_new_row['outstanding']

			
		data.append(customer_header_new_row)
		
		for invoice in frappe.db.sql(invoice_query, (report_from_date, report_to_date, customer.customer), as_dict=1):
			customer_invoice_new_row = customer_invoice_row.copy()
			customer_invoice_new_row['customer'] = ""
			customer_invoice_new_row['invoice_no'] = invoice.invoice_no
			customer_invoice_new_row['invoice_date'] = invoice.creation.date()
			customer_invoice_new_row['amount'] = invoice.rounded_total
			customer_invoice_new_row['paid'] = invoice.paid
			customer_invoice_new_row['outstanding'] = invoice.outstanding_amount
			customer_invoice_new_row['days'] = invoice.days
			customer_invoice_new_row['status'] = invoice.status
			data.append(customer_invoice_new_row)
			
			
		data.append(empty_row)
		
	
	data.append(empty_row)
	data.append(grand_total)
	

	return data


def get_customer_data(filters):
	return frappe.get_all("Customer", fields = ["name","customer_name"], order_by = 'name')

def default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
