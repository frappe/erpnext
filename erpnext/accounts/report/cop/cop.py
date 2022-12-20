# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.report.financial_statements import (get_period_list, get_columns, get_data)
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import get_net_profit_loss
from erpnext.accounts.report.cop_computation_report.cop_computation_report import get_data

def execute(filters):
	operation_accounts = {
		"section_name": "Operations",
		"section_footer": _("Cost Per MT Finished Products"),
		"section_header": _("Cost Per MT Finished Products"),
		"account_types": [
			{"acc_name": "mining_expenses", "label": _("Mining Cost per MT")},
			{"acc_name": "crushing_plant_expenses1", "label": _("Cost per MT Crushing Plant 1")},
			{"acc_name": "crushing_plant_expenses2", "label": _("Cost per MT Crushing Plant 2")},
			{"acc_name": "washed_expenses", "label": _("Cost Per MT Washed")}
		]
	}

	investing_accounts = {
		"section_name": "Investing",
		"section_footer": _("Cost per MT Finished Products at Stock Yard"),
		"section_header": _("Cost per MT Finished Products at Stock Yard"),
		"account_types": [
			{"acc_name": "transportation", "label": _("Transportaion to Stockyard Cost per MT")}
		]
	}

	financing_accounts = {
		"section_name": "Financing",
		"section_footer": _("Cost per MT of Product sold"),
		"section_header": _("Cost per MT of Product sold"),
		"account_types": [
			{"acc_name": "s_and_d", "label": _("Selling & Distribution Cost per MT ")}
		]
	}

	# combine all cash flow accounts for iteration
	cash_flow_accounts = []
	cash_flow_accounts.append(operation_accounts)
	cash_flow_accounts.append(investing_accounts)
	cash_flow_accounts.append(financing_accounts)

	data = []
	company_currency = frappe.db.get_value("Company", filters.company, "default_currency")
	row = {}
	amt = prepare_data(filters)
	for a in cash_flow_accounts:
		section_data = []
		data.append({
			"account_name": a['section_header'],
			"parent_account": None,
			"indent": 0.0,
			"account": a['section_header']
		})
		for account in a['account_types']:
			data.append({
				"account_name": account['label'],
				"indent": 1,
				"parent_account": a['section_header'],
				"currency": company_currency,
				"amount": amt.get(account['acc_name'], 0.0)
			})
		add_total_row_account(data, a['section_footer'],
		a['account_types'][0]['acc_name'], company_currency)
	columns = get_columns(filters)

	return columns, data

def prepare_data(filters):
	da = get_data(filters)
	amt = 0.0
	activity_list = ("total_exp", 'mining_expenses', 'crushing_plant_expenses1', 'crushing_plant_expenses2', 'washed_expenses', 'transportation', 's_and_d')
	dic = {}
	for act in activity_list:
		amt = 0.0
		if da:
			for a in da:
				amt  += flt(a.get(act, 0.0), 2)
				dic.setdefault(act, amt)
	return dic

def get_columns(filters):
	return [
		{
			"fieldname": "account",
			"label": _("Particular"),
			"fieldtype": "Data",
			"width": 350
		},
		{
			"fieldname": "amount",
			"label": _("Cost Per MT"),
			"fieldtype": "Currency",
			"width": 120
		}
	]


def add_total_row_account(data, label, acc_name, currency):
	total_row = {
		"account_name": "" + _("<i style='color:blue'>  {0} </i> ").format(label) + "",
		"account": None,
		"currency": currency,
	}
	for row in data:
		if row.get("parent_account"):
			total_row.setdefault(acc_name, 0.0)
			total_row[acc_name] += row.get(acc_name, 0.0)
			
			total_row.setdefault("amount", 0.0)
			total_row["amount"] += row["amount"]

	data.append(total_row)
	data.append({})
