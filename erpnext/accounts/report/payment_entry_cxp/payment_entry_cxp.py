# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
import datetime

def execute(filters=None):
	if not filters: filters = {}
	columns = [_("Date") + "::240", _("Serie") + "::240", _("Supplier") + "::240", _("CAI") + "::240", _("Transaction Number") + "::240", _("Company") + "::240", _("Reason Debit Note") + "::240",  _("Total References") + ":Currency:120", _("Total Exempt") + ":Currency:120", _("Isv 18%") + ":Currency:120",_("Isv 15%") + ":Currency:120",_("Amount Total") + ":Currency:120"]
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []
	dates = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)

	registers = frappe.get_all("Debit Note CXP", ["*"], filters = conditions,  order_by = "name asc")

	for register in registers:
		row = [register.posting_date, register.name, register.supplier, register.cai, register.transaction_number, register.company, register.reason_debit_note, register.total_references, register.total_exempt, register.isv_18, register.isv_15, register.total_amount]
		data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "company": "{}"'.format(filters.get("company"))
	if filters.get("supplier"): conditions += ', "supplier": "{}"'.format(filters.get("supplier"))
	if filters.get("reason"): conditions += ', "reason_debit_note": "{}"'.format(filters.get("reason"))
	conditions += '}'

	return conditions