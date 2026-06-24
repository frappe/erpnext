# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import typing

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import cint, flt


class InventoryDimensionNegativeStockError(frappe.ValidationError):
	pass


class InventoryDimensionBundle(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.inventory_dimension_entry.inventory_dimension_entry import (
			InventoryDimensionEntry,
		)

		amended_from: DF.Link | None
		company: DF.Link
		entries: DF.Table[InventoryDimensionEntry]
		is_cancelled: DF.Check
		item_code: DF.Link
		item_group: DF.Link | None
		item_name: DF.Data | None
		naming_series: DF.Literal["", "IDB-.########"]
		posting_datetime: DF.Datetime | None
		total_qty: DF.Float
		type_of_transaction: DF.Literal["", "Inward", "Outward"]
		voucher_detail_no: DF.Data | None
		voucher_no: DF.DynamicLink | None
		voucher_type: DF.Link | None
		warehouse: DF.Link | None
	# end: auto-generated types

	# Voucher types whose direction is unambiguous, used to stamp the bundle's direction when it
	# was created/linked manually before the voucher stamps it on submit. Ambiguous voucher types
	# (Stock Entry, Stock Reconciliation, Subcontracting Receipt) and returns are left to the
	# voucher, which stamps the exact direction via ``get_type_of_transaction`` on submit.
	DIRECTIONAL_VOUCHERS: typing.ClassVar[dict] = {
		"Delivery Note": "Outward",
		"Sales Invoice": "Outward",
		"POS Invoice": "Outward",
		"Purchase Receipt": "Inward",
		"Purchase Invoice": "Inward",
	}

	def validate(self):
		self.set_type_of_transaction()
		self.set_entry_references()
		self.calculate_total_qty()

	def set_type_of_transaction(self):
		"""Infer the bundle direction from the voucher when it is still unset.

		A bundle built/linked manually (the full form, not the on-submit stamp) has no direction
		yet, so its entries would default to inward. Stamp it from the voucher type for the
		unambiguous cases; the voucher overrides this with the exact direction on submit.
		"""
		if not self.type_of_transaction and self.voucher_type:
			self.type_of_transaction = self.DIRECTIONAL_VOUCHERS.get(self.voucher_type, "")

	def before_submit(self):
		self.validate_voucher_controlled("submitted")

		# Direction is unknown while the bundle is a draft created from the dialog; it is
		# stamped from the voucher on submit. Enforce it only at submit time.
		if not self.type_of_transaction:
			frappe.throw(_("Type of Transaction is required to submit an Inventory Dimension Bundle."))

		self.validate_mandatory_dimensions()
		self.validate_negative_stock()

	def before_cancel(self):
		self.validate_voucher_controlled("cancelled")

	def validate_voucher_controlled(self, action):
		"""The bundle's lifecycle is owned by its voucher: it is submitted/cancelled only when the
		linked voucher is submitted/cancelled (the controller sets ``flags.from_voucher``), never by
		hand. The migration patch reconstructs bundles directly and is exempt."""
		if self.flags.from_voucher or frappe.flags.in_patch:
			return

		frappe.throw(
			_(
				"An Inventory Dimension Bundle is {0} automatically when its linked voucher is {0};"
				" it cannot be {0} manually."
			).format(_(action)),
			title=_("Not Allowed"),
		)

	def validate_mandatory_dimensions(self):
		"""Each entry must carry a value for every dimension configured as Mandatory.

		The set of mandatory dimensions is taken from the dimension's ``reqd`` flag, scoped to the
		bundle's voucher (its item child doctype).
		"""
		# Migrating historical vouchers rebuilds bundles from SLEs that were posted when a dimension
		# may still have been optional; enforcing a now-mandatory dimension here would abort the
		# migration mid-run (mirrors the guard in validate_negative_stock).
		if frappe.flags.in_patch:
			return

		from erpnext.stock.doctype.inventory_dimension.inventory_dimension import (
			get_mandatory_inventory_dimensions,
			get_voucher_child_doctype,
		)

		child_doctype = get_voucher_child_doctype(self.voucher_type)
		mandatory = get_mandatory_inventory_dimensions(child_doctype)
		if not mandatory:
			return

		for row in self.entries:
			for dimension in mandatory:
				fieldname = dimension.get("source_fieldname")
				if not frappe.db.has_column("Inventory Dimension Entry", fieldname):
					continue
				if not row.get(fieldname):
					frappe.throw(
						_("Row #{0}: {1} is mandatory in the Inventory Dimension Bundle.").format(
							row.idx, frappe.bold(dimension.get("name"))
						),
						title=_("Inventory Dimension Required"),
					)

	def validate_negative_stock(self):
		"""Block submission when an outward entry would drive a dimension negative.

		Only dimensions flagged ``validate_negative_stock`` are checked. Each such dimension carries
		a ``negative_stock_validation_method``:

		* ``Per Dimension`` (default) - the dimension's own balance is validated independently, so
		  e.g. ``Rack=A`` must have stock regardless of which ``Bin`` it sits in.
		* ``Combined`` - the exact combination of *all* combined-method dimensions on a line is
		  validated together, so e.g. only ``Rack=A`` + ``Bin=X`` jointly must have stock.

		Availability is taken from the quantity sub-ledger strictly before this bundle's posting
		(this bundle excluded).
		"""
		from erpnext.stock.doctype.inventory_dimension.inventory_dimension import (
			get_inventory_dimensions,
		)

		# Migrating historical vouchers reconstructs an already-valid ledger; enforcing negative stock
		# here would spuriously fail whenever an outward bundle is rebuilt before its inward source.
		if frappe.flags.in_patch:
			return

		neg_dimensions = [d for d in get_inventory_dimensions() if d.get("validate_negative_stock")]
		if not neg_dimensions:
			return

		combined_dimensions = [
			d for d in neg_dimensions if d.get("negative_stock_validation_method") == "Combined"
		]
		per_dimensions = [
			d for d in neg_dimensions if d.get("negative_stock_validation_method") != "Combined"
		]

		flt_precision = cint(frappe.db.get_default("float_precision")) or 2

		# Aggregate outward qty per check key:
		# - one key holding every "Combined" dimension value present on the row, and
		# - one key per individual "Per Dimension" value on the row.
		outward_qty = {}
		combinations = {}
		for row in self.entries:
			if not row.is_outward:
				continue

			row_combinations = []

			combined = {
				d.source_fieldname: row.get(d.source_fieldname)
				for d in combined_dimensions
				if row.get(d.source_fieldname)
			}
			if combined:
				row_combinations.append(combined)

			for d in per_dimensions:
				value = row.get(d.source_fieldname)
				if value:
					row_combinations.append({d.source_fieldname: value})

			for combination in row_combinations:
				key = tuple(sorted(combination.items()))
				# qty is stored negative for outward; accumulate the outward demand as a magnitude.
				outward_qty[key] = outward_qty.get(key, 0.0) + abs(flt(row.qty))
				combinations[key] = combination

		for key, qty in outward_qty.items():
			available_qty = get_dimension_sub_ledger_balance(
				self.item_code,
				self.warehouse,
				combinations[key],
				posting_datetime=self.posting_datetime,
				exclude_bundle=self.name,
			)
			diff = flt(available_qty - qty, flt_precision)
			if diff < 0 and abs(diff) > 0.0001:
				self.throw_negative_stock_error(diff, combinations[key])

	def throw_negative_stock_error(self, diff, combination):
		frappe.throw(
			_(
				"{0} units of {1} are required in {2} with the inventory dimension: {3} to complete the transaction."
			).format(
				abs(diff),
				frappe.get_desk_link("Item", self.item_code),
				frappe.get_desk_link("Warehouse", self.warehouse),
				frappe.bold(", ".join([f"{field}: {value}" for field, value in combination.items()])),
			),
			title=_("Inventory Dimension Negative Stock"),
			exc=InventoryDimensionNegativeStockError,
		)

	def set_entry_references(self):
		"""Denormalize parent context onto each entry and normalise direction + sign.

		Runs on every save (mirrors Serial and Batch Entry): each reference is re-synced from the
		parent so a bundle edited directly - or stamped from its voucher on submit - always agrees
		with the parent (voucher no, posting datetime, etc. that were blank on a freshly created
		draft get filled in once the voucher stamps them).

		Direction is the parent's ``type_of_transaction`` unless an entry already carries its own
		``is_outward`` (a transfer migrated into one bundle keeps an outward leg + an inward leg).
		The entry ``qty`` is then signed to match - negative for outward, positive for inward -
		mirroring Stock Ledger Entry's ``actual_qty`` and Serial and Batch Bundle.
		"""
		is_outward = 1 if self.type_of_transaction == "Outward" else 0
		for row in self.entries:
			row.item_code = self.item_code
			row.voucher_type = self.voucher_type
			row.voucher_no = self.voucher_no
			row.voucher_detail_no = self.voucher_detail_no
			row.posting_datetime = self.posting_datetime
			row.is_cancelled = self.is_cancelled
			if not row.warehouse:
				row.warehouse = self.warehouse
			if not row.is_outward:
				row.is_outward = is_outward
			self.normalize_entry_qty(row)

	@staticmethod
	def normalize_entry_qty(row):
		"""Store qty signed by direction: negative for outward, positive for inward."""
		qty = flt(row.qty)
		if row.is_outward and qty > 0:
			row.qty = -qty
		elif not row.is_outward and qty < 0:
			row.qty = -qty

	def calculate_total_qty(self):
		# qty is stored signed (negative for outward), so the total nets per direction, matching
		# the voucher row's signed stock qty.
		self.total_qty = flt(sum(flt(row.qty) for row in self.entries))

	def on_submit(self):
		# Phase 3 will post the quantity sub-ledger from these entries.
		pass

	def on_cancel(self):
		# The voucher (and its item row) that links this bundle is still submitted while the
		# bundle is cancelled as part of the voucher's own cancellation; exempt those links and
		# the immutable Stock Ledger Entry from the back-link check.
		self.ignore_linked_doctypes = (
			"Stock Ledger Entry",
			"Stock Entry",
			"Delivery Note",
			"Sales Invoice",
			"POS Invoice",
			"Purchase Receipt",
			"Purchase Invoice",
			"Stock Reconciliation",
			"Subcontracting Receipt",
		)
		self.set_is_cancelled(1)

	def set_is_cancelled(self, value: int):
		self.db_set("is_cancelled", value)
		for row in self.entries:
			row.db_set("is_cancelled", value)

	def validate_total_qty_against_voucher(self, row_qty: float):
		"""Helper used by the transaction controllers (Phase 2): the bundle's total qty
		must reconcile with the linked transaction row qty."""
		# Compare magnitudes: total_qty is stored signed (negative for outward) while the voucher
		# row's qty may be positive. Tolerate float rounding (e.g. 1.2000000000000002 vs 1.2);
		# matches the negative-stock guard's tolerance rather than an exact equality test.
		if abs(abs(flt(self.total_qty)) - abs(flt(row_qty))) > 0.0001:
			frappe.throw(
				_(
					"Total quantity {0} in the inventory dimensions does not match the row quantity {1}."
				).format(frappe.bold(self.total_qty), frappe.bold(row_qty))
			)

	def set_inventory_dimension_values(
		self, parent_doc, row, qty_field="qty", warehouse=None, item_code=None, type_of_transaction=None
	):
		"""Stamp the linked transaction's references onto the bundle and submit it.

		Mirrors ``Serial and Batch Bundle.set_serial_and_batch_values``. Called from the
		transaction controllers on submit for stock-item rows that carry an inventory
		dimension bundle. ``warehouse`` is passed for the rejected-qty bundle so it posts against
		the rejected warehouse; otherwise it is derived from the row. ``item_code`` and
		``type_of_transaction`` are passed for rows whose stock identity isn't ``row.item_code`` or
		whose direction the voucher can't infer from the row (e.g. a Subcontracting Receipt's
		``supplied_items``, which consume ``rm_item_code`` outward from the supplier warehouse).
		"""
		from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
			combine_datetime,
			get_type_of_transaction,
		)

		self.voucher_type = parent_doc.doctype
		self.voucher_no = parent_doc.name
		self.voucher_detail_no = row.name
		self.item_code = item_code or row.item_code
		self.company = parent_doc.company

		# The voucher is authoritative for direction (it knows returns, transfers, etc.); overwrite
		# any direction inferred while the bundle was a manually created draft.
		self.type_of_transaction = type_of_transaction or get_type_of_transaction(parent_doc, row)

		if warehouse:
			self.warehouse = warehouse
		else:
			# Derive by direction so a transfer's outward leg posts against the source warehouse
			# (the inward leg gets its own bundle via make_inventory_dimension_bundle_for_transfer).
			self.warehouse = self.get_voucher_warehouse(row)

		if parent_doc.get("posting_date"):
			self.posting_datetime = combine_datetime(
				parent_doc.get("posting_date"), parent_doc.get("posting_time")
			)

		self.calculate_total_qty()
		self.validate_total_qty_against_voucher(flt(row.get(qty_field)))

		if self.docstatus == 0:
			self.flags.ignore_permissions = True
			# The voucher owns the bundle's lifecycle; authorise this submit (manual submit is blocked).
			self.flags.from_voucher = True
			self.submit()

	def get_voucher_warehouse(self, row):
		"""The warehouse this bundle posts against, by direction.

		An outward leg posts against the source warehouse and an inward leg against the target, so a
		two-legged Stock Entry transfer resolves each side correctly.
		"""
		if self.type_of_transaction == "Outward":
			return row.get("warehouse") or row.get("s_warehouse") or row.get("t_warehouse")
		return row.get("warehouse") or row.get("t_warehouse") or row.get("s_warehouse")


def make_inventory_dimension_bundle_for_transfer(source_bundle, warehouse, parent_doc, voucher_detail_no):
	"""Build (and submit) the inward Inventory Dimension Bundle for a transfer's target leg.

	A material transfer / Send to Subcontractor moves a row's qty out of the source warehouse and
	into the target warehouse, producing two Stock Ledger Entries. The row carries one (outward)
	bundle for the source leg; the target leg needs its own inward bundle, posting the same
	dimension split into the target warehouse. Mirrors Serial and Batch Bundle's
	``make_bundle_for_material_transfer``.
	"""
	from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import combine_datetime

	doc = frappe.copy_doc(frappe.get_doc("Inventory Dimension Bundle", source_bundle))
	doc.docstatus = 0
	doc.warehouse = warehouse
	doc.type_of_transaction = "Inward"
	doc.voucher_type = parent_doc.doctype
	doc.voucher_no = parent_doc.name
	doc.voucher_detail_no = voucher_detail_no
	doc.is_cancelled = 0

	if parent_doc.get("posting_date"):
		doc.posting_datetime = combine_datetime(
			parent_doc.get("posting_date"), parent_doc.get("posting_time")
		)

	for entry in doc.entries:
		entry.warehouse = warehouse
		entry.is_outward = 0
		entry.qty = abs(flt(entry.qty))
		entry.is_cancelled = 0

	doc.flags.ignore_permissions = True
	doc.flags.from_voucher = True
	doc.submit()
	return doc.name


def get_inventory_dimension_bundle_naming_series():
	return "IDB-.########"


def get_dimension_sub_ledger_balance(
	item_code: str,
	warehouse: str,
	dimension_filters: dict | None = None,
	posting_datetime=None,
	company: str | None = None,
	inclusive: bool = False,
	exclude_bundle: str | None = None,
) -> float:
	"""Net quantity balance for an item/warehouse (and optional dimension combination).

	The Inventory Dimension Entry rows are the quantity sub-ledger. Inward entries add,
	outward entries subtract. Pass ``dimension_filters`` (``{source_fieldname: value}``) to
	restrict to a specific dimension combination. ``posting_datetime`` caps the cutoff:
	``inclusive=False`` (default) counts entries strictly before it (balance *before* a posting);
	``inclusive=True`` counts entries up to and including it (balance *as of* a date).
	"""
	entry = frappe.qb.DocType("Inventory Dimension Entry")
	query = (
		frappe.qb.from_(entry)
		# qty is stored signed (negative for outward), so the net balance is a plain sum.
		.select(Sum(entry.qty))
		.where(
			(entry.item_code == item_code)
			& (entry.warehouse == warehouse)
			& (entry.is_cancelled == 0)
			# Only submitted bundles form the sub-ledger; draft bundles (e.g. a dialog draft or a
			# bundle whose voucher failed to submit) must never count toward a balance.
			& (entry.docstatus == 1)
		)
	)

	if company:
		bundle = frappe.qb.DocType("Inventory Dimension Bundle")
		query = query.join(bundle).on(entry.parent == bundle.name).where(bundle.company == company)

	if posting_datetime:
		if inclusive:
			query = query.where(entry.posting_datetime <= posting_datetime)
		else:
			query = query.where(entry.posting_datetime < posting_datetime)

	if exclude_bundle:
		query = query.where(entry.parent != exclude_bundle)

	for fieldname, value in (dimension_filters or {}).items():
		query = query.where(entry[fieldname] == value)

	result = query.run()
	return flt(result[0][0]) if result and result[0][0] is not None else 0.0


@frappe.whitelist()
def get_dimensions_for_selector(child_doctype: str) -> list:
	"""Dimensions (with their reference doctype + fieldname) that apply to a child doctype.

	Drives the dimension capture dialog: one Link column per dimension + a qty column.
	"""
	from erpnext.stock.doctype.inventory_dimension.inventory_dimension import (
		get_document_wise_inventory_dimensions,
	)

	dimensions = get_document_wise_inventory_dimensions(child_doctype) or []
	result = []
	for dimension in dimensions:
		result.append(
			{
				"dimension": dimension.get("name"),
				"fieldname": dimension.get("source_fieldname"),
				"reference_document": dimension.get("reference_document"),
				"reqd": dimension.get("reqd"),
			}
		)

	return result


@frappe.whitelist()
def get_inventory_dimension_bundle_entries(bundle: str) -> list:
	"""Return an existing bundle's entries (qty + dimension values) to pre-fill the capture dialog."""
	from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions

	if not bundle or not frappe.db.exists("Inventory Dimension Bundle", bundle):
		return []

	frappe.has_permission("Inventory Dimension Bundle", "read", bundle, throw=True)

	dimension_fields = [
		d.source_fieldname
		for d in get_inventory_dimensions()
		if d.source_fieldname and frappe.db.has_column("Inventory Dimension Entry", d.source_fieldname)
	]

	return frappe.get_all(
		"Inventory Dimension Entry",
		filters={"parent": bundle},
		fields=["qty", *dimension_fields],
		order_by="idx",
	)


@frappe.whitelist()
def create_inventory_dimension_bundle(
	company: str,
	item_code: str,
	warehouse: str | None = None,
	type_of_transaction: str | None = None,
	voucher_type: str | None = None,
	entries: str | list | None = None,
	bundle: str | None = None,
):
	"""Create (or replace) a draft Inventory Dimension Bundle from dialog input.

	Dimension values are written only to Entry fields that actually exist (the per-dimension
	columns are added in Phase 3), so this is safe to call before that migration runs.
	"""
	if isinstance(entries, str):
		entries = frappe.parse_json(entries)
	entries = entries or []

	if bundle and frappe.db.exists("Inventory Dimension Bundle", bundle):
		doc = frappe.get_doc("Inventory Dimension Bundle", bundle)
		if doc.docstatus == 0:
			doc.set("entries", [])
	else:
		doc = frappe.new_doc("Inventory Dimension Bundle")

	doc.company = company
	doc.item_code = item_code
	doc.warehouse = warehouse
	doc.type_of_transaction = type_of_transaction
	doc.voucher_type = voucher_type

	entry_meta_fields = {df.fieldname for df in frappe.get_meta("Inventory Dimension Entry").fields}
	for entry in entries:
		row = {"qty": flt(entry.get("qty")), "warehouse": entry.get("warehouse") or warehouse}
		for key, value in entry.items():
			if key in entry_meta_fields and key not in ("qty", "warehouse"):
				row[key] = value
		doc.append("entries", row)

	# Permission alread handled
	doc.save()
	return doc.name
