# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InventoryDimensionEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		is_cancelled: DF.Check
		is_outward: DF.Check
		item_code: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		posting_datetime: DF.Datetime | None
		qty: DF.Float
		voucher_detail_no: DF.Data | None
		voucher_no: DF.Data | None
		voucher_type: DF.Data | None
		warehouse: DF.Link | None
	# end: auto-generated types

	pass


def on_doctype_update():
	"""Composite indexes for the quantity sub-ledger, mirroring Stock Ledger Entry.

	The sub-ledger is read like the SLE: per item + warehouse balances over time (reporting,
	opening balances, negative-stock checks) and voucher-scoped lookups. At million-row scale a
	single composite index on each access path keeps these from degrading into full scans. Frappe
	runs this on every ``bench migrate`` and on install; ``add_index`` is idempotent.
	"""
	frappe.db.add_index(
		"Inventory Dimension Entry", ["item_code", "warehouse", "posting_datetime", "creation"]
	)
	frappe.db.add_index("Inventory Dimension Entry", ["voucher_no", "voucher_type"])
