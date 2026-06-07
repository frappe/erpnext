# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Status computation and progress tracking for Sales Order."""

import frappe
from frappe import _
from frappe.desk.notifications import clear_doctype_notifications
from frappe.utils import cint, cstr, flt

from erpnext.selling.doctype.sales_order.services.subcontracting import SubcontractingService


class StatusService:
	def __init__(self, doc):
		self.doc = doc

	def set_default_statuses(self) -> None:
		doc = self.doc
		if not doc.billing_status:
			doc.billing_status = "Not Billed"
		if not doc.delivery_status:
			doc.delivery_status = "Not Delivered"
		if not doc.advance_payment_status:
			doc.advance_payment_status = "Not Requested"

	def update_status(self, status: str) -> None:
		doc = self.doc
		self.check_modified_date()
		doc.set_status(update=True, status=status)
		# Upon Sales Order Re-open, check for credit limit.
		# Limit should be checked after the 'Hold/Closed' status is reset.
		if status == "Draft" and doc.docstatus == 1:
			doc.check_credit_limit()
		doc.update_reserved_qty()
		SubcontractingService(doc).update_subcontracting_order_status()
		doc.notify_update()
		clear_doctype_notifications(doc)
		doc.update_blanket_order()

	def check_modified_date(self) -> None:
		doc = self.doc
		mod_db = frappe.db.get_value("Sales Order", doc.name, "modified")
		if mod_db and cstr(mod_db) != cstr(doc.modified):
			frappe.throw(_("{0} {1} has been modified. Please refresh.").format(doc.doctype, doc.name))

	def update_delivery_status(self) -> None:
		"""Update delivery status from Purchase Order for drop shipping"""
		doc = self.doc
		tot_qty, delivered_qty = 0.0, 0.0

		for item in doc.items:
			if item.delivered_by_supplier:
				item_delivered_qty = frappe.get_all(
					"Purchase Order Item",
					{"sales_order_item": item.name, "docstatus": 1},
					[{"SUM": "received_qty", "AS": "received_qty"}],
					pluck="received_qty",
				)[0]
				item.db_set("delivered_qty", flt(item_delivered_qty), update_modified=False)

			delivered_qty += min(item.delivered_qty, item.qty)
			tot_qty += item.qty

		if tot_qty != 0:
			doc.db_set("per_delivered", flt(delivered_qty / tot_qty) * 100, update_modified=False)

	def update_picking_status(self) -> None:
		doc = self.doc
		total_picked_qty = 0.0
		total_qty = 0.0
		per_picked = 0.0

		for so_item in doc.items:
			if cint(
				frappe.get_cached_value("Item", so_item.item_code, "is_stock_item")
			) or doc.has_product_bundle(so_item.item_code):
				total_picked_qty += flt(so_item.picked_qty)
				total_qty += flt(so_item.stock_qty)

		if total_picked_qty and total_qty:
			per_picked = total_picked_qty / total_qty * 100

			pick_percentage = frappe.get_single_value("Stock Settings", "over_picking_allowance")
			if pick_percentage:
				total_qty += flt(total_qty) * (pick_percentage / 100)

			if total_picked_qty > total_qty:
				frappe.throw(
					_(
						"Total Picked Quantity {0} is more than ordered qty {1}. You can set the Over Picking Allowance in Stock Settings."
					).format(total_picked_qty, total_qty)
				)

		doc.db_set("per_picked", flt(per_picked), update_modified=False)

	def set_indicator(self) -> None:
		"""Set indicator for portal"""
		doc = self.doc
		doc.indicator_color = {
			"Draft": "red",
			"On Hold": "orange",
			"To Deliver and Bill": "orange",
			"To Bill": "orange",
			"To Deliver": "orange",
			"Completed": "green",
			"Cancelled": "red",
		}.get(doc.status, "blue")

		doc.indicator_title = _(doc.status)
