import json

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import flt

from erpnext.stock.utils import get_bin

from .base import BaseStockEntry


class SendToSubcontractorStockEntry(BaseStockEntry):
	def validate(self):
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
			for se_item in self.doc.items:
				self.validate_subcontracting_order_for_bom(se_item, subcontract_order)

		elif backflush_raw_materials_based_on == "Material Transferred for Subcontract":
			for row in self.doc.items:
				self.validate_subcontracting_order_for_transfer(row)

	def validate_subcontracting_order_for_bom(self, child_row, subcontract_order):
		item_code = child_row.original_item or child_row.item_code
		required_qty = self._get_required_qty_for_bom(item_code, child_row, subcontract_order)
		qty_allowance = flt(frappe.db.get_single_value("Buying Settings", "over_transfer_allowance"))
		total_allowed = required_qty + (required_qty * qty_allowance / 100)
		self._validate_transfer_qty(child_row, item_code, total_allowed)
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

	def _validate_transfer_qty(self, child_row, item_code, total_allowed):
		total_supplied = self.get_total_supplied_qty(child_row)
		total_returned = (
			self.get_total_returned_qty(child_row)
			if self.doc.subcontract_data.order_doctype == "Subcontracting Order"
			else 0
		)
		if flt(
			total_supplied + child_row.transfer_qty - total_returned, child_row.precision("transfer_qty")
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
					_("Row {0}# Item {1} not found in 'Raw Materials Supplied' table in {2} {3}").format(
						child_row.idx,
						item_code,
						self.doc.subcontract_data.order_doctype,
						self.doc.get(self.doc.subcontract_data.order_field),
					)
				)

	def validate_subcontracting_order_for_transfer(self, child_row):
		if not child_row.subcontracted_item:
			frappe.throw(
				_("Row {0}: Subcontracted Item is mandatory for the raw material {1}").format(
					child_row.idx, bold(child_row.item_code)
				)
			)
		elif not child_row.get(self.doc.subcontract_data.rm_detail_field):
			order_rm_detail = self.get_order_rm_detail(child_row)
			if order_rm_detail:
				child_row.db_set(self.doc.subcontract_data.rm_detail_field, order_rm_detail)

	def get_total_supplied_qty(self, child_row):
		se = frappe.qb.DocType("Stock Entry")
		sed = frappe.qb.DocType("Stock Entry Detail")
		order_filter = self._get_supplied_qty_order_filter(se, sed, child_row)
		return (
			frappe.qb.from_(se)
			.inner_join(sed)
			.on(se.name == sed.parent)
			.select(Sum(sed.transfer_qty))
			.where(
				(se.purpose == "Send to Subcontractor")
				& (se.docstatus == 1)
				& (sed.item_code == child_row.item_code)
				& order_filter
			)
		).run()[0][0] or 0

	def _get_supplied_qty_order_filter(self, se, sed, child_row):
		if self.doc.subcontract_data.order_doctype == "Purchase Order":
			return (se.purchase_order == self.doc.purchase_order) & (sed.po_detail == self.doc.po_detail)
		return (se.subcontracting_order == self.doc.subcontracting_order) & (
			sed.sco_rm_detail == child_row.sco_rm_detail
		)

	def get_total_returned_qty(self, child_row):
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
				& (sed.item_code == child_row.item_code)
				& (sed.sco_rm_detail == child_row.sco_rm_detail)
				& (se.subcontracting_order == self.doc.subcontracting_order)
			)
		).run()[0][0] or 0

	def get_order_rm_detail(self, child_row):
		filters = {
			"parent": self.doc.get(self.doc.subcontract_data.order_field),
			"docstatus": 1,
			"rm_item_code": child_row.item_code,
			"main_item_code": child_row.subcontracted_item,
		}

		return frappe.db.get_value(self.doc.subcontract_data.order_supplied_items_field, filters, "name")

	def on_submit(self):
		self.update_subcontract_order_supplied_items()

	def on_cancel(self):
		self.update_subcontract_order_supplied_items()

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
def get_items_from_subcontract_order(source_name: str, target_doc: str | Document | None = None):
	from erpnext.controllers.subcontracting_controller import make_rm_stock_entry

	if isinstance(target_doc, str):
		target_doc = frappe.get_doc(json.loads(target_doc))

	order_doctype = "Purchase Order" if target_doc.purchase_order else "Subcontracting Order"
	target_doc = make_rm_stock_entry(
		subcontract_order=source_name, order_doctype=order_doctype, target_doc=target_doc
	)

	return target_doc
