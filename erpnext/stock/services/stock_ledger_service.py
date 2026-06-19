# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Stock Ledger Entry building and reposting for stock transactions.

Extracted from ``StockController``. Builds the SLE dicts for a voucher, writes
them, and triggers future SLE/GL reposting. The repost helper *functions* remain
module-level in ``stock_controller`` (imported widely); this service owns the
instance-level logic.
"""

import frappe
from frappe.utils import flt

from erpnext.accounts.utils import get_fiscal_year


class StockLedgerService:
	def __init__(self, doc) -> None:
		self.doc = doc

	def get_items_and_warehouses(self) -> tuple[list[str], list[str]]:
		"""Get list of items and warehouses affected by a transaction"""

		if not (hasattr(self.doc, "items") or hasattr(self.doc, "packed_items")):
			return [], []

		item_rows = (self.doc.get("items") or []) + (self.doc.get("packed_items") or [])

		items = {d.item_code for d in item_rows if d.item_code}

		warehouses = set()
		for d in item_rows:
			if d.get("warehouse"):
				warehouses.add(d.warehouse)

			if self.doc.doctype == "Stock Entry":
				if d.get("s_warehouse"):
					warehouses.add(d.s_warehouse)
				if d.get("t_warehouse"):
					warehouses.add(d.t_warehouse)

		return list(items), list(warehouses)

	def get_stock_ledger_details(self):
		stock_ledger = {}

		table = frappe.qb.DocType("Stock Ledger Entry")

		stock_ledger_entries = (
			frappe.qb.from_(table)
			.select(
				table.name,
				table.warehouse,
				table.stock_value_difference,
				table.valuation_rate,
				table.voucher_detail_no,
				table.item_code,
				table.posting_date,
				table.posting_time,
				table.actual_qty,
				table.qty_after_transaction,
				table.project,
			)
			.where(
				(table.voucher_type == self.doc.doctype)
				& (table.voucher_no == self.doc.name)
				& (table.is_cancelled == 0)
			)
		).run(as_dict=True)

		for sle in stock_ledger_entries:
			stock_ledger.setdefault(sle.voucher_detail_no, []).append(sle)

		return stock_ledger

	def get_sl_entries(self, d, args):
		sl_dict = frappe._dict(
			{
				"item_code": d.get("item_code", None),
				"warehouse": d.get("warehouse", None),
				"serial_and_batch_bundle": d.get("serial_and_batch_bundle"),
				"inventory_dimension_bundle": d.get("inventory_dimension_bundle"),
				"posting_date": self.doc.posting_date,
				"posting_time": self.doc.posting_time,
				"fiscal_year": get_fiscal_year(self.doc.posting_date, company=self.doc.company)[0],
				"voucher_type": self.doc.doctype,
				"voucher_no": self.doc.name,
				"voucher_detail_no": d.name,
				"actual_qty": (self.doc.docstatus == 1 and 1 or -1) * flt(d.get("stock_qty")),
				"stock_uom": frappe.get_cached_value(
					"Item", args.get("item_code") or d.get("item_code"), "stock_uom"
				),
				"incoming_rate": 0,
				"company": self.doc.company,
				"project": d.get("project") or self.doc.get("project"),
				"is_cancelled": 1 if self.doc.docstatus == 2 else 0,
			}
		)

		sl_dict.update(args)

		if self.doc.docstatus == 2:
			from erpnext.deprecation_dumpster import deprecation_warning

			deprecation_warning("unknown", "v16", "No instructions.")
			# To handle denormalized serial no records, will br deprecated in v16
			for field in ["serial_no", "batch_no"]:
				if d.get(field):
					sl_dict[field] = d.get(field)

		return sl_dict

	def make_sl_entries(self, sl_entries, allow_negative_stock=False, via_landed_cost_voucher=False):
		from erpnext.stock.serial_batch_bundle import update_batch_qty
		from erpnext.stock.services.inventory_dimension_bundle_service import (
			InventoryDimensionBundleService,
		)
		from erpnext.stock.services.serial_batch_bundle_service import SerialBatchBundleService
		from erpnext.stock.stock_ledger import make_sl_entries

		# Submit (on docstatus 1) or cancel (on docstatus 2) the linked inventory dimension
		# bundles, posting/reversing the quantity sub-ledger alongside the stock ledger.
		if self.doc.meta.get_field("items"):
			InventoryDimensionBundleService(self.doc).process_bundles_on_stock_posting()

		make_sl_entries(sl_entries, allow_negative_stock, via_landed_cost_voucher)
		update_batch_qty(
			self.doc.doctype,
			self.doc.name,
			self.doc.docstatus,
			via_landed_cost_voucher=via_landed_cost_voucher,
		)

		SerialBatchBundleService(self.doc).validate_reserved_batches()

	def repost_future_sle_and_gle(self, force=False, via_landed_cost_voucher=False):
		from erpnext.controllers.stock_controller import (
			create_item_wise_repost_entries,
			create_repost_item_valuation_entry,
			future_sle_exists,
			repost_required_for_queue,
		)

		args = frappe._dict(
			{
				"posting_date": self.doc.posting_date,
				"posting_time": self.doc.posting_time,
				"voucher_type": self.doc.doctype,
				"voucher_no": self.doc.name,
				"company": self.doc.company,
				"via_landed_cost_voucher": via_landed_cost_voucher,
			}
		)

		if self.doc.docstatus == 2:
			force = True

		if force or future_sle_exists(args) or repost_required_for_queue(self.doc):
			item_based_reposting = frappe.get_single_value("Stock Reposting Settings", "item_based_reposting")
			if item_based_reposting:
				create_item_wise_repost_entries(
					voucher_type=self.doc.doctype,
					voucher_no=self.doc.name,
					via_landed_cost_voucher=via_landed_cost_voucher,
				)
			else:
				create_repost_item_valuation_entry(args)
