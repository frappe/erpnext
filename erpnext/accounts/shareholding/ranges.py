# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Validate ownership and recover historical values for numbered shares."""

from collections import defaultdict
from itertools import pairwise

import frappe
from frappe import _
from frappe.utils import cint, flt


def range_has_coverage(
	company,
	share_class,
	from_share_number,
	to_share_number,
	expected_coverage,
	share_folio=None,
	exclude_transaction=None,
):
	"""Return whether every share number in a range has the expected ledger balance."""
	entries = get_range_entries(
		company, share_class, from_share_number, to_share_number, share_folio, exclude_transaction
	)
	if expected_coverage == 0:
		reversed_entries = {entry.reversal_of for entry in entries if entry.is_reversal}
		if any(
			entry.transaction_type == "Issue"
			and not entry.is_reversal
			and entry.quantity_change > 0
			and entry.name not in reversed_entries
			for entry in entries
		):
			return False

	start = cint(from_share_number)
	end = cint(to_share_number)
	events = defaultdict(int)
	events[start] += 0
	events[end + 1] += 0
	for entry in entries:
		entry_start = max(start, cint(entry.from_share_number))
		entry_end = min(end, cint(entry.to_share_number))
		direction = 1 if cint(entry.quantity_change) > 0 else -1
		events[entry_start] += direction
		events[entry_end + 1] -= direction

	coverage = 0
	points = sorted(events)
	for index, point in enumerate(points[:-1]):
		coverage += events[point]
		if points[index + 1] > point and coverage != expected_coverage:
			return False
	return True


def get_face_value_per_share(
	company, share_class, share_folio, from_share_number, to_share_number, *, allow_unknown=False
):
	"""Resolve face value across all current ledger intervals, not just one entry.

	A transaction may span multiple prior issues or transfers. Reversals and
	outgoing movements must be included so that only the currently held layer
	of each share number contributes to its face value.
	"""
	entries = get_range_entries(company, share_class, from_share_number, to_share_number, share_folio)

	start = cint(from_share_number)
	end = cint(to_share_number)
	events = defaultdict(lambda: defaultdict(int))
	events[start]
	events[end + 1]
	for entry in entries:
		entry_start = max(start, cint(entry.from_share_number))
		entry_end = min(end, cint(entry.to_share_number))
		face_value = flt(entry.face_value_per_share)
		direction = 1 if cint(entry.quantity_change) > 0 else -1
		events[entry_start][face_value] += direction
		events[entry_end + 1][face_value] -= direction

	active = defaultdict(int)
	selected_face_value = None
	points = sorted(events)
	for index, point in enumerate(points[:-1]):
		for face_value, change in events[point].items():
			active[face_value] += change
		if points[index + 1] <= point:
			continue
		current = [value for value, quantity in active.items() if quantity]
		if (
			len(current) != 1
			or active[current[0]] != 1
			or current[0] < 0
			or (current[0] == 0 and not allow_unknown)
		):
			frappe.throw(_("Could not determine the face value for the selected share range."))
		if selected_face_value is None:
			selected_face_value = current[0]
		elif selected_face_value != current[0]:
			frappe.throw(
				_("The selected range contains shares with different face values. Use separate transactions.")
			)

	return selected_face_value


def get_treasury_cost_per_share(
	company,
	share_class,
	share_folio,
	from_share_number,
	to_share_number,
	exclude_share_transaction=None,
):
	"""Return one historical treasury cost per share for the complete range.

	A single Share Transaction cannot combine treasury lots carrying different costs;
	the user must post those lots as separate transactions.
	"""
	entries = get_range_entries(
		company, share_class, from_share_number, to_share_number, share_folio, exclude_share_transaction
	)

	start = cint(from_share_number)
	end = cint(to_share_number)
	events = defaultdict(lambda: [0, 0.0])
	events[start]
	events[end + 1]
	for entry in entries:
		entry_start = max(start, cint(entry.from_share_number))
		entry_end = min(end, cint(entry.to_share_number))
		entry_quantity = abs(cint(entry.quantity_change))
		if not entry_quantity:
			continue

		cost_change = flt(entry.treasury_cost_change)

		quantity_direction = 1 if cint(entry.quantity_change) > 0 else -1
		cost_per_share_change = cost_change / entry_quantity
		events[entry_start][0] += quantity_direction
		events[entry_start][1] += cost_per_share_change
		events[entry_end + 1][0] -= quantity_direction
		events[entry_end + 1][1] -= cost_per_share_change

	coverage = 0
	cost_per_share = 0.0
	selected_cost = None
	points = sorted(events)
	for index, point in enumerate(points[:-1]):
		coverage += events[point][0]
		cost_per_share += events[point][1]
		if points[index + 1] <= point:
			continue
		if coverage != 1 or cost_per_share <= 0:
			frappe.throw(_("Could not determine treasury cost for the complete selected share range."))
		if selected_cost is None:
			selected_cost = cost_per_share
		elif abs(selected_cost - cost_per_share) > 0.000001:
			frappe.throw(
				_(
					"The selected range contains treasury shares with different costs. Use separate transactions."
				)
			)

	return flt(selected_cost)


def get_treasury_cost(company, share_class, share_folio, start, end, currency, exclude_transaction=None):
	"""Allocate a lot's rounded cost by cumulative share-number boundaries."""
	from erpnext.accounts.shareholding.posting import money

	if not range_has_coverage(company, share_class, start, end, 1, share_folio, exclude_transaction):
		frappe.throw(_("The treasury folio does not own the complete selected share range."))
	entries = get_range_entries(company, share_class, start, end, share_folio, exclude_transaction)
	points = sorted(
		{cint(start), cint(end) + 1}
		| {
			point
			for entry in entries
			for point in (
				max(cint(start), cint(entry.from_share_number)),
				min(cint(end), cint(entry.to_share_number)) + 1,
			)
		}
	)
	cost = 0
	for left, right in pairwise(points):
		lot = get_active_treasury_lot(entries, left, right - 1)
		quantity = abs(cint(lot.quantity_change))
		cost += money(
			flt(lot.treasury_cost_change) * (right - lot.from_share_number) / quantity, currency
		) - money(flt(lot.treasury_cost_change) * (left - lot.from_share_number) / quantity, currency)
	cost = money(cost, currency)
	if cost < 0:
		frappe.throw(_("Could not determine treasury cost for the complete selected share range."))
	return cost


def get_active_treasury_lot(entries, start, end):
	"""Retain acquisition boundaries when a disposal is cancelled or numbers are reused."""
	active = None
	removed = {}
	for entry in entries:
		if entry.from_share_number > start or entry.to_share_number < end:
			continue
		if entry.quantity_change < 0:
			removed[entry.name] = active
			active = None
		elif entry.is_reversal:
			active = removed.get(entry.reversal_of)
		else:
			active = entry
	if not active:
		frappe.throw(_("Could not determine the original treasury acquisition for this range."))
	return active


def get_range_entries(company, share_class, start, end, folio=None, exclude_transaction=None):
	"""Read all signed movements overlapping a numbered interval."""
	entry = frappe.qb.DocType("Share Ledger Entry")
	query = (
		frappe.qb.from_(entry)
		.select(
			entry.name,
			entry.from_share_number,
			entry.to_share_number,
			entry.quantity_change,
			entry.face_value_per_share,
			entry.treasury_cost_change,
			entry.transaction_type,
			entry.is_reversal,
			entry.reversal_of,
		)
		.where(
			(entry.company == company)
			& (entry.share_class == share_class)
			& (entry.from_share_number <= cint(end))
			& (entry.to_share_number >= cint(start))
		)
	)
	if folio:
		query = query.where(entry.share_folio == folio)
	if exclude_transaction:
		query = query.where(
			entry.share_transaction.isnull() | (entry.share_transaction != exclude_transaction)
		)
	return query.orderby(entry.creation).orderby(entry.posting_sequence).for_update().run(as_dict=True)
