# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Replay submitted Share Transfers into ownership history, without reposting accounting.

The old Purchase operation removed shares from circulation. It is deliberately
not mapped to a treasury-share Buyback. Class terms cannot be inferred from the
old Share Type, so an explicit Share Class mapping is required before replay.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt


def execute():
	run_backfill(fail_on_unresolved=False)


def run_backfill(fail_on_unresolved=True):
	"""Run again after mapping legacy types if the first migrate reported a pending backfill."""
	if not frappe.db.table_exists("Share Transfer", cached=False):
		return

	transfers = get_submitted_transfers()
	if not transfers:
		unstaged_balances = (
			frappe.db.table_exists("Share Balance", cached=False)
			and not frappe.db.table_exists("Shareholding Legacy Balance Staging", cached=False)
			and frappe.db.exists("Share Balance", {"parenttype": "Shareholder"})
		)
		staged_balances = (
			frappe.db.table_exists("Shareholding Legacy Staging", cached=False)
			and frappe.db.table_exists("Shareholding Legacy Balance Staging", cached=False)
			and frappe.db.sql(
				"""
			select balance.name
			from `tabShareholding Legacy Balance Staging` balance
			inner join `tabShareholding Legacy Staging` holder on holder.name = balance.parent
			where holder.is_company = 0 and balance.is_company = 0
			limit 1
			"""
			)
		)
		if unstaged_balances or staged_balances:
			message = "Legacy balances exist without submitted Share Transfers; approve an opening balance."
			if fail_on_unresolved:
				frappe.throw(_(message))
			frappe.log_error(message=message, title="Shareholding Legacy Backfill Pending")
			print(message)
		return

	try:
		for doctype in ("Share Class", "Share Folio", "Share Ledger Entry"):
			if not frappe.db.table_exists(doctype, cached=False):
				frappe.throw(_("Cannot migrate Share Transfers before {0} is available.").format(doctype))
		for table in ("Shareholding Legacy Staging", "Shareholding Legacy Balance Staging"):
			if not frappe.db.table_exists(table, cached=False):
				frappe.throw(_("Cannot migrate Share Transfers without the {0} snapshot.").format(table))

		classes = get_class_mappings()
		folios = get_folios()
		validate_no_new_postings(transfers)
		prepared, final_ranges = prepare_transfers(transfers, classes, folios)
		reconcile_legacy_balances(final_ranges)
	except frappe.ValidationError as exc:
		if fail_on_unresolved:
			raise
		message = (
			f"Legacy Share Transfer backfill is pending: {exc}. "
			"New Share Transactions are blocked for affected companies until this is resolved."
		)
		frappe.log_error(message=message, title="Shareholding Legacy Backfill Pending")
		print(message)
		return
	post_legacy_movements(prepared)


def get_submitted_transfers():
	return frappe.db.sql(
		"""
		select name, company, share_type, transfer_type, `date`, creation,
			from_shareholder, to_shareholder, from_no, to_no, no_of_shares
		from `tabShare Transfer`
		where docstatus = 1
		order by `date`, creation, name
		""",
		as_dict=True,
	)


def get_class_mappings():
	classes = frappe.get_all("Share Class", fields=("name", "legacy_share_type"))
	mappings = {}
	for share_class in classes:
		if not share_class.legacy_share_type:
			continue
		key = share_class.legacy_share_type
		if key in mappings:
			frappe.throw(_("More than one Share Class maps to legacy Share Type {0}.").format(key))
		mappings[key] = share_class
	return mappings


def get_folios():
	return {
		(folio.company, folio.shareholder): folio.name
		for folio in frappe.get_all(
			"Share Folio", filters={"is_treasury": 0}, fields=("name", "company", "shareholder")
		)
	}


def validate_no_new_postings(transfers):
	companies = {transfer.company for transfer in transfers}
	for company in companies:
		if frappe.db.exists(
			"Share Ledger Entry", {"company": company, "source_doctype": "Share Transaction"}
		):
			frappe.throw(
				_(
					"Company {0} already has new Share Transactions. Review their ordering against "
					"legacy Share Transfers before backfilling history."
				).format(frappe.bold(company))
			)


def prepare_transfers(transfers, classes, folios):
	ownership = defaultdict(list)
	prepared = []
	for transfer in transfers:
		key = (transfer.company, transfer.share_type)
		share_class = classes.get(transfer.share_type)
		if not share_class:
			frappe.throw(
				_("Map legacy Share Type {0} to a Share Class for company {1} before migrating {2}.").format(
					transfer.share_type, transfer.company, transfer.name
				)
			)
		start, end = cint(transfer.from_no), cint(transfer.to_no)
		if start <= 0 or end < start or cint(transfer.no_of_shares) != end - start + 1:
			frappe.throw(_("Share Transfer {0} has an invalid share-number range.").format(transfer.name))
		if not transfer.date:
			frappe.throw(_("Share Transfer {0} has no posting date.").format(transfer.name))

		if transfer.transfer_type == "Issue":
			source, destination = None, transfer.to_shareholder
		elif transfer.transfer_type == "Transfer":
			source, destination = transfer.from_shareholder, transfer.to_shareholder
		elif transfer.transfer_type == "Purchase":
			source, destination = transfer.from_shareholder, None
		else:
			frappe.throw(_("Share Transfer {0} has an unsupported transaction type.").format(transfer.name))
		if source == destination or (source and (transfer.company, source) not in folios):
			frappe.throw(_("Share Transfer {0} has an invalid source folio.").format(transfer.name))
		if destination and (transfer.company, destination) not in folios:
			frappe.throw(_("Share Transfer {0} has no destination folio.").format(transfer.name))
		if not destination and not source:
			frappe.throw(_("Share Transfer {0} has no shareholder.").format(transfer.name))

		try:
			ownership[key] = move_range(ownership[key], start, end, source, destination)
		except ValueError as exc:
			frappe.throw(_("Share Transfer {0} cannot be replayed: {1}").format(transfer.name, str(exc)))
		prepared.append((transfer, share_class, source, destination, folios))
	return prepared, ownership


def move_range(ranges, start, end, source, destination):
	"""Return numbered ownership after one Issue, Transfer or legacy Purchase."""
	if start <= 0 or end < start or source == destination:
		raise ValueError("invalid share range or identical parties")
	if source:
		covered_until = start - 1
		for left, right, owner in ranges:
			if right < start or left > end:
				continue
			if owner != source or left > covered_until + 1:
				raise ValueError("the source does not own the complete range")
			covered_until = min(end, right)
		if covered_until != end:
			raise ValueError("the source does not own the complete range")
	elif any(left <= end and right >= start for left, right, _owner in ranges):
		raise ValueError("the range has already been issued")

	updated = []
	for left, right, owner in ranges:
		if right < start or left > end:
			updated.append((left, right, owner))
			continue
		if left < start:
			updated.append((left, start - 1, owner))
		if right > end:
			updated.append((end + 1, right, owner))
	if destination:
		updated.append((start, end, destination))
	return normalize_ranges(updated)


def normalize_ranges(ranges):
	merged = []
	for start, end, owner in sorted(ranges):
		if start <= 0 or end < start or not owner:
			raise ValueError("invalid legacy balance range")
		if merged and start <= merged[-1][1]:
			raise ValueError("overlapping legacy balance ranges")
		if merged and start == merged[-1][1] + 1 and owner == merged[-1][2]:
			merged[-1] = (merged[-1][0], end, owner)
		else:
			merged.append((start, end, owner))
	return merged


def reconcile_legacy_balances(final_ranges):
	balances = frappe.db.sql(
		"""
		select holder.company, balance.parent as shareholder, balance.share_type,
			balance.from_no, balance.to_no, balance.no_of_shares
		from `tabShareholding Legacy Balance Staging` balance
		inner join `tabShareholding Legacy Staging` holder on holder.name = balance.parent
		where holder.is_company = 0 and balance.is_company = 0
		""",
		as_dict=True,
	)
	staged_ranges = defaultdict(list)
	for balance in balances:
		start, end = cint(balance.from_no), cint(balance.to_no)
		if cint(balance.no_of_shares) != end - start + 1:
			frappe.throw(
				_("Legacy balance for shareholder {0} has an invalid share count.").format(
					balance.shareholder
				)
			)
		staged_ranges[(balance.company, balance.share_type)].append((start, end, balance.shareholder))
	for key in final_ranges.keys() | staged_ranges.keys():
		try:
			staged = normalize_ranges(staged_ranges[key])
		except ValueError as exc:
			frappe.throw(_("Legacy balances for {0} / {1} are invalid: {2}").format(*key, str(exc)))
		if final_ranges[key] != staged:
			frappe.throw(
				_(
					"Legacy balances do not match submitted Share Transfers for {0} / {1}. "
					"Review the old records or approve an opening balance before cutover."
				).format(*key)
			)


def post_legacy_movements(prepared):
	from erpnext.accounts.doctype.shareholder.shareholder import rebuild_current_holdings

	sequences = {}
	for transfer, share_class, source, destination, folios in prepared:
		quantity = cint(transfer.no_of_shares)
		movements = []
		if source:
			movements.append(("from", source, -quantity))
		if destination:
			movements.append(("to", destination, quantity))
		for side, shareholder, change in movements:
			posting_key = f"legacy-share-transfer:{transfer.name}:{side}"
			if frappe.db.exists("Share Ledger Entry", {"posting_key": posting_key}):
				continue
			sequence_key = (transfer.company, transfer.date)
			if sequence_key not in sequences:
				sequences[sequence_key] = cint(
					frappe.db.get_value(
						"Share Ledger Entry",
						{"company": transfer.company, "posting_date": transfer.date},
						"posting_sequence",
						order_by="posting_sequence desc",
					)
				)
			sequences[sequence_key] += 1
			face_value = None
			entry = frappe.get_doc(
				{
					"doctype": "Share Ledger Entry",
					"source_doctype": "Share Transfer",
					"source_name": transfer.name,
					"posting_key": posting_key,
					"recorded_at": transfer.creation,
					"transaction_type": (
						"Legacy Purchase" if transfer.transfer_type == "Purchase" else transfer.transfer_type
					),
					"company": transfer.company,
					"posting_date": transfer.date,
					"posting_sequence": sequences[sequence_key],
					"share_class": share_class.name,
					"share_folio": folios[(transfer.company, shareholder)],
					"from_share_number": transfer.from_no,
					"to_share_number": transfer.to_no,
					"quantity_change": change,
					"currency": frappe.db.get_value("Company", transfer.company, "default_currency"),
					"face_value_per_share": face_value,
					"capital_change": change * face_value if face_value is not None else None,
				}
			)
			entry.flags.from_legacy_migration = True
			entry.insert(ignore_permissions=True)

	shareholders = {
		shareholder
		for _transfer, _share_class, source, destination, _folios in prepared
		for shareholder in (source, destination)
		if shareholder
	}
	for shareholder in sorted(shareholders):
		rebuild_current_holdings(shareholder)
