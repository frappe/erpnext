# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	if not filters:
		filters = {}

	if not filters.get("date"):
		frappe.throw(_("Please select date"))

	columns = get_columns(filters)

	date = filters.get("date")

	data = []

	if not filters.get("shareholder"):
		pass
	else:
		transfers = get_all_transfers(date, filters.get("shareholder"))
		for transfer in transfers:
			if transfer.transfer_type == "Transfer":
				if transfer.from_shareholder == filters.get("shareholder"):
					transfer.transfer_type += " to {}".format(transfer.to_shareholder)
				else:
					transfer.transfer_type += " from {}".format(transfer.from_shareholder)
			row = [
				filters.get("shareholder"),
				transfer.date,
				transfer.transfer_type,
				transfer.share_type,
				transfer.no_of_shares,
				transfer.rate,
				transfer.amount,
				transfer.company,
				transfer.name,
			]

			data.append(row)

	return columns, data


def get_columns(filters):
	columns = [
		_("Shareholder") + ":Link/Shareholder:150",
		_("Date") + ":Date:100",
		_("Transfer Type") + "::140",
		_("Share Type") + "::90",
		_("No of Shares") + "::90",
		_("Rate") + ":Currency:90",
		_("Amount") + ":Currency:90",
		_("Company") + "::150",
		_("Share Transfer") + ":Link/Share Transfer:90",
	]
	return columns


def get_all_transfers(date, shareholder):
	condition = " "
	# if company:
	# 	condition = 'AND company = %(company)s '
	return frappe.db.sql(
		"""SELECT * FROM `tabShare Transfer`
		WHERE ((DATE(date) <= %(date)s AND from_shareholder = %(shareholder)s {condition})
		OR (DATE(date) <= %(date)s AND to_shareholder = %(shareholder)s {condition}))
		AND docstatus = 1
		ORDER BY date""".format(
			condition=condition
		),
		{"date": date, "shareholder": shareholder},
		as_dict=1,
	)
