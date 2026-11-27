import json
from collections import defaultdict

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.query_builder import Case
from frappe.query_builder.functions import Coalesce, NullIf, Sum
from frappe.utils import flt

from erpnext.stock.serial_batch_bundle import get_batches_from_bundle
from erpnext.stock.utils import get_bin

from .stock_entry_base import BaseStockEntry


class SendToSubcontractorStockEntry(BaseStockEntry):
	def validate(self):
		if self.doc.get(self.doc.subcontract_data.order_field):
			self.validate_subcontract_order()

	def validate_subcontract_order(self):
		"""Throw exception if more raw material is transferred against Subcontract Order than in
		the raw materials supplied table"""
		backflush_raw_materials_based_on = frappe.db.get_single_value(
			"Buying Settings", "backflush_raw_materials_of_subcontract_based_on"
		)

		if backflush_raw_materials_based_on == "BOM":
			subcontract_order = frappe.get_doc(
				self.doc.subcontract_data.order_doctype, self.doc.get(self.doc.subcontract_data.order_field)
			)
			qty_in_entry = defaultdict(float)
			for se_item in self.doc.items:
				self.validate_subcontracting_order_for_bom(se_item, subcontract_order, qty_in_entry)

		elif backflush_raw_materials_based_on == "Material Transferred for Subcontract":
			finished_goods = self.get_order_finished_goods()
			finished_good_of_rows = self.get_finished_good_of_order_rows()
			for row in self.doc.items:
				self.validate_subcontracting_order_for_transfer(row, finished_goods, finished_good_of_rows)

	def validate_subcontracting_order_for_bom(self, child_row, subcontract_order, qty_in_entry):
		item_code = child_row.original_item or child_row.item_code
		required_qty = self._get_required_qty_for_bom(item_code, child_row, subcontract_order)
		qty_allowance = flt(frappe.db.get_single_value("Buying Settings", "over_transfer_allowance"))
		total_allowed = required_qty + (required_qty * qty_allowance / 100)
		stock_qty = self.get_stock_qty(child_row)
		self._validate_transfer_qty(child_row, item_code, total_allowed, qty_in_entry[item_code], stock_qty)
		qty_in_entry[item_code] += stock_qty
		self._link_rm_detail_if_missing(child_row, item_code)

	def _get_required_qty_for_bom(self, item_code, child_row, subcontract_order):
		required_qty = sum(
			flt(d.required_qty) for d in subcontract_order.supplied_items if d.rm_item_code == item_code
		)
		if not required_qty and child_row.allow_alternative_item:
			original_item_code = frappe.get_value(
				"Item Alternative", {"alternative_item_code": item_code}, "item_code"
			)
			required_qty = sum(
				flt(d.required_qty)
				for d in subcontract_order.supplied_items
				if d.rm_item_code == original_item_code
			)
		if not required_qty:
			frappe.throw(
				_("Item {0} not found in 'Raw Materials Supplied' table in {1} {2}").format(
					item_code,
					self.doc.subcontract_data.order_doctype,
					self.doc.get(self.doc.subcontract_data.order_field),
				)
			)
		return required_qty

	def _validate_transfer_qty(self, child_row, item_code, total_allowed, earlier_rows_qty, stock_qty):
		total_supplied = self.get_total_supplied_qty(item_code)
		total_returned = (
			self.get_total_returned_qty(item_code)
			if self.doc.subcontract_data.order_doctype == "Subcontracting Order"
			else 0
		)
		if flt(
			total_supplied + earlier_rows_qty + stock_qty - total_returned,
			child_row.precision("transfer_qty"),
		) > flt(total_allowed, child_row.precision("transfer_qty")):
			frappe.throw(
				_("Row #{0}: Item {1} cannot be transferred more than {2} against {3} {4}").format(
					child_row.idx,
					item_code,
					total_allowed,
					self.doc.subcontract_data.order_doctype,
					self.doc.get(self.doc.subcontract_data.order_field),
				)
			)

	def _link_rm_detail_if_missing(self, child_row, item_code):
		if not child_row.get(self.doc.subcontract_data.rm_detail_field):
			order_rm_detail = self.get_order_rm_detail(child_row)
			if order_rm_detail:
				child_row.db_set(self.doc.subcontract_data.rm_detail_field, order_rm_detail)
			elif not child_row.allow_alternative_item:
				frappe.throw(
					_("Row #{0}: Item {1} not found in 'Raw Materials Supplied' table in {2} {3}").format(
						child_row.idx,
						item_code,
						self.doc.subcontract_data.order_doctype,
						self.doc.get(self.doc.subcontract_data.order_field),
					)
				)

	def get_order_finished_goods(self):
		return set(
			frappe.get_all(
				f"{self.doc.subcontract_data.order_doctype} Item",
				filters={"parent": self.doc.get(self.doc.subcontract_data.order_field)},
				pluck="item_code",
			)
		)

	def get_finished_good_of_order_rows(self):
		"""Finished good of each raw material row of the order."""
		return dict(
			frappe.get_all(
				self.doc.subcontract_data.order_supplied_items_field,
				filters={"parent": self.doc.get(self.doc.subcontract_data.order_field)},
				fields=["name", "main_item_code"],
				as_list=True,
			)
		)

	def validate_subcontracting_order_for_transfer(self, child_row, finished_goods, finished_good_of_rows):
		if not child_row.subcontracted_item:
			frappe.throw(
				_("Row {0}: Subcontracted Item is mandatory for the raw material {1}").format(
					child_row.idx, bold(child_row.item_code)
				)
			)

		if child_row.subcontracted_item not in finished_goods:
			frappe.throw(
				_("Row {0}: Subcontracted Item {1} is not a finished good of {2} {3}").format(
					child_row.idx,
					bold(child_row.subcontracted_item),
					self.doc.subcontract_data.order_doctype,
					self.doc.get(self.doc.subcontract_data.order_field),
				)
			)

		rm_detail_field = self.doc.subcontract_data.rm_detail_field
		if finished_good_of_rows.get(child_row.get(rm_detail_field)) != child_row.subcontracted_item:
			order_rm_detail = self.get_order_rm_detail(child_row)
			if order_rm_detail != child_row.get(rm_detail_field):
				child_row.db_set(rm_detail_field, order_rm_detail)

	def get_total_supplied_qty(self, item_code):
		se = frappe.qb.DocType("Stock Entry")
		sed = frappe.qb.DocType("Stock Entry Detail")
		order_filter = self._get_supplied_qty_order_filter(se, sed)
		return (
			frappe.qb.from_(se)
			.inner_join(sed)
			.on(se.name == sed.parent)
			.select(Sum(sed.transfer_qty))
			.where(
				(se.purpose == "Send to Subcontractor")
				& (se.docstatus == 1)
				& (Coalesce(NullIf(sed.original_item, ""), sed.item_code) == item_code)
				& order_filter
			)
		).run()[0][0] or 0

	def _get_supplied_qty_order_filter(self, se, sed):
		if self.doc.subcontract_data.order_doctype == "Purchase Order":
			return (se.purchase_order == self.doc.purchase_order) & (sed.po_detail == self.doc.po_detail)
		return se.subcontracting_order == self.doc.subcontracting_order

	def get_total_returned_qty(self, item_code):
		se = frappe.qb.DocType("Stock Entry")
		sed = frappe.qb.DocType("Stock Entry Detail")
		return (
			frappe.qb.from_(se)
			.inner_join(sed)
			.on(se.name == sed.parent)
			.select(Sum(sed.transfer_qty))
			.where(
				(se.purpose == "Material Transfer")
				& (se.docstatus == 1)
				& (se.is_return == 1)
				& (Coalesce(NullIf(sed.original_item, ""), sed.item_code) == item_code)
				& (se.subcontracting_order == self.doc.subcontracting_order)
			)
		).run()[0][0] or 0

	def get_order_rm_detail(self, child_row):
		filters = {
			"parent": self.doc.get(self.doc.subcontract_data.order_field),
			"docstatus": 1,
			"rm_item_code": child_row.original_item or child_row.item_code,
			"main_item_code": child_row.subcontracted_item,
		}

		return frappe.db.get_value(self.doc.subcontract_data.order_supplied_items_field, filters, "name")

	def on_submit(self):
		self.update_subcontract_order_supplied_items()

	def on_cancel(self):
		self.update_subcontract_order_supplied_items()
		self.update_consumed_qty_in_order()

	def update_consumed_qty_in_order(self):
		"""Count the order's consumption again on the transfers left, and block a cancel that leaves some unsupplied."""
		order = self.doc.get(self.doc.subcontract_data.order_field)
		if not order:
			return

		self.validate_reservation_is_not_consumed(order)
		# one cancel of the order's transfers at a time
		order_doc = frappe.get_doc(self.doc.subcontract_data.order_doctype, order, for_update=True)
		order_doc.set_consumed_qty_in_subcontract_order()
		self.validate_consumed_batches_are_supplied(order_doc)

		item_codes = list({row.item_code for row in self.doc.items})
		net_qty_sent = self.get_net_qty_sent(order, item_codes)
		consumed_qty = get_consumed_qty_by_item(order, item_codes)
		precision = frappe.get_precision(self.doc.subcontract_data.order_supplied_items_field, "consumed_qty")
		for item_code in item_codes:
			qty = flt(consumed_qty.get(item_code, 0) - net_qty_sent.get(item_code, 0), precision)
			if qty > 0:
				frappe.throw(
					_(
						"Cannot cancel: {0} {1} would then supply {2} less of Item {3} than its receipts already consumed and its returns took back."
					).format(self.doc.subcontract_data.order_doctype, order, qty, item_code)
				)

	def validate_consumed_batches_are_supplied(self, order_doc):
		"""The order's other transfers must still supply what its receipts consumed of the batches this entry sent."""
		batches = self.get_batches_sent()
		precision = frappe.get_precision(self.doc.subcontract_data.order_supplied_items_field, "consumed_qty")
		for (item_code, batch_no), qty in order_doc.get("unsupplied_batch_qty", default={}).items():
			qty = flt(qty, precision)
			if batch_no in batches and qty > 0:
				frappe.throw(
					_(
						"Cannot cancel: {0} {1} would then supply {2} less of Batch {3} of Item {4} than its receipts already consumed."
					).format(order_doc.doctype, order_doc.name, qty, batch_no, item_code)
				)

	def get_batches_sent(self):
		"""Batches this entry sent to the supplier."""
		bundles = [row.serial_and_batch_bundle for row in self.doc.items if row.serial_and_batch_bundle]
		return {row.batch_no for row in self.doc.items if row.batch_no} | set(
			get_batches_from_bundle(bundles)
		)

	def validate_reservation_is_not_consumed(self, order):
		"""Receipts keep the supplier warehouse reservation of this entry they consumed; the cancel cannot move it to another."""
		if frappe.db.exists(
			"Stock Reservation Entry",
			{
				"from_voucher_type": "Stock Entry",
				"from_voucher_no": self.doc.name,
				"docstatus": 1,
				"consumed_qty": (">", 0),
			},
		):
			frappe.throw(
				_(
					"Cannot cancel: receipts of {0} {1} already consumed the stock this entry reserved at the supplier. Cancel those receipts first."
				).format(self.doc.subcontract_data.order_doctype, order)
			)

	def get_net_qty_sent(self, order, item_codes):
		"""Net qty of each item the order's transfers and their returns still supply."""
		se = frappe.qb.DocType("Stock Entry")
		se_detail = frappe.qb.DocType("Stock Entry Detail")
		qty = Case().when(se.is_return == 1, -se_detail.transfer_qty).else_(se_detail.transfer_qty)
		rows = (
			frappe.qb.from_(se)
			.inner_join(se_detail)
			.on(se.name == se_detail.parent)
			.select(se_detail.item_code, Sum(qty))
			.where(
				(se.docstatus == 1)
				& (se[self.doc.subcontract_data.order_field] == order)
				& se_detail.item_code.isin(item_codes)
				& (
					(se.purpose == "Send to Subcontractor")
					| ((se.purpose == "Material Transfer") & (se.is_return == 1))
				)
			)
			.groupby(se_detail.item_code)
		).run()

		return dict(rows)

	def update_subcontract_order_supplied_items(self):
		if not self.doc.get(self.doc.subcontract_data.order_field):
			return
		order_supplied_items = self._get_order_supplied_items()
		supplied_items = self._get_supplied_items_details()
		self._update_supplied_items_in_order(order_supplied_items, supplied_items)
		self._update_reserved_qty_for_subcontracting(order_supplied_items)

	def _get_order_supplied_items(self):
		return frappe.db.get_all(
			self.doc.subcontract_data.order_supplied_items_field,
			filters={"parent": self.doc.get(self.doc.subcontract_data.order_field)},
			fields=["name", "rm_item_code", "reserve_warehouse"],
		)

	def _get_supplied_items_details(self):
		return get_supplied_items(
			self.doc.get(self.doc.subcontract_data.order_field),
			self.doc.subcontract_data.rm_detail_field,
			self.doc.subcontract_data.order_field,
		)

	def _update_supplied_items_in_order(self, order_supplied_items, supplied_items):
		for row in order_supplied_items:
			item = supplied_items.get(row.name) or {
				"supplied_qty": 0,
				"returned_qty": 0,
				"total_supplied_qty": 0,
			}
			frappe.db.set_value(self.doc.subcontract_data.order_supplied_items_field, row.name, item)

	def _update_reserved_qty_for_subcontracting(self, order_supplied_items):
		item_wh = {x.get("rm_item_code"): x.get("reserve_warehouse") for x in order_supplied_items}
		for d in self.doc.get("items"):
			item_code = d.get("original_item") or d.get("item_code")
			reserve_warehouse = item_wh.get(item_code)
			if not (reserve_warehouse and item_code):
				continue
			stock_bin = get_bin(item_code, reserve_warehouse)
			stock_bin.update_reserved_qty_for_sub_contracting()


def get_supplied_items(
	subcontract_order, rm_detail_field="sco_rm_detail", subcontract_order_field="subcontracting_order"
):
	fields = [
		"`tabStock Entry Detail`.`transfer_qty`",
		"`tabStock Entry`.`is_return`",
		f"`tabStock Entry Detail`.`{rm_detail_field}`",
		"`tabStock Entry Detail`.`item_code`",
	]

	filters = [
		["Stock Entry", "docstatus", "=", 1],
		["Stock Entry", subcontract_order_field, "=", subcontract_order],
	]

	supplied_item_details = {}
	for row in frappe.get_all("Stock Entry", fields=fields, filters=filters):
		if not row.get(rm_detail_field):
			continue

		key = row.get(rm_detail_field)
		if key not in supplied_item_details:
			supplied_item_details.setdefault(
				key, frappe._dict({"supplied_qty": 0, "returned_qty": 0, "total_supplied_qty": 0})
			)

		supplied_item = supplied_item_details[key]

		if row.is_return:
			supplied_item.returned_qty += row.transfer_qty
		else:
			supplied_item.supplied_qty += row.transfer_qty

		supplied_item.total_supplied_qty = flt(supplied_item.supplied_qty) - flt(supplied_item.returned_qty)

	return supplied_item_details


@frappe.whitelist()
def get_items_from_subcontract_order(source_name: str, target_doc: str | dict | Document | None = None):
	from erpnext.controllers.subcontracting_controller import make_rm_stock_entry

	target_doc = frappe.get_doc(frappe.parse_json(target_doc))
	target_doc.purchase_order = None
	target_doc = make_rm_stock_entry(subcontract_order=source_name, target_doc=target_doc)

	return target_doc


def get_consumed_qty_by_item(order, item_codes):
	"""Qty of each item the order's subcontracting receipts consumed, net of their returns."""
	supplied_item = frappe.qb.DocType("Subcontracting Receipt Supplied Item")
	receipt_item = frappe.qb.DocType("Subcontracting Receipt Item")
	rows = (
		frappe.qb.from_(supplied_item)
		.inner_join(receipt_item)
		.on(receipt_item.name == supplied_item.reference_name)
		.select(supplied_item.rm_item_code, Sum(supplied_item.consumed_qty))
		.where(
			(supplied_item.docstatus == 1)
			& (receipt_item.subcontracting_order == order)
			& supplied_item.rm_item_code.isin(item_codes)
		)
		.groupby(supplied_item.rm_item_code)
	).run()

	return dict(rows)
