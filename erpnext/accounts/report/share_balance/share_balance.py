# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict
from itertools import pairwise

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
	"""Share blocks the shareholder holds on `date`, each at the rate it was last received at.

	A share number is held when it was received more often than sent, so the result does not depend
	on the order the transfers were saved or submitted in."""
	holder = frappe.db.get_value("Shareholder", shareholder, ["name", "is_company", "company"], as_dict=True)
	if not holder:
		return []

	transfers = get_transfers(holder, date, company)
	received = [transfer for transfer in transfers if is_received(transfer, holder)]
	sent = [transfer for transfer in transfers if not is_received(transfer, holder)]

	return [
		get_block(get_last_receipt(received, share_type, from_no, to_no), from_no, to_no)
		for share_type, from_no, to_no in get_held_ranges(received, sent)
	]


def get_transfers(holder, date, company=None):
	share_transfer = frappe.qb.DocType("Share Transfer")
	is_involved = (share_transfer.to_shareholder == holder.name) | (
		share_transfer.from_shareholder == holder.name
	)
	if holder.is_company:
		is_involved |= share_transfer.transfer_type.isin(["Issue", "Purchase"]) & (
			share_transfer.company == holder.company
		)

	query = (
		frappe.qb.from_(share_transfer)
		.select(
			share_transfer.transfer_type,
			share_transfer.share_type,
			share_transfer.from_no,
			share_transfer.to_no,
			share_transfer.no_of_shares,
			share_transfer.rate,
			share_transfer.amount,
			share_transfer.to_shareholder,
		)
		.where((share_transfer.docstatus == 1) & (share_transfer.date <= date) & is_involved)
		.orderby(share_transfer.date)
		.orderby(share_transfer.creation)
	)

	if company:
		query = query.where(share_transfer.company == company)

	return query.run(as_dict=True)


def is_received(transfer, holder):
	if holder.is_company and transfer.transfer_type == "Issue":
		return True

	return transfer.to_shareholder == holder.name


def get_held_ranges(received, sent):
	"""Share number ranges received more often than sent, split at every transfer boundary."""
	changes = defaultdict(int)
	for transfers, sign in ((received, 1), (sent, -1)):
		for transfer in transfers:
			changes[(transfer.share_type, transfer.from_no)] += sign
			changes[(transfer.share_type, transfer.to_no + 1)] -= sign

	held_ranges = []
	held_count = 0
	for (share_type, from_no), (next_share_type, next_no) in pairwise(sorted(changes)):
		held_count += changes[(share_type, from_no)]
		if held_count > 0 and share_type == next_share_type:
			held_ranges.append((share_type, from_no, next_no - 1))

	return held_ranges


def get_last_receipt(received, share_type, from_no, to_no):
	return [
		transfer
		for transfer in received
		if transfer.share_type == share_type and transfer.from_no <= from_no and transfer.to_no >= to_no
	][-1]


def get_block(block, from_no, to_no):
	no_of_shares = to_no - from_no + 1
	return frappe._dict(
		share_type=block.share_type,
		from_no=from_no,
		to_no=to_no,
		no_of_shares=no_of_shares,
		rate=block.rate,
		amount=no_of_shares * block.rate,
	)
