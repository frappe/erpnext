# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

"""Shared test-only helpers for constructing serial/batch composition in fixtures, used across
many doctypes' test suites."""

import frappe
from frappe.utils import flt, nowtime

from erpnext.stock.serial_batch_bundle import SerialBatchCreation, combine_datetime


def make_serial_batch_bundle(kwargs):
	"""Test-only helper. do_not_save=True callers get the raw SerialBatchCreation object back;
	the default path runs the resolve+validate chain (so duplicate/future-entry/etc validation
	errors still raise the same way) and returns the resolved entries. Nothing is persisted -
	real postings write to Stock Location Ledger via make_location_ledger_entries()."""
	if isinstance(kwargs, dict):
		kwargs = frappe._dict(kwargs)

	type_of_transaction = "Inward" if kwargs.qty > 0 else "Outward"
	if kwargs.get("type_of_transaction"):
		type_of_transaction = kwargs.get("type_of_transaction")

	posting_datetime = None
	if kwargs.get("posting_date"):
		posting_datetime = combine_datetime(kwargs.posting_date, kwargs.posting_time or nowtime())

	sb = SerialBatchCreation(
		{
			"item_code": kwargs.item_code,
			"warehouse": kwargs.warehouse,
			"voucher_type": kwargs.voucher_type,
			"voucher_no": kwargs.voucher_no,
			"voucher_detail_no": kwargs.get("voucher_detail_no"),
			"posting_datetime": posting_datetime,
			"qty": kwargs.qty,
			"avg_rate": kwargs.rate,
			"batches": kwargs.batches,
			"serial_nos": kwargs.serial_nos,
			"type_of_transaction": type_of_transaction,
			"company": kwargs.company or "_Test Company",
		}
	)

	if kwargs.get("do_not_save"):
		return sb

	entries = sb.resolve_entries()
	sb.validate_entries(entries)

	return frappe._dict(
		{
			"name": None,
			"entries": entries,
			"item_code": kwargs.item_code,
			"warehouse": kwargs.warehouse,
			"company": kwargs.company or "_Test Company",
			"type_of_transaction": type_of_transaction,
			"total_qty": sum(abs(flt(e.qty)) for e in entries),
		}
	)
