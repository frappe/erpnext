# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, getdate
from frappe import msgprint, _

def execute(filters=None):
	if not filters: filters = {}

	if not filters.get("date"):
		msgprint(_("Please select date"), raise_exception=1)
	
	columns = get_columns(filters)
	
	date = filters.get("date")
	company = '*'
	if filters.get("company"):
		company = filters.get("company")

	data = []
	
	if not filters.get("shareholder"):
		pass
	else:
		transfers = get_all_transfers(date, filters.get("shareholder"), company)
		for transfer in transfers:
			row = [filters.get("shareholder"), transfer.date, transfer.transfer_type,
				transfer.share_type, transfer.no_of_shares, transfer.rate, transfer.amount,
				transfer.company]
			
			data.append(row)

	return columns, data

def get_columns(filters):
	columns = [ 
		_("Shareholder") + ":Link/Shareholder:150", 
		_("Date") + "::100",
		_("Transfer Type") + "::140",
		_("Share Type") + "::90",
		_("No of Shares") + "::90", 
		_("Rate") + "::90",
		_("Amount") + "::90",
		_("Company") + "::150",
	]
	return columns

def get_all_transfers(date, shareholder, company):
	return frappe.db.sql("""SELECT * FROM `tabShare Transfer` 
		WHERE (DATE(date) <= %s AND from_shareholder = %s AND company = %s)
		OR (DATE(date) <= %s AND to_shareholder = %s AND company = %s)
		ORDER BY date""", (date, shareholder, company, date, shareholder, company), as_dict=1)
