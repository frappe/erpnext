# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _, msgprint

def execute(filters=None):
	if not filters: filters = {}
	# Columns of data
	columns = [
		_("Item Code") + "::120", _("Item Name") + "::200", _("Item Group") + "::200", _("Quantity") + "::60", _("Total Sale") + ":Currency:110", _("Gross Amount") + ":Currency:110",
		_("Discounts") + ":Currency:110", _("ISV") + ":Currency:110", _("Costo") + ":Currency:110",
		_("Utility") + ":Currency:110"
	]

	# Declarate array
	data = []
	registers = []

	conditions = return_filters(filters)
	sales_invoice = frappe.get_all("Sales Invoice", ["name", "status"], filters = conditions)
	rate = 0
	for sales in sales_invoice:
		if sales.status == "Paid" or sales.status == "Unpaid":
			filters_item = get_item(filters, sales.name)
			items = frappe.get_all("Sales Invoice Item", ["item_code", "item_name", "qty", "amount", "discount_amount", "item_tax_template", "purchase_rate", "item_group"], filters = filters_item)
			for invoice_item in items:
				result_tax = 0
				tax_template = frappe.get_all("Item Tax Template", "name", filters = {"name": invoice_item.item_tax_template})
				for item_tax in tax_template:
					tax_rate = frappe.get_all("Item Tax Template Detail", filters = {"parent": item_tax.name}, fields={"tax_rate"})
					for rate in tax_rate:
						result_tax = rate.tax_rate

				# Calculate data
				rate_purchase = invoice_item.qty * invoice_item.purchase_rate
				taxes_calculate = result_tax * invoice_item.amount / 100
				total_sale = invoice_item.amount + taxes_calculate  
				discount = invoice_item.discount_amount * invoice_item.qty
				utility = invoice_item.amount - rate_purchase
				# utility = invoice_item.amount - utility_initial

				acc = 0
				if len(registers) > 0:
					for select in registers:
						acc += 1
						if select[0] == invoice_item.item_code:
							select[3] += invoice_item.qty
							select[4] += total_sale
							select[5] += invoice_item.amount
							select[6] += discount
							select[7] += taxes_calculate
							select[8] += rate_purchase
							select[9] += utility
							acc -= 1
					
						if acc == len(registers):
							json = [
								invoice_item.item_code,
								invoice_item.item_name,
								invoice_item.item_group,
								invoice_item.qty,
								total_sale,
								invoice_item.amount,
								discount,
								taxes_calculate,
								rate_purchase,
								utility
							]
							registers.append(json)
							break
				else:
					new = [
						invoice_item.item_code,
						invoice_item.item_name,
						invoice_item.item_group,
						invoice_item.qty,
						total_sale,
						invoice_item.amount,
						discount,
						taxes_calculate,
						rate_purchase,
						utility
					]
					registers.append(new)

	for reg in registers:
		row = [reg[0], reg[1], reg[2], reg[3], reg[4], reg[5], reg[6], reg[7], reg[8], reg[9]]
		data.append(row)
	return columns, data

def return_filters(filters):
	conditions = ''

	conditions += "{"
	if filters.get("from_date") and filters.get("to_date"):conditions += '"posting_date": [">=", "{}"], "modified": ["<=", "{}"]'.format(filters.get("from_date"), filters.get("to_date"))
	if filters.get("company"): conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += '}'

	return conditions

def get_item(filters, sales):
	conditions = ''

	conditions += '{'
	conditions += '"parent": "{}"'.format(sales)
	if filters.get("item_code"): conditions += ', "item_code": "{}"'.format(filters.get("item_code"))
	if filters.get("item_group"): conditions += ', "item_group": "{}"'.format(filters.get("item_group"))
	conditions += "}"

	return conditions

