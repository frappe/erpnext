from collections import defaultdict
from math import floor

import frappe
from frappe import _
from frappe.query_builder.functions import IfNull, Min, NullIf, Sum
from frappe.utils import cint, flt

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.serial_batch_bundle import SerialBatchCreation
from erpnext.stock.serial_batch_identity import SerialBatchIdentity
from erpnext.stock.utils import get_combine_datetime

from .manufacturing import (
	ceil_qty_if_uom_has_whole_number,
	get_bom_items,
	get_production_item_details,
	get_secondary_items,
)
from .stock_entry_base import BaseStockEntry


def _qty_tolerance(precision: int) -> float:
	"""One unit at the column's precision -- absorbs float rounding without letting a real
	(whole-unit) quantity divergence slip through."""
	return 1.0 / (10**precision)


def get_whole_number_units(row) -> tuple[float, float] | None:
	"""Row qty in its coarser whole-number UOM and the stock qty of one such unit, or None when any
	qty is allowed. Rounding in the finer unit can leave a fraction of the coarser one."""
	uom_is_whole = cint(frappe.get_cached_value("UOM", row.uom, "must_be_whole_number"))
	stock_uom_is_whole = cint(frappe.get_cached_value("UOM", row.stock_uom, "must_be_whole_number"))
	if stock_uom_is_whole and (not uom_is_whole or flt(row.conversion_factor) < 1):
		return flt(row.transfer_qty), 1.0
	if uom_is_whole:
		return flt(row.qty), flt(row.conversion_factor)
	return None


def _manufacture_line_order(line):
	return (line.parent_creation, line.parent_name.casefold(), line.parent_name, line.idx)


class DisassembleStockEntry(BaseStockEntry):
	def validate(self):
		self.validate_warehouse()

	def validate_warehouse(self):
		for row in self.doc.items:
			if not row.s_warehouse and not row.t_warehouse:
				frappe.throw(_("Source or Target Warehouse is required for item {0}").format(row.item_code))

	def validate_fg_completed_qty(self):
		if not self.doc.source_stock_entry:
			return

		from erpnext.manufacturing.doctype.work_order.work_order import get_disassembly_available_qty

		available_qty = get_disassembly_available_qty(self.doc.source_stock_entry, self.doc.name)

		if flt(self.doc.fg_completed_qty) > available_qty:
			frappe.throw(
				_(
					"Cannot disassemble {0} qty against Stock Entry {1}. Only {2} qty available to disassemble."
				).format(
					self.doc.fg_completed_qty,
					self.doc.source_stock_entry,
					available_qty,
				),
				title=_("Excess Disassembly"),
			)

	def validate_disassembly_quantities(self):
		self.validate_fg_completed_qty()
		self.validate_finished_good_consumption()
		self.validate_materials_against_source()

	def validate_finished_good_consumption(self):
		"""The finished good consumed (in stock UOM) must equal the quantity to disassemble."""
		precision = frappe.get_precision("Stock Entry Detail", "transfer_qty")
		tolerance = _qty_tolerance(precision)

		fg_stock_qty = sum(flt(row.transfer_qty) for row in self.doc.items if row.is_finished_item)
		fg_completed_qty = flt(self.doc.fg_completed_qty)

		if abs(flt(fg_stock_qty, precision) - flt(fg_completed_qty, precision)) > tolerance:
			frappe.throw(
				_(
					"Finished good quantity being consumed ({0} in stock UOM) must equal the quantity "
					"to disassemble ({1}). Do not change the UOM, conversion factor or quantity of the "
					"finished good row."
				).format(flt(fg_stock_qty, precision), flt(fg_completed_qty, precision)),
				title=_("Invalid Disassembly Quantity"),
			)

	def validate_materials_against_source(self):
		"""Every non-finished-good row's posted stock qty must equal the qty derived from the source."""
		source_fg_qty = self.get_source_fg_qty()
		if not source_fg_qty:
			return self.validate_materials_against_bom()

		progress = self.get_disassembly_progress(source_fg_qty)
		expected_rows = [
			(source_row, self.get_component_stock_qty(source_row, progress))
			for source_row in self.get_items_from_manufacture_stock_entry()
		]
		expected_by_name, expected_by_item = {}, defaultdict(float)
		for source_row, qty in expected_rows:
			if source_row.get("name"):
				expected_by_name[source_row.name] = (qty, flt(source_row.conversion_factor))
			expected_by_item[source_row.item_code] += qty

		precision = frappe.get_precision("Stock Entry Detail", "transfer_qty")
		tolerance = _qty_tolerance(precision)
		qty_precision = frappe.get_precision("Stock Entry Detail", "qty")
		self.validate_no_missing_components(expected_rows, precision, tolerance)

		for row in self.doc.items:
			if row.is_finished_item:
				continue  # covered by validate_finished_good_consumption

			if row.ste_detail and row.ste_detail in expected_by_name:
				expected, conversion_factor = expected_by_name[row.ste_detail]
			elif row.item_code in expected_by_item:
				expected, conversion_factor = expected_by_item[row.item_code], 1
			else:
				frappe.throw(
					_(
						"Row #{0}: Item {1} is not part of the source manufacture entry and cannot be "
						"added to this disassembly."
					).format(row.idx, frappe.bold(row.item_code)),
					title=_("Invalid Disassembly Item"),
				)

			# rows are populated with qty rounded in the source UOM, so expect the same rounding
			expected = flt(expected / conversion_factor, qty_precision) * conversion_factor
			if abs(flt(row.transfer_qty, precision) - flt(expected, precision)) > tolerance:
				frappe.throw(
					_(
						"Row #{0}: Item {1} quantity ({2} in stock UOM) does not match the quantity "
						"derived from the source ({3}). Do not change the UOM, conversion factor or "
						"quantity of disassembly rows."
					).format(
						row.idx,
						frappe.bold(row.item_code),
						flt(row.transfer_qty, precision),
						flt(expected, precision),
					),
					title=_("Invalid Disassembly Quantity"),
				)

	def validate_materials_against_bom(self):
		if not self.doc.bom_no:
			return

		expected_qty = {
			row.item_code: flt(row.qty) * flt(self.doc.fg_completed_qty)
			for row in get_bom_items(self.doc.bom_no, self.doc.use_multi_level_bom)
		}
		precision = frappe.get_precision("Stock Entry Detail", "transfer_qty")
		for item_code, qty in self.get_received_component_qty().items():
			if item_code not in expected_qty:
				frappe.throw(
					_("Item {0} is not part of the BOM {1} and cannot be added to this disassembly.").format(
						frappe.bold(item_code), frappe.bold(self.doc.bom_no)
					),
					title=_("Invalid Disassembly Item"),
				)

			if abs(flt(qty, precision) - flt(expected_qty[item_code], precision)) > _qty_tolerance(precision):
				frappe.throw(
					_("Item {0} quantity ({1} in stock UOM) does not match the BOM quantity {2}.").format(
						frappe.bold(item_code), flt(qty, precision), flt(expected_qty[item_code], precision)
					),
					title=_("Invalid Disassembly Quantity"),
				)

	def validate_no_missing_components(self, expected_rows, precision, tolerance):
		"""A draft made before another disassembly was submitted can lack a component it now owes."""
		present = {row.ste_detail or row.item_code for row in self.doc.items}
		for source_row, qty in expected_rows:
			key = source_row.get("name") or source_row.item_code
			if not source_row.is_finished_item and flt(qty, precision) > tolerance and key not in present:
				frappe.throw(
					_("Item {0} is missing from this disassembly. Get the items again.").format(
						frappe.bold(source_row.item_code)
					),
					title=_("Missing Disassembly Item"),
				)

	def get_received_component_qty(self) -> dict:
		received_qty = defaultdict(float)
		for row in self.doc.items:
			if row.t_warehouse and not row.is_finished_item:
				received_qty[row.item_code] += flt(row.transfer_qty)

		return received_qty

	def get_source_fg_qty(self) -> float:
		if self.doc.source_stock_entry:
			return flt(frappe.db.get_value("Stock Entry", self.doc.source_stock_entry, "fg_completed_qty"))
		if self.doc.work_order:
			return flt(frappe.db.get_value("Work Order", self.doc.work_order, "produced_qty"))
		return 0.0

	def get_disassembly_progress(self, source_fg_qty) -> frappe._dict:
		"""Share of the source disassembled up to this entry, and component stock qty that submitted
		disassemblies of the same source already moved."""
		SE = frappe.qb.DocType("Stock Entry")
		SED = frappe.qb.DocType("Stock Entry Detail")
		if self.doc.source_stock_entry:
			source_filter, key = SE.source_stock_entry == self.doc.source_stock_entry, SED.ste_detail
		else:
			source_filter, key = SE.work_order == self.doc.work_order, SED.item_code

		earlier = source_filter & (SE.purpose == "Disassemble") & (SE.docstatus == 1)
		earlier_fg_qty = frappe.qb.from_(SE).select(Sum(SE.fg_completed_qty)).where(earlier).run()[0][0]
		moved = (
			frappe.qb.from_(SED)
			.join(SE)
			.on(SED.parent == SE.name)
			.select(key.as_("key"), Sum(SED.transfer_qty).as_("qty"))
			.where(earlier & (SED.is_finished_item == 0))
			.groupby(key)
			.run(as_dict=True)
		)

		return frappe._dict(
			share_to_date=(flt(earlier_fg_qty) + flt(self.doc.fg_completed_qty)) / source_fg_qty,
			moved_qty={row.key: flt(row.qty) for row in moved},
		)

	def get_component_stock_qty(self, source_row, progress) -> float:
		"""Stock qty of a source row this disassembly moves, taken off the running total so the
		disassembly that completes the source takes the remainder. Whole-number rows are rounded down."""
		precision = frappe.get_precision("Stock Entry Detail", "transfer_qty")
		moved_qty = progress.moved_qty.get(source_row.get("name") or source_row.item_code, 0)
		whole_number_units = get_whole_number_units(source_row)
		if not whole_number_units:
			return flt(max(flt(source_row.transfer_qty) * progress.share_to_date - moved_qty, 0), precision)

		units, step = whole_number_units
		units_to_date = floor(flt(units * progress.share_to_date, precision))
		return max(units_to_date - round(moved_qty / step), 0) * step

	def add_items(self):
		"""
		Priority:
		1. From a specific Manufacture Stock Entry (exact reversal)
		2. From Work Order Manufacture Stock Entries (averaged reversal)
		3. From BOM (standalone disassembly)
		"""

		# Auto-set source_stock_entry if WO has exactly one manufacture entry
		if not self.doc.get("source_stock_entry") and self.doc.work_order:
			manufacture_entries = frappe.get_all(
				"Stock Entry",
				filters={
					"work_order": self.doc.work_order,
					"purpose": "Manufacture",
					"docstatus": 1,
				},
				pluck="name",
			)
			if len(manufacture_entries) == 1:
				self.doc.source_stock_entry = manufacture_entries[0]

		if self.doc.get("source_stock_entry"):
			return self._add_items_for_disassembly_from_stock_entry()

		if self.doc.work_order:
			return self._add_items_for_disassembly_from_work_order()

		return self._add_items_for_disassembly_from_bom()

	def _add_items_for_disassembly_from_stock_entry(self):
		source_fg_qty = self.get_source_fg_qty()
		if not source_fg_qty:
			frappe.throw(
				_("Source Stock Entry {0} has no finished goods quantity").format(self.doc.source_stock_entry)
			)

		self._append_disassembly_row_from_source(source_fg_qty)

	def _add_items_for_disassembly_from_work_order(self):
		wo_produced_qty = self.get_source_fg_qty()
		if wo_produced_qty <= 0:
			frappe.throw(_("Work Order {0} has no produced qty").format(self.doc.work_order))

		if flt(self.doc.fg_completed_qty) <= 0:
			frappe.throw(_("Disassemble Qty cannot be less than or equal to 0."))

		self._append_disassembly_row_from_source(wo_produced_qty)

	def _append_disassembly_row_from_source(self, source_fg_qty):
		progress = self.get_disassembly_progress(source_fg_qty)
		for source_row in self.get_items_from_manufacture_stock_entry():
			self._append_disassembly_item(source_row, progress)

	def _get_disassembly_warehouses(self, source_row, progress):
		if source_row.is_finished_item:
			return flt(self.doc.fg_completed_qty), self.doc.from_warehouse or source_row.t_warehouse, ""

		qty = flt(
			self.get_component_stock_qty(source_row, progress) / source_row.conversion_factor,
			frappe.get_precision("Stock Entry Detail", "qty"),
		)
		if source_row.s_warehouse:
			return qty, "", self.doc.to_warehouse or source_row.s_warehouse
		return qty, source_row.t_warehouse, ""

	def _build_disassembly_item_dict(self, source_row, qty, s_warehouse, t_warehouse):
		return {
			"item_code": source_row.item_code,
			"item_name": source_row.item_name,
			"description": source_row.description,
			"stock_uom": source_row.stock_uom,
			"uom": source_row.uom,
			"conversion_factor": source_row.conversion_factor,
			"basic_rate": source_row.basic_rate,
			"qty": qty,
			"s_warehouse": s_warehouse,
			"t_warehouse": t_warehouse,
			"is_finished_item": source_row.is_finished_item,
			"secondary_item_type": source_row.secondary_item_type,
			"valuation_type": source_row.valuation_type,
			"bom_secondary_item": source_row.bom_secondary_item,
			"bom_no": source_row.bom_no,
			"use_serial_batch_fields": 1 if (source_row.batch_no or source_row.serial_no) else 0,
		}

	def _append_disassembly_item(self, source_row, progress):
		qty, s_warehouse, t_warehouse = self._get_disassembly_warehouses(source_row, progress)
		if not qty:
			return
		item = self._build_disassembly_item_dict(source_row, qty, s_warehouse, t_warehouse)
		if self.doc.source_stock_entry:
			item.update({"against_stock_entry": self.doc.source_stock_entry, "ste_detail": source_row.name})
		self.doc.append("items", item)

	def _add_items_for_disassembly_from_bom(self):
		if not self.doc.bom_no or not self.doc.fg_completed_qty:
			frappe.throw(_("BOM and Finished Good Quantity is mandatory for Disassembly"))

		self.add_raw_materials()
		self.add_secondary_items()
		self.add_finished_goods()

	def add_raw_materials(self):
		# Raw materials will be available after disassembly in target warehouse
		items = get_bom_items(self.doc.bom_no, self.doc.use_multi_level_bom)

		for row in items:
			row["t_warehouse"] = self.doc.to_warehouse
			row["from_warehouse"] = ""
			row["is_finished_item"] = 0
			row["qty"] = flt(row["qty"]) * flt(self.doc.fg_completed_qty)
			row["uom"] = row.get("uom") or row.get("stock_uom")
			self.doc.append("items", row)

	def add_secondary_items(self):
		# Secondary items will be removed from source warehouse

		secondary_items = get_secondary_items(self.doc.bom_no, self.doc.work_order)
		for row in secondary_items:
			item_args = {}
			fields = [
				"item_code",
				"item_name",
				"uom",
				"stock_uom",
				"conversion_factor",
				"item_group",
				"description",
				"secondary_item_type",
			]
			for field in fields:
				item_args[field] = row.get(field)

			item_args["valuation_type"] = row.get("valuation_type")
			item_args["s_warehouse"] = self.doc.from_warehouse
			item_args["uom"] = item_args.get("uom") or item_args.get("stock_uom")
			item_args["bom_secondary_item"] = row.get("name")

			row.qty = row.qty * self.doc.fg_completed_qty
			if row.get("process_loss_per"):
				row.qty -= flt(row.qty * row.get("process_loss_per") / 100)
			item_args["qty"] = ceil_qty_if_uom_has_whole_number(row.qty, item_args["uom"])

			self.doc.append("items", item_args)

	def add_finished_goods(self):
		item_details = get_production_item_details(self.doc.work_order, self.doc.bom_no)

		item_details.update(
			{
				"conversion_factor": 1,
				"uom": item_details.stock_uom,
				"qty": self.doc.fg_completed_qty,
				"t_warehouse": None,
				"s_warehouse": self.doc.from_warehouse,
				"is_finished_item": 1,
			}
		)

		item_details["item_code"] = item_details["name"]
		del item_details["name"]

		self.doc.append("items", item_details)

	def get_items_from_manufacture_stock_entry(self):
		SE = frappe.qb.DocType("Stock Entry")
		SED = frappe.qb.DocType("Stock Entry Detail")
		query = frappe.qb.from_(SED).join(SE).on(SED.parent == SE.name).where(SE.docstatus == 1)

		common_fields = [
			SED.item_code,
			SED.item_name,
			SED.description,
			SED.stock_uom,
			SED.uom,
			SED.basic_rate,
			SED.conversion_factor,
			SED.is_finished_item,
			SED.secondary_item_type,
			SED.valuation_type,
			SED.bom_secondary_item,
			SED.batch_no,
			SED.serial_no,
			SED.use_serial_batch_fields,
			SED.s_warehouse,
			SED.t_warehouse,
			SED.bom_no,
		]

		if self.doc.source_stock_entry:
			return (
				query.select(SED.name, SED.qty, SED.transfer_qty, *common_fields)
				.where(SE.name == self.doc.source_stock_entry)
				.orderby(SED.idx)
				.run(as_dict=True)
			)

		# Aggregate in stock UOM: qty is expressed in each row's selected UOM and cannot be added
		# when manufacture entries use different UOMs for the same item. basic_rate is also per
		# stock UOM, so weight it by transfer_qty. Manufacture rows always carry positive stock
		# qty, so NullIf only guards a theoretical /0.
		rows = (
			query.select(
				SED.item_code,
				Sum(SED.transfer_qty).as_("qty"),
				Sum(SED.transfer_qty).as_("transfer_qty"),
				(Sum(SED.basic_rate * SED.transfer_qty) / NullIf(Sum(SED.transfer_qty), 0)).as_("basic_rate"),
			)
			.where(SE.purpose == "Manufacture")
			.where(SE.work_order == self.doc.work_order)
			.groupby(SED.item_code)
			.orderby(Min(SED.idx))
			.run(as_dict=True)
		)

		representative = self.get_representative_manufacture_rows()
		for row in rows:
			row.update(representative.get(row.item_code) or {})
			row.uom = row.stock_uom
			row.conversion_factor = 1

		return rows

	def get_representative_manufacture_rows(self):
		"""Earliest posted line per item across the work order's Manufacture entries.

		The disassembly wants one row per item, but some descriptive columns describe a line, not
		an item: batch_no and serial_no only mean something beside their warehouse, and
		is_finished_item decides whether the row is the output or an input. Aggregating each column
		on its own can pair values from different lines into a row that was never posted, so take
		the columns from a single real line instead. UOM is normalized separately to stock UOM.

		Ordered in Python rather than SQL, keeping the original (entry creation, entry name, line idx)
		precedence. casefold reproduces MariaDB's case-insensitive collation without depending on the
		database's, which PostgreSQL resolves by byte value.
		"""
		SE = frappe.qb.DocType("Stock Entry")
		SED = frappe.qb.DocType("Stock Entry Detail")

		lines = (
			frappe.qb.from_(SED)
			.join(SE)
			.on(SED.parent == SE.name)
			.select(
				SE.creation.as_("parent_creation"),
				SE.name.as_("parent_name"),
				SED.idx,
				SED.item_code,
				SED.item_name,
				SED.description,
				SED.stock_uom,
				SED.is_finished_item,
				SED.secondary_item_type,
				SED.valuation_type,
				SED.bom_secondary_item,
				SED.batch_no,
				SED.serial_no,
				SED.use_serial_batch_fields,
				SED.s_warehouse,
				SED.t_warehouse,
				SED.bom_no,
			)
			.where(
				(SE.docstatus == 1) & (SE.purpose == "Manufacture") & (SE.work_order == self.doc.work_order)
			)
			.run(as_dict=True)
		)
		lines.sort(key=_manufacture_line_order)

		representative = {}
		for line in lines:
			line.pop("parent_creation")
			line.pop("parent_name")
			representative.setdefault(line.item_code, line)

		return representative

	def before_submit(self):
		self.set_serial_batch_for_disassembly()

	def on_submit(self):
		self.update_disassembled_order()

	def on_cancel(self):
		self.update_disassembled_order()

	def set_serial_batch_for_disassembly(self):
		if self.doc.get("source_stock_entry"):
			self._set_serial_batch_for_disassembly_from_stock_entry()
		else:
			self._set_serial_batch_for_disassembly_from_available_materials()

	def _set_serial_batch_for_disassembly_from_stock_entry(self):
		from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
			get_voucher_wise_serial_batch_from_bundle,
		)

		bundle_data = get_voucher_wise_serial_batch_from_bundle(voucher_no=[self.doc.source_stock_entry])
		source_rows_by_name = {r.name: r for r in self.get_items_from_manufacture_stock_entry()}
		used = self.get_serial_batches_used_by_earlier_disassemblies()
		for row in self.doc.items:
			if not row.ste_detail:
				continue
			source_row = source_rows_by_name.get(row.ste_detail)
			if source_row:
				self._apply_bundle_to_disassembly_row(row, source_row, bundle_data, used)

	def get_serial_batches_used_by_earlier_disassemblies(self) -> frappe._dict:
		"""Serial nos and batch qty by source warehouse that submitted disassemblies of the source entry
		already moved."""
		SE = frappe.qb.DocType("Stock Entry")
		SED = frappe.qb.DocType("Stock Entry Detail")
		SBE = frappe.qb.DocType("Serial and Batch Entry")
		source = frappe.qb.DocType("Stock Entry Detail").as_("source")
		rows = (
			frappe.qb.from_(SED)
			.join(SE)
			.on(SED.parent == SE.name)
			.join(source)
			.on(SED.ste_detail == source.name)
			.join(SBE)
			.on(SBE.parent == SED.serial_and_batch_bundle)
			.select(
				IfNull(NullIf(source.s_warehouse, ""), source.t_warehouse).as_("warehouse"),
				SBE.serial_no,
				SBE.batch_no,
				SBE.qty,
			)
			.where(
				(SE.source_stock_entry == self.doc.source_stock_entry)
				& (SE.purpose == "Disassemble")
				& (SE.docstatus == 1)
			)
			.run(as_dict=True)
		)

		used = frappe._dict(serial_nos=set(), batch_qty=defaultdict(lambda: defaultdict(float)))
		for row in rows:
			if row.serial_no:
				used.serial_nos.add(row.serial_no)
			if row.batch_no:
				used.batch_qty[row.warehouse][row.batch_no] += abs(flt(row.qty))
		return used

	def _apply_bundle_to_disassembly_row(self, row, source_row, bundle_data, used):
		source_warehouse = source_row.s_warehouse or source_row.t_warehouse
		key = (source_row.item_code, source_warehouse, self.doc.source_stock_entry)
		source_bundle = bundle_data.get(key, {})
		used_batch_qty = used.batch_qty[source_warehouse]
		batches = self._extract_batches(source_row, source_bundle, row, used_batch_qty)
		serial_nos = self._extract_serial_nos(source_row, source_bundle, row, used.serial_nos)
		self._set_serial_batch_bundle_for_disassembly_row(row, serial_nos, batches)

		# rows of the same item and warehouse share the source bundle
		used.serial_nos.update(serial_nos)
		for batch_no, qty in batches.items():
			used_batch_qty[batch_no] += qty

	def _extract_batches(self, source_row, source_bundle, row, used_batch_qty):
		"""Fill the row from the source batches in order, skipping qty earlier disassemblies moved."""
		if source_bundle.get("batch_nos"):
			precision = frappe.get_precision("Stock Entry Detail", "transfer_qty")
			remaining = {
				batch_no: flt(abs(flt(qty)) - used_batch_qty[batch_no], precision)
				for batch_no, qty in source_bundle["batch_nos"].items()
			}
			return self._collect_available_batches(
				{batch_no: qty for batch_no, qty in remaining.items() if qty > 0}, row.transfer_qty
			)
		if source_row.batch_no:
			return {source_row.batch_no: row.transfer_qty}
		return {}

	def _extract_serial_nos(self, source_row, source_bundle, row, used_serial_nos):
		if source_bundle.get("serial_nos"):
			serial_nos = get_serial_nos(source_bundle["serial_nos"])
		elif source_row.serial_no:
			serial_nos = SerialBatchIdentity("Serial No").resolve(
				source_row.item_code, get_serial_nos(source_row.serial_no), ignore_permissions=True
			)
		else:
			return []

		return [serial_no for serial_no in serial_nos if serial_no not in used_serial_nos][
			: int(row.transfer_qty)
		]

	def _set_serial_batch_for_disassembly_from_available_materials(self):
		available_materials = get_available_materials(self.doc.work_order, self.doc)
		for row in self.doc.items:
			warehouse = row.s_warehouse or row.t_warehouse
			materials = available_materials.get((row.item_code, warehouse))
			if materials:
				self._apply_available_material_bundle(row, materials)

	def _apply_available_material_bundle(self, row, materials):
		batches = self._collect_available_batches(materials.batch_details, row.transfer_qty)
		serial_nos = materials.serial_nos[: int(row.transfer_qty)] if materials.serial_nos else []
		self._set_serial_batch_bundle_for_disassembly_row(row, serial_nos, batches)

	def _collect_available_batches(self, batch_details, transfer_qty):
		batches, qty = defaultdict(float), transfer_qty
		for batch_no, batch_qty in batch_details.items():
			if qty <= 0:
				break
			batch_qty = abs(batch_qty)
			if batch_qty <= qty:
				batches[batch_no], qty = batch_qty, qty - batch_qty
			else:
				batches[batch_no], qty = qty, 0
		return batches

	def _set_serial_batch_bundle_for_disassembly_row(self, row, serial_nos, batches):
		if not serial_nos and not batches:
			return

		warehouse = row.s_warehouse or row.t_warehouse
		bundle_doc = SerialBatchCreation(
			{
				"item_code": row.item_code,
				"warehouse": warehouse,
				"posting_datetime": get_combine_datetime(self.doc.posting_date, self.doc.posting_time),
				"voucher_type": self.doc.doctype,
				"voucher_no": self.doc.name,
				"voucher_detail_no": row.name,
				"qty": row.transfer_qty,
				"type_of_transaction": "Inward" if row.t_warehouse else "Outward",
				"company": self.doc.company,
				"do_not_submit": True,
			}
		).make_serial_and_batch_bundle(serial_nos=serial_nos, batch_nos=batches)

		row.serial_and_batch_bundle = bundle_doc.name
		row.use_serial_batch_fields = 0

	def update_disassembled_order(self):
		if not self.doc.work_order:
			return

		if self.doc.fg_completed_qty:
			pro_doc = frappe.get_doc("Work Order", self.doc.work_order)
			pro_doc.run_method(
				"update_disassembled_qty", self.doc.fg_completed_qty, self.doc._action == "cancel"
			)


def get_available_materials(work_order, stock_entry_doc=None) -> dict:
	data = get_stock_entry_data(work_order, stock_entry_doc=stock_entry_doc)
	available_materials = {}
	for row in data:
		key = _get_material_key(row, stock_entry_doc)
		if key not in available_materials:
			available_materials[key] = frappe._dict(
				{"item_details": row, "batch_details": defaultdict(float), "qty": 0, "serial_nos": []}
			)
		_update_material_qty(available_materials[key], row, stock_entry_doc)
	sort_serial_nos_by_number(available_materials)
	return available_materials


def sort_serial_nos_by_number(available_materials):
	serial_nos = [serial_no for material in available_materials.values() for serial_no in material.serial_nos]
	numbers = SerialBatchIdentity("Serial No").get_number_map(serial_nos)
	for material in available_materials.values():
		material.serial_nos.sort(key=lambda name: numbers.get(name, name))


def _get_material_key(row, stock_entry_doc):
	if stock_entry_doc and stock_entry_doc.purpose == "Disassemble":
		return (row.item_code, row.s_warehouse or row.warehouse)
	if row.purpose != "Material Transfer for Manufacture":
		return (row.item_code, row.s_warehouse)
	return (row.item_code, row.warehouse)


def _update_material_qty(item_data, row, stock_entry_doc):
	is_inward = row.purpose == "Material Transfer for Manufacture" or (
		stock_entry_doc and stock_entry_doc.purpose == "Disassemble" and row.purpose == "Manufacture"
	)
	if is_inward:
		_add_inward_material_qty(item_data, row)
	else:
		_deduct_consumed_material_qty(item_data, row)


def _add_inward_material_qty(item_data, row):
	item_data.qty += row.qty
	if row.batch_no:
		item_data.batch_details[row.batch_no] += row.qty
	elif row.batch_nos:
		for batch_no, qty in row.batch_nos.items():
			item_data.batch_details[batch_no] += qty
	_extend_serial_nos_from_row(item_data, row)


def _extend_serial_nos_from_row(item_data, row):
	known = set(item_data.serial_nos)
	item_data.serial_nos.extend(serial_no for serial_no in row.serial_nos or [] if serial_no not in known)


def _deduct_consumed_material_qty(item_data, row):
	item_data.qty -= row.qty
	if row.batch_no:
		item_data.batch_details[row.batch_no] -= row.qty
	elif row.batch_nos:
		for batch_no, qty in row.batch_nos.items():
			item_data.batch_details[batch_no] += qty
	_remove_serial_nos_from_available(item_data, row)


def _remove_serial_nos_from_available(item_data, row):
	for serial_no in row.serial_nos or []:
		if serial_no in item_data.serial_nos:
			item_data.serial_nos.remove(serial_no)


def get_stock_entry_data(work_order, stock_entry_doc=None):
	data = _run_stock_entry_query(work_order, stock_entry_doc)
	if not data:
		return []
	_enrich_with_bundle_data(data, stock_entry_doc)
	for row in data:
		if row.serial_no and not row.serial_nos:
			row.serial_nos = SerialBatchIdentity("Serial No").resolve(
				row.item_code, get_serial_nos(row.serial_no), ignore_permissions=True
			)
	return data


def _run_stock_entry_query(work_order, stock_entry_doc):
	se = frappe.qb.DocType("Stock Entry")
	sed = frappe.qb.DocType("Stock Entry Detail")
	query = _build_stock_entry_base_query(se, sed, work_order)
	query = _apply_stock_entry_purpose_filter(query, se, sed, stock_entry_doc)
	return query.run(as_dict=1)


def _build_stock_entry_base_query(se, sed, work_order):
	return (
		frappe.qb.from_(se)
		.from_(sed)
		.select(
			sed.item_name,
			sed.original_item,
			sed.item_code,
			sed.qty,
			sed.t_warehouse.as_("warehouse"),
			sed.s_warehouse.as_("s_warehouse"),
			sed.description,
			sed.stock_uom,
			sed.expense_account,
			sed.cost_center,
			sed.serial_and_batch_bundle,
			sed.batch_no,
			sed.serial_no,
			se.purpose,
			se.name,
		)
		.where((se.name == sed.parent) & (se.work_order == work_order) & (se.docstatus == 1))
		.orderby(se.creation, sed.item_code, sed.idx)
	)


def _apply_stock_entry_purpose_filter(query, se, sed, stock_entry_doc):
	if stock_entry_doc and stock_entry_doc.purpose == "Disassemble":
		query = query.where(se.purpose.isin(["Disassemble", "Manufacture"]))
		return query.where(se.name != stock_entry_doc.name)
	query = query.where(
		se.purpose.isin(
			["Manufacture", "Material Consumption for Manufacture", "Material Transfer for Manufacture"]
		)
	)
	return query.where(IfNull(sed.s_warehouse, "") != "")


def _enrich_with_bundle_data(data, stock_entry_doc):
	from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
		get_voucher_wise_serial_batch_from_bundle,
	)

	voucher_nos = [row.get("name") for row in data if row.get("name")]
	if not voucher_nos:
		return
	bundle_data = get_voucher_wise_serial_batch_from_bundle(voucher_no=voucher_nos)
	for row in data:
		key = _get_bundle_key(row, stock_entry_doc)
		if bundle_data.get(key):
			row.update(bundle_data.get(key))


def _get_bundle_key(row, stock_entry_doc):
	if stock_entry_doc and stock_entry_doc.purpose == "Disassemble":
		return (row.item_code, row.s_warehouse or row.warehouse, row.name)
	if row.purpose != "Material Transfer for Manufacture":
		return (row.item_code, row.s_warehouse, row.name)
	return (row.item_code, row.warehouse, row.name)
