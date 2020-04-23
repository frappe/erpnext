# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _, msgprint

def execute(filters=None):
	if not filters: filters = {}

	columns = [
		{
   			"fieldname": "date",
  			"fieldtype": "Date",
  			"label": "Date",
			"width": 100
  		},
		{
			"fieldname": "rtn",
   			"fieldtype": "Data",
   			"label": "RTN",
			"width": 120
		},
		{
			"fieldname": "name",
   			"fieldtype": "Data",
   			"label": "Name",
			"width": 140
		},
		{
   			"fieldname": "type_document",
  			"fieldtype": "Data",
  			"label": "Type Document",
			"width": 100
  		},
		{
			"fieldname": "document",
   			"fieldtype": "Data",
   			"label": "Document",
			"width": 140
		},
		{
			"fieldname": "total_final",
   			"fieldtype": "Currency",
   			"label": "Total Final",
			"width": 110
		},
		{
			"fieldname": "total",
   			"fieldtype": "Currency",
   			"label": "Total",
			"width": 110
		},
		{
   			"fieldname": "total_exempt",
  			"fieldtype": "Currency",
  			"label": "Total Exempt",
			"width": 110
  		},
		{
			"fieldname": "exonerated",
   			"fieldtype": "Currency",
   			"label": "Exonerated",
			"width": 110
		},
		{
			"fieldname": "base_isv_15%",
   			"fieldtype": "Currency",
   			"label": "Base ISV 15%",
			"width": 110
		},
		{
			"fieldname": "isv_15%",
   			"fieldtype": "Currency",
   			"label": "ISV 15%",
			"width": 110
		}
		,
		{
			"fieldname": "base_isv_18%",
   			"fieldtype": "Currency",
   			"label": "Base ISV 18%",
			"width": 110
		},
		{
			"fieldname": "isv_18%",
   			"fieldtype": "Currency",
   			"label": "ISV 18%",
			"width": 110
		}
	]

	data = []

	conditions = return_filters(filters)
	sales_invoice = frappe.get_all("Sales Invoice", ["name", "posting_date", "rtn", "customer", "type_document", "numeration", "grand_total", "exonerated", "status"], filters = conditions, order_by='numeration')
	for sales in sales_invoice:
		taxes_calculate_15 = 0
		taxes_calculate_18 = 0
		base_15 = 0
		base_18 = 0
		total_exepmt = 0
		amount_exonerated = 0
		total = 0
		if sales.status == "Paid" or sales.status == "Unpaid":
			items = frappe.get_all("Sales Invoice Item", ["item_code", "item_name", "qty", "amount", "discount_amount", "item_tax_template", "purchase_rate"], filters = {"parent": sales.name})
			for invoice_item in items:
				total += invoice_item.amount
				if invoice_item.item_tax_template == None:
					total_exepmt = sales.grand_total
				tax_template = frappe.get_all("Item Tax Template", "name", filters = {"name": invoice_item.item_tax_template})
				for item_tax in tax_template:
					tax_rate = frappe.get_all("Item Tax Template Detail", filters = {"parent": item_tax.name}, fields={"tax_rate"})
					for rate in tax_rate:
						if rate.tax_rate == 15:
							taxes_calculate_15 += rate.tax_rate * invoice_item.amount / 100
							base_15 += invoice_item.amount
						elif rate.tax_rate == 18:
							taxes_calculate_18 += rate.tax_rate * invoice_item.amount / 100
							base_18 += invoice_item.amount
						if sales.exonerated == 1:
							amount_exonerated = sales.grand_total
							taxes_calculate_15 = 0
							taxes_calculate_18 = 0

		elif sales.status == "Cancelled":
			sales.rtn = "**Cancelled**"
			sales.customer = "**Cancelled**"
			sales.grand_total = 0

		row = [
			sales.posting_date,
			sales.rtn,
			sales.customer,
			sales.type_document,
			sales.numeration,
			sales.grand_total,
			total,
			total_exepmt,
			amount_exonerated,
			base_15,
			taxes_calculate_15,
			base_18,
			taxes_calculate_18
		]
		data.append(row)

	return columns, data

def return_filters(filters):
	conditions = ''

	conditions += "{"
	if filters.get("from_date") and filters.get("to_date"):conditions += '"posting_date": [">=", "{}"], "modified": ["<=", "{}"]'.format(filters.get("from_date"), filters.get("to_date"))
	if filters.get("company"): conditions += ', "company": "{}"'.format(filters.get("company"))
	if filters.get("type_document"): conditions += ', "type_document": "{}"'.format(filters.get("type_document"))
	if filters.get("cashier"): conditions += ', "pos": "{}"'.format(filters.get("cashier"))
	if filters.get("branch_office"): conditions += ', "branch_office": "{}"'.format(filters.get("branch_office"))
	conditions += '}'

	return conditions
