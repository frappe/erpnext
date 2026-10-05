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
	"""Share blocks the shareholder holds on `date`, each at the rate it was received at."""
	holder = frappe.db.get_value("Shareholder", shareholder, ["name", "is_company", "company"], as_dict=True)

	blocks = []
	for transfer in get_transfers(holder, date, company):
		if is_received(transfer, holder):
			blocks.append(transfer)
		else:
			blocks = get_remaining_blocks(blocks, transfer)

	return blocks


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
		.orderby(share_transfer.creation)
	)

	if company:
		query = query.where(share_transfer.company == company)

	return query.run(as_dict=True)


def is_received(transfer, holder):
	if holder.is_company and transfer.transfer_type == "Issue":
		return True

	return transfer.to_shareholder == holder.name


def get_remaining_blocks(blocks, transfer):
	"""Blocks left after `transfer` takes its share numbers out; split blocks keep their rate."""
	remaining = []
	for block in blocks:
		if (
			block.share_type != transfer.share_type
			or block.to_no < transfer.from_no
			or block.from_no > transfer.to_no
		):
			remaining.append(block)
			continue

		if block.from_no < transfer.from_no:
			remaining.append(get_block(block, block.from_no, transfer.from_no - 1))
		if block.to_no > transfer.to_no:
			remaining.append(get_block(block, transfer.to_no + 1, block.to_no))

	return remaining


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
