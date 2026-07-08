# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	if not filters:
		filters = {}

	if not filters.get("date"):
		frappe.throw(_("Please select date"))

	columns = get_columns(filters)

	data = []

	if not filters.get("shareholder"):
		pass
	else:
		share_type, no_of_shares, rate, amount = 1, 2, 3, 4

		all_shares = get_all_shares(filters.get("shareholder"), filters.get("date"), filters.get("company"))
		for share_entry in all_shares:
			row = False
			for datum in data:
				if datum[share_type] == share_entry.share_type:
					datum[no_of_shares] += share_entry.no_of_shares
					datum[amount] += share_entry.amount
					if datum[no_of_shares] == 0:
						datum[rate] = 0
					else:
						datum[rate] = datum[amount] / datum[no_of_shares]
					row = True
					break
			# new entry
			if not row:
				row = [
					filters.get("shareholder"),
					share_entry.share_type,
					share_entry.no_of_shares,
					share_entry.rate,
					share_entry.amount,
				]

				data.append(row)

	return columns, data


def get_columns(filters):
	columns = [
		_("Shareholder") + ":Link/Shareholder:150",
		_("Share Type") + "::90",
		_("No of Shares") + "::90",
		_("Average Rate") + ":Currency:90",
		_("Amount") + ":Currency:90",
	]
	return columns


def get_all_shares(shareholder, date, company=None):
	"""Share movements for the shareholder up to (and including) `date`, signed by direction:
	shares received are positive, shares transferred/sold out are negative.

	The shareholder and company predicates are pushed into the query so only the
	relevant transfers are fetched instead of scanning the whole table."""
	share_transfer = frappe.qb.DocType("Share Transfer")
	query = (
		frappe.qb.from_(share_transfer)
		.select(
			share_transfer.share_type,
			share_transfer.no_of_shares,
			share_transfer.rate,
			share_transfer.amount,
			share_transfer.from_shareholder,
			share_transfer.to_shareholder,
		)
		.where((share_transfer.docstatus == 1) & (share_transfer.date <= date))
		.where(
			(share_transfer.to_shareholder == shareholder) | (share_transfer.from_shareholder == shareholder)
		)
		.orderby(share_transfer.date)
	)

	if company:
		query = query.where(share_transfer.company == company)

	transfers = query.run(as_dict=True)

	shares = []
	for transfer in transfers:
		if transfer.to_shareholder == shareholder:
			shares.append(transfer)
		elif transfer.from_shareholder == shareholder:
			shares.append(
				frappe._dict(
					share_type=transfer.share_type,
					no_of_shares=-transfer.no_of_shares,
					rate=transfer.rate,
					amount=-transfer.amount,
				)
			)

	return shares
