# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.controllers.status_updater import StatusUpdater


class PackingSlip(StatusUpdater):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.packing_slip_item.packing_slip_item import PackingSlipItem

		amended_from: DF.Link | None
		delivery_note: DF.Link
		from_case_no: DF.Int
		gross_weight_pkg: DF.Float
		gross_weight_uom: DF.Link | None
		items: DF.Table[PackingSlipItem]
		letter_head: DF.Link | None
		naming_series: DF.Literal["MAT-PAC-.YYYY.-"]
		net_weight_pkg: DF.Float
		net_weight_uom: DF.Link | None
		to_case_no: DF.Int
	# end: auto-generated types

	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self.status_updater = [
			{
				"target_dt": "Delivery Note Item",
				"join_field": "dn_detail",
				"target_field": "packed_qty",
				"target_parent_dt": "Delivery Note",
				"target_ref_field": "qty",
				"source_dt": "Packing Slip Item",
				"source_field": "qty",
			},
			{
				"target_dt": "Packed Item",
				"join_field": "pi_detail",
				"target_field": "packed_qty",
				"target_parent_dt": "Delivery Note",
				"target_ref_field": "qty",
				"source_dt": "Packing Slip Item",
				"source_field": "qty",
			},
		]

	def validate(self) -> None:
		from erpnext.utilities.transaction_base import validate_uom_is_integer

		self.validate_delivery_note()
		self.validate_case_nos()
		self.validate_items()

		validate_uom_is_integer(self, "stock_uom", "qty")
		validate_uom_is_integer(self, "weight_uom", "net_weight")

		self.set_missing_values()
		self.calculate_net_total_pkg()

	def on_submit(self):
		self.update_prevdoc_status()

	def on_cancel(self):
		self.update_prevdoc_status()

	def validate_delivery_note(self):
		"""Raises an exception if the `Delivery Note` status is not Draft"""

		if cint(frappe.db.get_value("Delivery Note", self.delivery_note, "docstatus")) != 0:
			frappe.throw(
				_("A Packing Slip can only be created for Draft Delivery Note.").format(self.delivery_note)
			)

	def validate_case_nos(self):
		"""Validate if case nos overlap. If they do, recommend next case no."""

		if cint(self.from_case_no) <= 0:
			frappe.throw(_("The 'From Package No.' field must neither be empty nor it's value less than 1."))
		elif not self.to_case_no:
			self.to_case_no = self.from_case_no
		elif cint(self.to_case_no) < cint(self.from_case_no):
			frappe.throw(_("'To Package No.' cannot be less than 'From Package No.'"))
		else:
			ps = frappe.qb.DocType("Packing Slip")
			res = (
				frappe.qb.from_(ps)
				.select(
					ps.name,
				)
				.where(
					(ps.delivery_note == self.delivery_note)
					& (ps.docstatus == 1)
					& (
						(ps.from_case_no.between(self.from_case_no, self.to_case_no))
						| (ps.to_case_no.between(self.from_case_no, self.to_case_no))
						| ((ps.from_case_no <= self.from_case_no) & (ps.to_case_no >= self.from_case_no))
					)
				)
			).run()

			if res:
				frappe.throw(
					_("""Package No(s) already in use. Try from Package No {0}""").format(
						self.get_recommended_case_no()
					)
				)

	def validate_items(self):
		for item in self.items:
			if item.qty <= 0:
				frappe.throw(_("Row {0}: Qty must be greater than 0.").format(item.idx))

			if not item.dn_detail and not item.pi_detail:
				frappe.throw(
					_("Row {0}: Either Delivery Note Item or Packed Item reference is mandatory.").format(
						item.idx
					)
				)

			remaining_qty = frappe.db.get_value(
				"Delivery Note Item" if item.dn_detail else "Packed Item",
				{"name": item.dn_detail or item.pi_detail, "docstatus": 0},
				["sum(qty - packed_qty)"],
			)

			if remaining_qty is None:
				frappe.throw(
					_("Row {0}: Please provide a valid Delivery Note Item or Packed Item reference.").format(
						item.idx
					)
				)
			elif remaining_qty <= 0:
				frappe.throw(
					_("Row {0}: Packing Slip is already created for Item {1}.").format(
						item.idx, frappe.bold(item.item_code)
					)
				)
			elif item.qty > remaining_qty:
				frappe.throw(
					_("Row {0}: Qty cannot be greater than {1} for the Item {2}.").format(
						item.idx, frappe.bold(remaining_qty), frappe.bold(item.item_code)
					)
				)

	def set_missing_values(self):
		if not self.from_case_no:
			self.from_case_no = self.get_recommended_case_no()

		for item in self.items:
			stock_uom, weight_per_unit, weight_uom = frappe.db.get_value(
				"Item", item.item_code, ["stock_uom", "weight_per_unit", "weight_uom"]
			)

			item.stock_uom = stock_uom
			if weight_per_unit and not item.net_weight:
				item.net_weight = weight_per_unit
			if weight_uom and not item.weight_uom:
				item.weight_uom = weight_uom

	def get_recommended_case_no(self):
		"""Returns the next case no. for a new packing slip for a delivery note"""

		return (
			cint(
				frappe.db.get_value(
					"Packing Slip", {"delivery_note": self.delivery_note, "docstatus": 1}, ["max(to_case_no)"]
				)
			)
			+ 1
		)

	def calculate_net_total_pkg(self):
		self.net_weight_uom = self.items[0].weight_uom if self.items else None
		self.gross_weight_uom = self.net_weight_uom

		net_weight_pkg = 0
		for item in self.items:
			if item.weight_uom != self.net_weight_uom:
				frappe.throw(
					_(
						"Different UOM for items will lead to incorrect (Total) Net Weight value. Make sure that Net Weight of each item is in the same UOM."
					)
				)

			net_weight_pkg += flt(item.net_weight) * flt(item.qty)

		self.net_weight_pkg = round(net_weight_pkg, 2)

		if not flt(self.gross_weight_pkg):
			self.gross_weight_pkg = self.net_weight_pkg


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_details(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	return frappe.db.sql(
		"""select name, item_name, description from `tabItem`
				where name in ( select item_code FROM `tabDelivery Note Item`
	 						where parent= {})
	 			and {} like "{}" {}
	 			limit  {} offset {} """.format("%s", searchfield, "%s", get_match_cond(doctype), "%s", "%s"),
		((filters or {}).get("delivery_note"), "%%%s%%" % txt, page_len, start),
	)
