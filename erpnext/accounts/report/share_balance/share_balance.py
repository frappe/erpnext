# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _

def execute(filters=None):
	if not filters: filters = {}

	if not filters.get("date"):
		frappe.throw(_("Please select date"))
	
	columns = get_columns(filters)
	
	date = filters.get("date")
	
	company = None
	if filters.get("company"):
		company = filters.get("company")

	data = []

	if not filters.get("shareholder"):
		pass
	else:
		transfers = get_all_transfers(date, filters.get("shareholder"), company)
		transfer_type, share_type, no_of_shares, rate, amount, company = 1, 2, 3, 4, 5, 6
		for transfer in transfers:
			row = None
			for datum in data:
				if datum[company] == transfer.company and datum[share_type] == transfer.share_type:
					if transfer.to_shareholder == filters.get("shareholder"):
						datum[no_of_shares] += transfer.no_of_shares
						datum[amount] += transfer.amount
						datum[rate]    =  datum[amount] / ( datum[no_of_shares] + transfer.no_of_shares ) 
					else:
						print ("\n\n\n\n\n\n\nHERE\n\n\n\n\n\n")
						datum[no_of_shares] -= transfer.no_of_shares
						datum[amount] -= transfer.amount
						datum[rate]    =  datum[amount] / ( datum[no_of_shares] - transfer.no_of_shares ) 
					row = 'already exists'
					break
			# new entry
			if not row:
				row = [filters.get("shareholder"), transfer.transfer_type,
					transfer.share_type, transfer.no_of_shares, transfer.rate, transfer.amount,
					transfer.company]
				data.append(row)

	return columns, data

def get_columns(filters):
	columns = [ 
		_("Shareholder") + ":Link/Shareholder:150", 
		_("Transfer Type") + "::140",
		_("Share Type") + "::90",
		_("No of Shares") + "::90", 
		_("Average Rate") + "::90",
		_("Amount") + "::90",
		_("Company") + "::150"
	]
	return columns

def get_all_transfers(date, shareholder, company):
	if company:
		condition = 'AND company = %(company)s '
	else:
		condition = ' '

	return frappe.db.sql("""SELECT * FROM `tabShare Transfer` 
		WHERE (DATE(date) <= %(date)s AND from_shareholder = %(shareholder)s {condition})
		OR (DATE(date) <= %(date)s AND to_shareholder = %(shareholder)s {condition})
		ORDER BY date""".format(condition=condition), 
		{'date': date, 'shareholder': shareholder, 'company': company}, as_dict=1)
