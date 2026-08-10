# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Single write path for `tabStock Ledger Entry`.

Every statement that inserts or mutates Stock Ledger Entry rows belongs here,
so the table has exactly one write address. Business logic (what to write and
when) stays with the callers; this module owns the writes. This is also where
event emission and bypass detection attach in later phases.
"""

from typing import TYPE_CHECKING

import frappe
from frappe.utils import now

if TYPE_CHECKING:
	from frappe.model.document import Document


def submit_new(
	args: dict, allow_negative_stock: bool = False, via_landed_cost_voucher: bool = False
) -> "Document":
	"""Insert and submit one Stock Ledger Entry — the only insert path."""
	args["doctype"] = "Stock Ledger Entry"
	sle = frappe.get_doc(args)
	sle.flags.ignore_permissions = 1
	sle.allow_negative_stock = allow_negative_stock
	sle.via_landed_cost_voucher = via_landed_cost_voucher
	if args.get("is_cancelled"):
		sle.flags.ignore_links = True
	sle.submit()

	# SLEs recreated while reposting a Stock Reconciliation keep their original creation
	if args.get("creation_time") and args.get("voucher_type") == "Stock Reconciliation":
		set_fields(sle, {"creation": args.get("creation_time")})

	return sle


def insert_raw(args: dict) -> "Document":
	"""Insert a draft SLE skipping validations and link checks.

	Exists only for console repair tooling
	(``stock_balance.set_stock_balance_as_per_serial_no``); everything else
	must go through :func:`submit_new`.
	"""
	sle = frappe.get_doc(args)
	sle.flags.ignore_validate = True
	sle.flags.ignore_links = True
	sle.insert()
	return sle


def set_fields(sle: "Document | str", values: dict, update_modified: bool = True) -> None:
	"""Update fields on one SLE row; ``sle`` is a Document or a name."""
	if isinstance(sle, str):
		frappe.db.set_value("Stock Ledger Entry", sle, values, update_modified=update_modified)
	else:
		sle.db_set(values, update_modified=update_modified)


def write_valuation(sle: dict) -> None:
	"""Write back recomputed valuation fields during a repost.

	Full-row UPDATE via ``db_update`` — deliberately no validation and no hooks,
	matching how reposting has always written.
	"""
	frappe.get_doc(sle).db_update()


def flag_voucher_cancelled(voucher_type: str, voucher_no: str) -> None:
	"""Mark all live SLEs of a voucher cancelled.

	Rows are flagged, never deleted; the caller inserts reversal rows via
	:func:`submit_new` so the ledger stays append-only.
	"""
	sle = frappe.qb.DocType("Stock Ledger Entry")
	(
		frappe.qb.update(sle)
		.set(sle.is_cancelled, 1)
		.set(sle.modified, now())
		.set(sle.modified_by, frappe.session.user)
		.where((sle.voucher_type == voucher_type) & (sle.voucher_no == voucher_no) & (sle.is_cancelled == 0))
	).run()


def set_fields_for_voucher(
	voucher_type: str, voucher_no: str, values: dict, except_warehouses: list[str] | None = None
) -> None:
	"""Bulk-update fields on all of a voucher's SLE rows."""
	sle = frappe.qb.DocType("Stock Ledger Entry")
	query = frappe.qb.update(sle).where((sle.voucher_type == voucher_type) & (sle.voucher_no == voucher_no))
	if except_warehouses:
		query = query.where(sle.warehouse.notin(except_warehouses))
	for field, value in values.items():
		query = query.set(sle[field], value)
	query.run()


def clear_bundle_links(bundle_names: list[str]) -> None:
	"""Null the bundle link on cancelled SLEs referencing these bundles (POS merge delink)."""
	sle = frappe.qb.DocType("Stock Ledger Entry")
	(
		frappe.qb.update(sle)
		.set(sle.serial_and_batch_bundle, None)
		.where(sle.serial_and_batch_bundle.isin(bundle_names) & (sle.is_cancelled == 1))
	).run()


def rename_row(oldname: str, newname: str) -> None:
	"""Rename a temporarily named SLE row to its final series name (hourly rename job)."""
	sle = frappe.qb.DocType("Stock Ledger Entry")
	(
		frappe.qb.update(sle)
		.set(sle.name, newname)
		.set(sle.to_rename, 0)
		.set(sle.modified, now())
		.where(sle.name == oldname)
	).run()


def delete_for_voucher(voucher_type: str, voucher_no: str) -> None:
	"""Hard-delete a voucher's SLE rows.

	Only reached from document deletion with Accounts Settings
	``delete_linked_ledger_entries`` enabled; cancellation never deletes.
	"""
	sle = frappe.qb.DocType("Stock Ledger Entry")
	frappe.qb.from_(sle).delete().where(
		(sle.voucher_type == voucher_type) & (sle.voucher_no == voucher_no)
	).run()


def delete_rows(names: list[str]) -> None:
	"""Hard-delete SLE rows by name (per-company transaction deletion job)."""
	frappe.db.delete("Stock Ledger Entry", {"name": ("in", names)})


def shift_future_qty(
	args: dict, qty_shift: float, next_stock_reco_detail=None, standard_rate: float | None = None
) -> None:
	"""Shift ``qty_after_transaction`` on every future row of the (item, warehouse).

	``standard_rate`` is passed only for Standard Cost items, whose
	``stock_value`` is carried at that rate and can be updated in place.
	"""
	from erpnext.stock.stock_ledger import get_datetime_limit_condition

	posting_datetime = args["posting_datetime"]
	sle = frappe.qb.DocType("Stock Ledger Entry")

	future_condition = sle.posting_datetime > posting_datetime
	if args.get("creation") and not args.get("is_cancelled"):
		future_condition = future_condition | (
			(sle.posting_datetime == posting_datetime) & (sle.creation > args.get("creation"))
		)

	query = frappe.qb.update(sle).where(
		(sle.item_code == args.get("item_code"))
		& (sle.warehouse == args.get("warehouse"))
		& (sle.is_cancelled == 0)
		& future_condition
	)

	if next_stock_reco_detail:
		query = query.where(get_datetime_limit_condition(sle, next_stock_reco_detail[0]))

	new_qty = sle.qty_after_transaction + qty_shift

	if standard_rate is not None:
		# Set stock_value before qty_after_transaction: MariaDB evaluates SET left-to-right with the
		# already-updated values, so stock_value must be computed while qty still holds its pre-shift
		# value. (Postgres uses pre-update values throughout, so the result is the same either way.)
		query = query.set(sle.stock_value, new_qty * standard_rate)

	query = query.set(sle.qty_after_transaction, new_qty)
	query.run()
