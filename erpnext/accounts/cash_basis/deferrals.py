# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Deferred revenue and deferred expense on the cash basis (phase 7).

On the cash basis, the income or expense of a deferred item is recognised on payment, as any
convertible line. The row of the invoice on the deferred account becomes the line: its
deferral removes it on the invoice date, and its recognition goes to the income or expense
account of the item. The schedule (the rows that move the deferred account to the income or
expense account) is removed on its own dates.

The schedule rows come in two shapes:
- GL rows of the invoice with against_voucher_type "Process Deferred Accounting";
- Journal Entries of the type "Deferred Revenue" or "Deferred Expense", with the invoice as
  the against voucher ("Book Deferred Entries Via Journal Entry").
"""

from dataclasses import dataclass

from frappe.utils import flt

DEFERRAL_JOURNAL_TYPES = ("Deferred Revenue", "Deferred Expense")


@dataclass
class DeferredItem:
	"""An invoice item with a deferred account, from the item rows of the invoice."""

	name: str  # the item row
	deferred_account: str
	account: str  # the income or expense account of the item
	cost_center: str | None
	amount: float  # the amount of its GL row on the deferred account, company currency
	# The project and the accounting dimensions of its GL row: of the item, else of the invoice.
	dimensions: dict


@dataclass
class DeferredPiece:
	"""A part of a GL row on a deferred account, for one income or expense account."""

	row: object
	account: str
	amount: float  # GL sign, company currency


def split_deferred_rows(balance_rows, items, precision, is_return=False) -> tuple[list, list] | None:
	"""Split the rows of the invoice on its deferred accounts between the accounts of the items.

	Returns the pieces and the balance rows that stay balance rows. Returns None when an item of
	an invoice has no row on its deferred account, so the voucher stays an exception.

	A return posts a deferred item to the deferred account or to the income or expense account,
	item by item. Its row on the deferred account names the item in voucher_detail_no. An item
	of a return with no such row is an ordinary convertible line.
	"""
	pieces, remaining = [], []
	matched_items = set()
	for row in balance_rows:
		matches = [
			(index, item)
			for index, item in enumerate(items)
			if flt(item.amount, precision)
			and item.deferred_account == row.account
			and item_matches_row(item, row, is_return)
		]
		if not matches:
			remaining.append(row)
			continue
		matched_items.update(index for index, _item in matches)
		pieces.extend(split_row(row, [item for _index, item in matches], precision))
	# An item with no amount (fully discounted) has no GL row.
	expected = {index for index, item in enumerate(items) if flt(item.amount, precision)}
	if not is_return and not expected <= matched_items:
		return None
	return pieces, remaining


def item_matches_row(item, row, is_return) -> bool:
	if is_return and row.get("voucher_detail_no"):
		return row.voucher_detail_no == item.name
	if (item.cost_center or None) != (row.cost_center or None):
		return False
	return all((value or None) == (row.get(field) or None) for field, value in item.dimensions.items())


def split_row(row, items, precision) -> list[DeferredPiece]:
	"""The pieces of one row, in proportion to the item amounts. The last piece takes the rest."""
	amount = flt(row.debit) - flt(row.credit)
	by_account = {}
	for item in items:
		by_account[item.account] = by_account.get(item.account, 0.0) + flt(item.amount)
	total = sum(by_account.values())
	pieces, given = [], 0.0
	accounts = sorted(by_account)
	for index, account in enumerate(accounts):
		if index == len(accounts) - 1:
			part = flt(amount - given, precision)
		else:
			part = flt(amount * by_account[account] / total, precision) if total else 0.0
		given += part
		pieces.append(DeferredPiece(row, account, part))
	return pieces
