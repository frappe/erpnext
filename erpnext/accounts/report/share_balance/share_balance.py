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

	data = []

	if not filters.get("shareholder_party"):
		pass
	else:
		transfers = get_all_transfers(date, filters.get("shareholder_party"))
		share_type, no_of_shares, rate, amount, company = 1, 2, 3, 4, 5
		for transfer in transfers:
			row = False
			for datum in data:
				if datum[company] == transfer.company and datum[share_type] == transfer.share_type:
					if transfer.to_party == filters.get("shareholder_party"):
						datum[no_of_shares] += transfer.no_of_shares
						datum[amount] += transfer.amount
						if datum[no_of_shares] == 0:
							datum[rate] = 0
						else:
							datum[rate] = datum[amount] / datum[no_of_shares]
					else:
						datum[no_of_shares] -= transfer.no_of_shares
						datum[amount] -= transfer.amount
						if datum[no_of_shares] == 0:
							datum[rate] = 0
						else:
							datum[rate] = datum[amount] / datum[no_of_shares]
					row = True
					break
			# new entry
			if not row:
				if transfer.to_party == filters.get("shareholder_party"):
					row = [filters.get("shareholder_party"),
						transfer.share_type, transfer.no_of_shares, transfer.rate, transfer.amount,
						transfer.company]
				else:
					row = [filters.get("shareholder_party"),
						transfer.share_type, -transfer.no_of_shares, -transfer.rate, -transfer.amount,
						transfer.company]
				data.append(row)
				
		data = [datum for datum in data if datum[no_of_shares] > 0]

	return columns, data

def get_columns(filters):
	columns = [
		_("Shareholder") + ":Link/Shareholder Party:150",
		_("Share Type") + "::90",
		_("No of Shares") + "::90",
		_("Average Rate") + ":Currency:90",
		_("Amount") + ":Currency:90",
		_("Company") + "::150"
	]
	return columns

def get_all_transfers(date, party):
	condition = ' '
	# if company:
	# 	condition = 'AND company = %(company)s '
	return frappe.db.sql("""SELECT * FROM `tabShare Transfer`
		WHERE (DATE(date) <= %(date)s AND from_party = %(party)s {condition})
		OR (DATE(date) <= %(date)s AND to_party = %(party)s {condition})
		ORDER BY date""".format(condition=condition),
		{'date': date, 'party': party}, as_dict=1)
