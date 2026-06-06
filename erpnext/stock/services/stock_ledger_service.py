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
from erpnext.stock.doctype.inventory_dimension.inventory_dimension import (
	get_evaluated_inventory_dimension,
)


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
		self.update_inventory_dimensions(d, sl_dict)

		if self.doc.docstatus == 2:
			from erpnext.deprecation_dumpster import deprecation_warning

			deprecation_warning("unknown", "v16", "No instructions.")
			# To handle denormalized serial no records, will br deprecated in v16
			for field in ["serial_no", "batch_no"]:
				if d.get(field):
					sl_dict[field] = d.get(field)

		return sl_dict

	def update_inventory_dimensions(self, row, sl_dict) -> None:
		# To handle delivery note and sales invoice
		if row.get("item_row"):
			row = row.get("item_row")

		dimensions = get_evaluated_inventory_dimension(row, sl_dict, parent_doc=self.doc)
		for dimension in dimensions:
			if not dimension:
				continue

			if (
				self.doc.doctype in ["Purchase Invoice", "Purchase Receipt"]
				and row.get("rejected_warehouse")
				and sl_dict.get("warehouse") == row.get("rejected_warehouse")
			):
				fieldname = f"rejected_{dimension.source_fieldname}"
				sl_dict[dimension.target_fieldname] = row.get(fieldname)
				continue

			if self.doc.doctype in [
				"Purchase Invoice",
				"Purchase Receipt",
				"Sales Invoice",
				"Delivery Note",
				"Stock Entry",
			]:
				if (
					(
						sl_dict.actual_qty > 0
						and not self.doc.get("is_return")
						or sl_dict.actual_qty < 0
						and self.doc.get("is_return")
					)
					and self.doc.doctype in ["Purchase Invoice", "Purchase Receipt", "Stock Entry"]
				) or (
					(
						sl_dict.actual_qty < 0
						and not self.doc.get("is_return")
						or sl_dict.actual_qty > 0
						and self.doc.get("is_return")
					)
					and self.doc.doctype in ["Sales Invoice", "Delivery Note", "Stock Entry"]
				):
					if self.doc.doctype == "Stock Entry":
						if row.get("t_warehouse") == sl_dict.warehouse and sl_dict.get("actual_qty") > 0:
							fieldname = f"to_{dimension.source_fieldname}"
							if dimension.source_fieldname.startswith("to_"):
								fieldname = f"{dimension.source_fieldname}"

							sl_dict[dimension.target_fieldname] = row.get(fieldname)
							continue

					sl_dict[dimension.target_fieldname] = row.get(dimension.source_fieldname)
				else:
					fieldname_start_with = "to"
					if self.doc.doctype in ["Purchase Invoice", "Purchase Receipt"]:
						fieldname_start_with = "from"

					fieldname = f"{fieldname_start_with}_{dimension.source_fieldname}"
					sl_dict[dimension.target_fieldname] = row.get(fieldname)

					if not sl_dict.get(dimension.target_fieldname):
						sl_dict[dimension.target_fieldname] = row.get(dimension.source_fieldname)

			elif row.get(dimension.source_fieldname):
				sl_dict[dimension.target_fieldname] = row.get(dimension.source_fieldname)

			if not sl_dict.get(dimension.target_fieldname) and dimension.fetch_from_parent:
				sl_dict[dimension.target_fieldname] = self.doc.get(dimension.fetch_from_parent)

				# Get value based on doctype name
				if not sl_dict.get(dimension.target_fieldname):
					fieldname = next(
						(
							field.fieldname
							for field in frappe.get_meta(self.doc.doctype).fields
							if field.options == dimension.fetch_from_parent
						),
						None,
					)

					if fieldname and self.doc.get(fieldname):
						sl_dict[dimension.target_fieldname] = self.doc.get(fieldname)

				if sl_dict[dimension.target_fieldname] and self.doc.docstatus == 1:
					row.db_set(dimension.source_fieldname, sl_dict[dimension.target_fieldname])

	def make_sl_entries(self, sl_entries, allow_negative_stock=False, via_landed_cost_voucher=False):
		from erpnext.stock.serial_batch_bundle import update_batch_qty
		from erpnext.stock.services.serial_batch_bundle_service import SerialBatchBundleService
		from erpnext.stock.stock_ledger import make_sl_entries

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
