# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Inventory Dimension Bundle handling for stock transactions.

Mirrors ``SerialBatchBundleService``: owns creation, validation and submission of
Inventory Dimension Bundles for a stock voucher. The controller keeps thin delegators
for methods reached from other doctypes / ``run_method``; internal helpers live here.

Inventory dimensions are a **quantity-only** sub-ledger: a bundle captures how a row's
qty is split across dimension combinations. The check is gated on ``is_stock_item`` so
service / non-stock rows are never asked for dimension values.
"""

import typing

import frappe
from frappe import _, bold
from frappe.utils import flt

from erpnext.stock.doctype.inventory_dimension.inventory_dimension import (
	get_document_wise_inventory_dimensions,
	is_inventory_dimension_enabled,
)


class InventoryDimensionBundleService:
	def __init__(self, doc) -> None:
		self.doc = doc

	# ------------------------------------------------------------------ helpers

	def get_table_name(self, table_name=None) -> str:
		return table_name or "items"

	# Tables other than ``items`` whose rows can carry a dimension bundle, with the field overrides
	# needed to stamp it. A Subcontracting Receipt consumes raw materials through ``supplied_items``,
	# which name the item/qty/warehouse differently and always move stock *out* of the supplier
	# warehouse - so the bundle is stamped as an Outward consumption against that warehouse.
	TABLE_CONFIG: typing.ClassVar[dict] = {
		"packed_items": {},
		"supplied_items": {
			"item_field": "rm_item_code",
			"qty_field": "consumed_qty",
			"type_of_transaction": "Outward",
			"warehouse_attr": "supplier_warehouse",
		},
	}

	def get_bundle_tables(self, table_name=None) -> list:
		"""Item tables that can carry inventory dimension bundles.

		Besides the main ``items`` table, a Product Bundle line's stock moves through ``packed_items``
		and a Subcontracting Receipt's raw material is consumed through ``supplied_items``; a dimension
		bundle captured on either must be stamped/submitted/cancelled alongside the main rows.
		"""
		if table_name:
			return [table_name]

		tables = ["items", *self.TABLE_CONFIG]
		return [table for table in tables if self.doc.meta.get_field(table)]

	def get_child_doctype(self, table_name) -> str | None:
		meta_field = self.doc.meta.get_field(table_name)
		return meta_field.options if meta_field else None

	def get_applicable_dimensions(self, table_name) -> list:
		"""Inventory dimensions that apply to this voucher's child doctype (or all doctypes)."""
		child_doctype = self.get_child_doctype(table_name)
		if not child_doctype:
			return []

		return get_document_wise_inventory_dimensions(child_doctype) or []

	@staticmethod
	def is_stock_item(item_code) -> bool:
		if not item_code:
			return False

		return bool(frappe.get_cached_value("Item", item_code, "is_stock_item"))

	def row_has_dimension_qty(self, row) -> bool:
		"""True only for stock rows that actually move stock (qty or rejected qty)."""
		return bool(self.is_stock_item(row.get("item_code"))) and bool(
			flt(row.get("qty")) or flt(row.get("rejected_qty"))
		)

	def dimension_applies_to_row(self, dimension, row) -> bool:
		"""Honour the dimension's optional ``condition`` against the row."""
		if not dimension.get("condition"):
			return True

		try:
			return bool(frappe.safe_eval(dimension.get("condition"), None, {"doc": row, "parent": self.doc}))
		except Exception:
			# A malformed condition should not block posting; treat as applicable.
			return True

	# ------------------------------------------------------------- build / submit

	def process_bundles_on_stock_posting(self, table_name=None):
		"""Single entry point invoked from the shared stock-posting chokepoint.

		On submit (docstatus 1) the linked draft bundles are stamped + submitted, posting the
		quantity sub-ledger. On cancel (docstatus 2) the submitted bundles are cancelled. Both the
		main ``items`` table and (for Product Bundle lines) ``packed_items`` are processed.
		"""
		for table in self.get_bundle_tables(table_name):
			if self.doc.docstatus == 2:
				self.cancel_inventory_dimension_bundles(table)
			else:
				self.set_inventory_dimension_bundle(table)

	# The accepted-qty bundle and (on purchase docs) the rejected-qty bundle are stamped/submitted
	# and cancelled the same way, only differing in the qty field, warehouse and link field.
	BUNDLE_FIELDS = (
		("inventory_dimension_bundle", "qty", None),
		("rejected_inventory_dimension_bundle", "rejected_qty", "rejected_warehouse"),
	)

	def set_inventory_dimension_bundle(self, table_name=None, ignore_validate=False):
		"""On submit, stamp references onto each row's bundle(s) and submit them."""
		table_name = self.get_table_name(table_name)
		config = self.TABLE_CONFIG.get(table_name, {})
		item_field = config.get("item_field", "item_code")

		for row in self.doc.get(table_name):
			item_code = row.get(item_field)
			for fieldname, qty_field, warehouse_field in self.BUNDLE_FIELDS:
				bundle = row.get(fieldname)
				if not bundle:
					continue

				if not self.is_stock_item(item_code):
					# A non-stock row must never carry a dimension bundle.
					row.set(fieldname, None)
					continue

				doc = frappe.get_doc("Inventory Dimension Bundle", bundle)
				if doc.docstatus == 0:
					doc.set_inventory_dimension_values(
						self.doc,
						row,
						qty_field=config.get("qty_field", qty_field),
						warehouse=self._bundle_warehouse(row, warehouse_field, config),
						item_code=item_code,
						type_of_transaction=config.get("type_of_transaction"),
					)

	def _bundle_warehouse(self, row, warehouse_field, config):
		"""Warehouse the bundle posts against: a parent attribute (supplied items consume from the
		supplier warehouse, which the row does not name), else the row's own warehouse field."""
		if config.get("warehouse_attr"):
			return self.doc.get(config["warehouse_attr"])
		return row.get(warehouse_field) if warehouse_field else None

	def cancel_inventory_dimension_bundles(self, table_name=None):
		"""Cancel the submitted bundles of a voucher being cancelled, then unlink them from its rows.

		Detaching the bundle from the row keeps a later amend from carrying a link to a now-cancelled
		document ("Cannot link cancelled document"). The Stock Ledger Entry keeps its own (immutable)
		link, so the sub-ledger reversal is unaffected.
		"""
		table_name = self.get_table_name(table_name)

		# Detach the bundles from this table's rows (covers the main item row and a Product Bundle's
		# packed item row). The field is no_copy, but clearing it here also covers amend on sites
		# whose meta predates that flag.
		for row in self.doc.get(table_name):
			for fieldname, _qty_field, _warehouse_field in self.BUNDLE_FIELDS:
				if row.get(fieldname):
					row.db_set(fieldname, None, update_modified=False)

		self.cancel_voucher_bundles()

	def cancel_voucher_bundles(self):
		"""Cancel every submitted bundle of this voucher.

		Besides the bundles linked on the voucher rows, this also catches the inward bundle a
		transfer's target leg creates on its Stock Ledger Entry (it is not linked on any row).
		"""
		bundles = frappe.get_all(
			"Inventory Dimension Bundle",
			filters={"voucher_type": self.doc.doctype, "voucher_no": self.doc.name, "docstatus": 1},
			pluck="name",
		)
		for bundle in bundles:
			doc = frappe.get_doc("Inventory Dimension Bundle", bundle)
			doc.flags.ignore_permissions = True
			# The voucher owns the bundle's lifecycle; authorise this cancel (manual cancel is blocked).
			doc.flags.from_voucher = True
			doc.cancel()

	# --------------------------------------------------------------- validation

	def validate_inventory_dimension_bundle(self, table_name=None):
		"""is_stock_item-gated mandatory-dimension enforcement (replaces field-level reqd).

		Service / non-stock rows are skipped entirely (fixes the spurious 'set the
		Inventory Dimension' error on service items).
		"""
		if not is_inventory_dimension_enabled():
			return

		table_name = self.get_table_name(table_name)
		dimensions = self.get_applicable_dimensions(table_name)
		if not dimensions:
			return

		mandatory = [d for d in dimensions if d.get("reqd")]
		if not mandatory:
			return

		# Validate the accepted leg (qty -> inventory_dimension_bundle) and the rejected leg
		# (rejected_qty -> rejected_inventory_dimension_bundle) independently. A purchase row can move
		# stock on either or both legs, and each leg captures its dimensions on its own bundle; checking
		# them together would falsely flag a row that captured its dimension on the other leg's bundle.
		for bundle_field, qty_field, _warehouse_field in self.BUNDLE_FIELDS:
			self._validate_accepted_dim_qty(table_name, dimensions, mandatory, bundle_field, qty_field)

	def _validate_accepted_dim_qty(self, table_name, dimensions, mandatory, bundle_field, qty_field):
		"""Enforce mandatory dimensions for the rows that move stock on one leg (accepted/rejected)."""
		# Some tables name the item/qty fields differently (supplied items hold the RM in
		# ``rm_item_code`` and consume ``consumed_qty``); resolve them the same way the stamping does
		# so the gate is not silently skipped. The per-table qty override is the accepted-leg field;
		# the rejected leg keeps its own (``rejected_qty``), which such tables simply do not have.
		config = self.TABLE_CONFIG.get(table_name, {})
		item_field = config.get("item_field", "item_code")
		if bundle_field == "inventory_dimension_bundle":
			qty_field = config.get("qty_field", qty_field)

		rows = [
			row
			for row in self.doc.get(table_name)
			if self.is_stock_item(row.get(item_field)) and flt(row.get(qty_field))
		]
		if not rows:
			return

		# Batch-fetch every linked bundle's entries up front so the per-row coverage check below
		# is a dict lookup, not an N+1 query (a 50-line receipt fired 50 queries previously).
		entries_by_bundle = self._get_entries_by_bundle(rows, bundle_field)

		for row in rows:
			covered = self._covered_dimensions(row, dimensions, entries_by_bundle, bundle_field)
			for dimension in mandatory:
				if not self.dimension_applies_to_row(dimension, row):
					continue

				if dimension.get("name") not in covered:
					frappe.throw(
						_("Row #{0}: Please set the inventory dimension {1} for item {2}.").format(
							row.idx, bold(dimension.get("name")), bold(row.get(item_field))
						),
						title=_("Inventory Dimension Required"),
					)

	def _get_entries_by_bundle(self, rows, bundle_field="inventory_dimension_bundle") -> dict:
		"""All Inventory Dimension Entry rows for the rows' bundles, grouped by bundle, in one query."""
		bundles = [row.get(bundle_field) for row in rows if row.get(bundle_field)]
		if not bundles:
			return {}

		entries_by_bundle = {}
		for entry in frappe.get_all(
			"Inventory Dimension Entry", filters={"parent": ("in", bundles)}, fields=["*"]
		):
			entries_by_bundle.setdefault(entry.parent, []).append(entry)

		return entries_by_bundle

	def _covered_dimensions(
		self, row, dimensions, entries_by_bundle, bundle_field="inventory_dimension_bundle"
	) -> set:
		"""Set of dimension names that the row's bundle provides a value for."""
		bundle = row.get(bundle_field)
		if not bundle:
			return set()

		# Dimension values live in custom columns on Inventory Dimension Entry (added per
		# dimension in Phase 3); a dimension is "covered" when at least one entry has a value.
		entries = entries_by_bundle.get(bundle, [])

		covered = set()
		for dimension in dimensions:
			fieldname = dimension.get("source_fieldname")
			if fieldname and any(entry.get(fieldname) for entry in entries):
				covered.add(dimension.get("name"))

		return covered
