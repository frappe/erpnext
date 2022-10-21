# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from datetime import datetime

def execute(filters=None):
	if not filters: filters = {}
	columns = [
		{
   			"fieldname": "date",
  			"fieldtype": "Data",
  			"label": "Date",
  		},
		{
			"fieldname": "document",
   			"fieldtype": "Link",
   			"label": "Document",
			"options": "Bank Transactions"
		},
		{
			"fieldname": "document_number",
   			"fieldtype": "data",
   			"label": "Document Number"
		},
		{
   			"fieldname": "party",
  			"fieldtype": "Data",
  			"label": "Party",
  		},
		{
   			"fieldname": "debits",
  			"fieldtype": "Currency",
  			"label": "Debits",
  		},
		{
   			"fieldname": "credits",
  			"fieldtype": "Currency",
  			"label": "Credits",
  		},
		{
   			"fieldname": "balances",
  			"fieldtype": "Currency",
  			"label": "Balances",
  		}
	]
	data = []

	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")

	##Bank Deposit
	conditions_deposit = get_conditions_deposit(filters, from_date, to_date)

	deposits = frappe.get_all("Bank Transactions", ["*"], filters = conditions_deposit)

	balances = 0

	debits_totals = 0
	credits_totals = 0

	for deposit in deposits:
		if deposit.credit_note == 1 or deposit.bank_deposit == 1:
			credits_totals += deposit.amount_data
			balances += deposit.amount_data
			product_arr = {"date": deposit.date_data, "document": deposit.name, "document_number": deposit.transaction_number, "party": deposit.person_name, "credits": deposit.amount_data, "balances": balances}
			data.append(product_arr)
		else:
			debits_totals += deposit.amount_data
			balances -= deposit.amount_data
			product_arr = {"date": deposit.date_data, "document": deposit.name, "document_number": deposit.transaction_number, "party": deposit.person_name, "debits": deposit.amount_data, "balances": balances}
			data.append(product_arr)	

	balance_total = credits_totals - debits_totals
	group_arr = {"document": "Total", "debits": debits_totals, "credits": credits_totals, "balances": balance_total}
	data.append(group_arr)	

	return columns, data

def sortByDate(elem):
	return datetime.strptime(elem[1], '%Y/%m/%d')

def get_conditions_deposit(filters, from_date, to_date):
	conditions = ''

	conditions += "{"
	conditions += '"date_data": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "bank_account": "{}"'.format(filters.get("bank_account"))
	conditions += ', "docstatus": ["!=", "0"]'
	conditions += '}'

	return conditions
