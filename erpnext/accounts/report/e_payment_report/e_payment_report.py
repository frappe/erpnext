# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if filters.payment_type == "Bank Payment":
		columns, data = get_column(), get_data(filters)
	else:
		columns, data = get_utility_column(), get_utility_data(filters)
	return columns, data

def get_column():
	columns = [
		("Transaction") + ":Link/Bank Payment:100",
		("Transaction Type") + ":Data:150",
		("Transaction ID") + ":Data:150",
		("Transaction Date") + ":Date:100",
		("Transaction Reference") + ":Data:100",
		("Supplier") + ":Link/Supplier:120",
		("Beneficiary Name") + ":Data:150",
		("Beneficiary Bank Acc No.") + ":Data:150",
		("Total Amount") + ":Currency:100",
		("Status") + ":Data:100",
		("Journal No.") + ":Data:100",
		("PI Number") + ":Data:100"
	]
	return columns

def get_data(filters):
	cond = get_condition(filters)
	data = frappe.db.sql("""
		SELECT 
			bp.name, bpi.transaction_type, bpi.transaction_id, bpi.transaction_date, bpi.transaction_reference, bpi.supplier, bpi.beneficiary_name, bpi.bank_account_no, bpi.amount, bpi.status, bpi.bank_journal_no, bpi.pi_number
		FROM `tabBank Payment` bp, `tabBank Payment Item` bpi
		WHERE bp.name=bpi.parent
		{condition}
	""".format(condition=cond))
	return data

def get_utility_column():
	columns = [
		("Utility Service Type") + ":Data:150",
		("Party") + ":Data:150",
		("Branch Expense Account") + ":Data:200",
		("Paid From Bank Account") + ":Data:200",
		("Debit Account") + ":Link/Account:200",
		("Unique Identity Code") + ":Data:100",
		("Outstanding Amount") + ":Data:100",
		("Payment Status") + ":Data:100",
		("Payment API Response") + ":Data:400",
		("Create Direct Payment") + ":Check:100",
		("TDS Applicable") + ":Check:100",
		("PI Number")
	]
	return columns

def get_utility_data(filters):
	cond = get_condition(filters)
	data = frappe.db.sql("""
		SELECT 
			uti.utility_service_type, uti.party, ut.expense_account, ut.bank_account, uti.debit_account, uti.consumer_code, uti.outstanding_amount, uti.payment_status, uti.payment_response_msg, uti.create_direct_payment, uti.tds_applicable, uti.pi_number
		FROM `tabUtility Bill` ut, `tabUtility Bill Item` uti 
		WHERE ut.name=uti.parent
		{condition}
	""".format(condition=cond))
	return data

def get_condition(filters):
	conds = ""
	if filters.transaction_type:
		conds += "and bpi.transaction_type='{}'".format(filters.transaction_type)
	if filters.supplier:
		conds += "and bpi.supplier='{}'".format(filters.supplier)
	if filters.status:
		conds += "and bpi.status='{}'".format(filters.status)
	if filters.party:
		conds = "and uti.party='{}'".format(filters.party)
	if filters.branch:
		if filters.payment_type == "Bank Payment":
			conds = "and bp.branch = '{}'".format(filters.branch)
		else:
			conds = "and ut.branch = '{}'".format(filters.branch)
	return conds