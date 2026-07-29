# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Status transitions and receiving progress for Purchase Order."""

import frappe
from frappe import _
from frappe.desk.notifications import clear_doctype_notifications
from frappe.utils import cstr, flt

from erpnext.buying.doctype.purchase_order.services.subcontracting import SubcontractingService
from erpnext.controllers.item_close import validate_parent_reopen


class StatusService:
	def __init__(self, doc):
		self.doc = doc

	def update_status(self, status: str) -> None:
		doc = self.doc
		self.check_modified_date()

		if status != "Closed" and doc.status == "Closed":
			validate_parent_reopen(doc)

		doc.set_status(update=True, status=status)
		doc.update_requested_qty()
		doc.update_ordered_qty()
		SubcontractingService(doc).update_subcontracting_order_status()
		doc.update_blanket_order()
		doc.notify_update()
		clear_doctype_notifications(doc)

	def recalculate_after_item_close(self) -> None:
		"""Refresh progress after row flags changed.

		`update_billing_percentage` runs last because it reloads the parent and
		writes the final status from both percentages.
		"""
		doc = self.doc
		self.update_receiving_percentage()
		doc.update_ordered_qty()
		doc.update_billing_percentage()

	def check_modified_date(self) -> None:
		doc = self.doc
		modified_in_db = frappe.db.get_value("Purchase Order", doc.name, "modified")

		if modified_in_db and cstr(modified_in_db) != cstr(doc.modified):
			frappe.msgprint(
				_("{0} {1} has been modified. Please refresh.").format(doc.doctype, doc.name),
				raise_exception=True,
			)

	def update_receiving_percentage(self) -> None:
		doc = self.doc
		total_qty, received_qty = 0.0, 0.0
		for item in doc.items:
			if item.closed:
				continue
			received_qty += min(item.received_qty, item.qty)
			total_qty += item.qty

		if total_qty and received_qty:
			per_received = flt(received_qty / total_qty) * 100
		elif doc.items and not total_qty:
			per_received = 100
		else:
			per_received = 0

		doc.db_set("per_received", per_received, update_modified=False)
