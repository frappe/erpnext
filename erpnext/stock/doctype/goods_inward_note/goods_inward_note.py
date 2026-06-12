# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Custody before ownership: goods that have physically arrived but are not stock yet.

A consignment waiting at a custody point — a factory gate, a customs area, a
port warehouse — is recorded here against its order, without any stock or
accounting impact: nothing is owned until a receipt is made from this note.
One note follows the consignment from its first custody point to receipt; the
current location is updated as it moves, and quality triggers may demand an
inspection before the goods are allowed to become stock at all.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_link_to_form

ORDER_ITEM_DOCTYPES = {
	"Purchase Order": "Purchase Order Item",
	"Subcontracting Order": "Subcontracting Order Item",
}
RECEIPT_DOCTYPES = {
	"Purchase Order": "Purchase Receipt",
	"Subcontracting Order": "Subcontracting Receipt",
}


class GoodsInwardNote(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.goods_inward_note_item.goods_inward_note_item import (
			GoodsInwardNoteItem,
		)

		amended_from: DF.Link | None
		arrived_on: DF.Datetime
		company: DF.Link
		current_inward_location: DF.Link
		customs_reference: DF.Data | None
		gross_weight: DF.Float
		items: DF.Table[GoodsInwardNoteItem]
		naming_series: DF.Literal["GIN-.YYYY.-"]
		net_weight: DF.Float
		order: DF.DynamicLink
		order_type: DF.Literal["Purchase Order", "Subcontracting Order"]
		remarks: DF.Text | None
		status: DF.Literal["In Custody", "Partially Received", "Received", "Returned"]
		supplier: DF.Link
		supplier_document_date: DF.Date | None
		supplier_document_number: DF.Data | None
		tare_weight: DF.Float
		transport_document_date: DF.Date | None
		transport_document_number: DF.Data | None
		transporter: DF.Link | None
		vehicle_number: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.set_details_from_order()
		self.validate_items_against_order()
		self.validate_quantities()
		self.validate_arrivals_against_order_qty()
		self.set_net_weight()
		self.set_status()

	def on_submit(self):
		self.notify_pending_inspections()

	def notify_pending_inspections(self):
		"""Custody never waits for quality: arrival is a fact, the note records it.

		Items whose triggers demand a custody inspection are flagged here — their
		quantities stay out of receipts until an inspection at the inward location
		decides them.
		"""
		from erpnext.stock.services.quality_trigger_resolution import resolve_inspection_points

		pending = sorted(
			{
				point.item_code
				for point in resolve_inspection_points(self)
				if point.quality_control_mode in ("Block", "Warn") and not point.row.get("quality_inspection")
			}
		)
		if pending:
			frappe.msgprint(
				_("Quality inspection pending at {0} for: {1}.").format(
					get_link_to_form("Inward Location", self.current_inward_location),
					", ".join(get_link_to_form("Item", item) for item in pending),
				),
				title=_("Inspect In Custody"),
				indicator="orange",
				alert=True,
			)

	def on_update_after_submit(self):
		self.validate_quantities()
		self.update_status()

	def update_status(self):
		# runs after the database write: the recomputed status must persist itself
		self.set_status()
		self.db_set("status", self.status, update_modified=False)

	def set_details_from_order(self):
		order = frappe.db.get_value(
			self.order_type, self.order, ["supplier", "company", "docstatus", "status"], as_dict=True
		)
		if not order:
			return
		if order.docstatus != 1:
			frappe.throw(
				_("{0} {1} is not submitted.").format(
					_(self.order_type), get_link_to_form(self.order_type, self.order)
				)
			)
		if order.status == "Closed":
			frappe.throw(
				_("{0} {1} is closed.").format(
					_(self.order_type), get_link_to_form(self.order_type, self.order)
				)
			)
		self.supplier = order.supplier
		self.company = order.company

	def validate_items_against_order(self):
		"""Every arrival row fulfils a row of the order it references."""
		order_items = {
			row.name: row
			for row in frappe.get_all(
				ORDER_ITEM_DOCTYPES[self.order_type],
				filters={"parent": self.order},
				fields=["name", "item_code"],
			)
		}
		items_on_order = {row.item_code for row in order_items.values()}

		for row in self.items:
			if row.order_item and row.order_item not in order_items:
				frappe.throw(
					_("Row #{0}: Order Item {1} is not on {2}.").format(
						row.idx, row.order_item, get_link_to_form(self.order_type, self.order)
					)
				)
			if row.order_item and order_items[row.order_item].item_code != row.item_code:
				frappe.throw(
					_("Row #{0}: Order Item {1} is for {2}, not {3}.").format(
						row.idx,
						row.order_item,
						get_link_to_form("Item", order_items[row.order_item].item_code),
						get_link_to_form("Item", row.item_code),
					)
				)
			if not row.order_item:
				if row.item_code not in items_on_order:
					frappe.throw(
						_("Row #{0}: Item {1} is not on {2}.").format(
							row.idx,
							get_link_to_form("Item", row.item_code),
							get_link_to_form(self.order_type, self.order),
						)
					)
				row.order_item = next(
					name for name, order_row in order_items.items() if order_row.item_code == row.item_code
				)

	def validate_quantities(self):
		for row in self.items:
			if flt(row.qty) <= 0:
				frappe.throw(_("Row #{0}: Quantity must be greater than zero.").format(row.idx))
			if flt(row.returned_qty) < 0 or flt(row.received_qty) < 0:
				frappe.throw(_("Row #{0}: Quantities cannot be negative.").format(row.idx))
			if flt(row.received_qty) + flt(row.returned_qty) > flt(row.qty):
				frappe.throw(
					_(
						"Row #{0}: Received ({1}) plus returned ({2}) cannot exceed the {3} unit(s) "
						"that arrived."
					).format(row.idx, row.received_qty, row.returned_qty, row.qty),
					title=_("More Than Arrived"),
				)

	def validate_arrivals_against_order_qty(self):
		"""All arrivals together may not overshoot the order (plus allowance).

		An order row is claimed by this note, by other submitted notes (less what
		went back with the truck — its replacement may arrive again), and by
		receipts made directly against the order outside any note. Receipts drawn
		from a note are already inside that note's claim.
		"""
		from erpnext.controllers.status_updater import get_allowance_for

		claimed = {}
		for row in self.items:
			claimed[row.order_item] = claimed.get(row.order_item, 0) + flt(row.qty)

		for other in frappe.get_all(
			"Goods Inward Note Item",
			filters={
				"order_item": ("in", list(claimed)),
				"docstatus": 1,
				"parent": ("!=", self.name),
			},
			fields=["order_item", "qty", "returned_qty"],
		):
			claimed[other.order_item] += flt(other.qty) - flt(other.returned_qty)

		order_item_field = (
			"purchase_order_item" if self.order_type == "Purchase Order" else "subcontracting_order_item"
		)
		for received in frappe.get_all(
			RECEIPT_DOCTYPES[self.order_type] + " Item",
			filters={
				order_item_field: ("in", list(claimed)),
				"docstatus": 1,
				"goods_inward_note": ("is", "not set"),
			},
			fields=[f"{order_item_field} as order_item", "received_qty", "qty"],
		):
			claimed[received.order_item] += flt(received.received_qty) or flt(received.qty)

		item_allowance = {}
		global_qty_allowance = global_amount_allowance = None
		for order_row in frappe.get_all(
			ORDER_ITEM_DOCTYPES[self.order_type],
			filters={"name": ("in", list(claimed))},
			fields=["name", "item_code", "qty"],
		):
			allowance, item_allowance, global_qty_allowance, global_amount_allowance = get_allowance_for(
				order_row.item_code, item_allowance, global_qty_allowance, global_amount_allowance, "qty"
			)
			allowed = flt(order_row.qty) * (100 + flt(allowance)) / 100
			if flt(claimed[order_row.name] - allowed, 6) > 0:
				frappe.throw(
					_(
						"With this note, {0} unit(s) of {1} would have arrived against {2}, which "
						"orders only {3} (allowance included). Other open notes and receipts "
						"already claim the rest."
					).format(
						claimed[order_row.name],
						get_link_to_form("Item", order_row.item_code),
						get_link_to_form(self.order_type, self.order),
						allowed,
					),
					title=_("More Than Ordered"),
				)

	def set_net_weight(self):
		if self.gross_weight or self.tare_weight:
			self.net_weight = flt(self.gross_weight) - flt(self.tare_weight)

	def set_status(self):
		total = sum(flt(row.qty) for row in self.items)
		received = sum(flt(row.received_qty) for row in self.items)
		returned = sum(flt(row.returned_qty) for row in self.items)

		if received + returned >= total and total > 0:
			self.status = "Received" if received > 0 else "Returned"
		elif received > 0:
			self.status = "Partially Received"
		else:
			self.status = "In Custody"

	def outstanding_qty(self, row):
		"""What may still be received: arrived, minus received, minus returned."""
		return flt(row.qty) - flt(row.received_qty) - flt(row.returned_qty)

	@frappe.whitelist()
	def get_items_from_order(self):
		"""Prefill arrival rows from the order — the operator corrects quantities."""
		# the form syncs this document back: supplier and company arrive with the
		# rows, so the client-side mandatory check is already satisfied
		self.set_details_from_order()
		received_by_order_item = self._received_against_order()
		self.set("items", [])
		for row in frappe.get_all(
			ORDER_ITEM_DOCTYPES[self.order_type],
			filters={"parent": self.order},
			fields=["name", "item_code", "item_name", "qty", "stock_uom"],
			order_by="idx",
		):
			pending = flt(row.qty) - received_by_order_item.get(row.name, 0)
			if pending <= 0:
				continue
			self.append(
				"items",
				{
					"item_code": row.item_code,
					"item_name": row.item_name,
					"qty": pending,
					"uom": row.stock_uom,
					"order_item": row.name,
				},
			)

	def _received_against_order(self):
		"""Order quantities already covered by receipts or other open notes."""
		covered = {}
		receipt_item_doctype = RECEIPT_DOCTYPES[self.order_type] + " Item"
		order_field = "purchase_order" if self.order_type == "Purchase Order" else "subcontracting_order"
		for row in frappe.get_all(
			receipt_item_doctype,
			filters={order_field: self.order, "docstatus": 1},
			fields=[f"{order_field}_item as order_item", "qty"],
		):
			covered[row.order_item] = covered.get(row.order_item, 0) + flt(row.qty)
		for row in frappe.get_all(
			"Goods Inward Note Item",
			filters={
				"parenttype": "Goods Inward Note",
				"docstatus": 1,
				"order_item": ("is", "set"),
			},
			fields=["order_item", "qty", "received_qty", "returned_qty"],
		):
			# an open note already accounts for its unreceived quantity
			covered[row.order_item] = covered.get(row.order_item, 0) + self.outstanding_qty(row)
		return covered


def get_custody_verdicts(row_name, exclude_inspection=None):
	"""Submitted verdicts on a note row, summed across batch inspections.

	A row may be inspected a tranche at a time: each Each Quantity inspection
	decides its unit quantity, while a Sample or manual verdict decides the
	whole row at once. Returns how many units the verdicts decided and how
	many of those they rejected, both capped at what arrived.
	"""
	row_qty = flt(frappe.db.get_value("Goods Inward Note Item", row_name, "qty"))
	filters = {
		"reference_type": "Goods Inward Note",
		"child_row_reference": row_name,
		"docstatus": 1,
	}
	if exclude_inspection:
		filters["name"] = ("!=", exclude_inspection)

	decided = rejected = 0.0
	for verdict in frappe.get_all(
		"Quality Inspection",
		filters=filters,
		fields=[
			"inspection_basis",
			"manual_inspection",
			"status",
			"unit_quantity",
			"rejected_unit_quantity",
		],
	):
		if verdict.inspection_basis == "Each Quantity" and not verdict.manual_inspection:
			decided += flt(verdict.unit_quantity)
			rejected += flt(verdict.rejected_unit_quantity)
		else:
			decided = row_qty
			if verdict.status == "Rejected":
				rejected = row_qty
	return frappe._dict(decided=min(decided, row_qty), rejected=min(rejected, row_qty))
