# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Status transitions and receiving progress for Purchase Order."""

from collections import defaultdict

import frappe
from frappe import _
from frappe.desk.notifications import clear_doctype_notifications
from frappe.query_builder.functions import Sum
from frappe.utils import cstr, flt, getdate, nowdate

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
		for item in [item for item in doc.items if not item.closed] or doc.items:
			received_qty += min(item.received_qty, item.qty)
			total_qty += item.qty

		per_received = flt(received_qty / total_qty) * 100 if total_qty else 0
		doc.db_set("per_received", per_received, update_modified=False)

	def update_supplier_quotation_status(self) -> None:
		supplier_quotations = {item.supplier_quotation for item in self.doc.items if item.supplier_quotation}
		update_supplier_quotation_status(supplier_quotations)


def update_supplier_quotation_status(
	supplier_quotations: set[str] | list[str], *, update_modified: bool = True
) -> None:
	if not supplier_quotations:
		return

	quotation_items = _get_supplier_quotation_items(supplier_quotations)
	ordered_qty_by_item = _get_ordered_qty_by_item(supplier_quotations)
	items_by_quotation = defaultdict(list)
	quotation_by_name = {}

	for item in quotation_items:
		items_by_quotation[item.supplier_quotation].append(item)
		quotation_by_name[item.supplier_quotation] = item

	status_updates = {}
	for name, quotation in quotation_by_name.items():
		status = _get_supplier_quotation_status(quotation, items_by_quotation[name], ordered_qty_by_item)
		if status != quotation.status:
			status_updates[name] = {"status": status}

	frappe.db.bulk_update("Supplier Quotation", status_updates, update_modified=update_modified)


def _get_supplier_quotation_items(supplier_quotations):
	supplier_quotation = frappe.qb.DocType("Supplier Quotation")
	supplier_quotation_item = frappe.qb.DocType("Supplier Quotation Item")

	return (
		frappe.qb.from_(supplier_quotation)
		.inner_join(supplier_quotation_item)
		.on(supplier_quotation_item.parent == supplier_quotation.name)
		.select(
			supplier_quotation.name.as_("supplier_quotation"),
			supplier_quotation.status,
			supplier_quotation.docstatus,
			supplier_quotation.valid_till,
			supplier_quotation_item.name.as_("supplier_quotation_item"),
			supplier_quotation_item.stock_qty,
		)
		.where(supplier_quotation.name.isin(supplier_quotations))
	).run(as_dict=True)


def _get_ordered_qty_by_item(supplier_quotations):
	purchase_order_item = frappe.qb.DocType("Purchase Order Item")
	ordered_items = (
		frappe.qb.from_(purchase_order_item)
		.select(
			purchase_order_item.supplier_quotation_item,
			Sum(purchase_order_item.stock_qty).as_("ordered_qty"),
		)
		.where(
			(purchase_order_item.docstatus == 1)
			& (purchase_order_item.supplier_quotation.isin(supplier_quotations))
			& purchase_order_item.supplier_quotation_item.isnotnull()
		)
		.groupby(purchase_order_item.supplier_quotation_item)
	).run(as_dict=True)

	return {item.supplier_quotation_item: item.ordered_qty for item in ordered_items}


def _get_supplier_quotation_status(quotation, items, ordered_qty_by_item):
	if quotation.docstatus == 2:
		return "Cancelled"

	if any(item.supplier_quotation_item in ordered_qty_by_item for item in items):
		is_fully_ordered = all(
			item.supplier_quotation_item in ordered_qty_by_item
			and flt(item.stock_qty) <= flt(ordered_qty_by_item[item.supplier_quotation_item])
			for item in items
		)
		return "Ordered" if is_fully_ordered else "Partially Ordered"

	if quotation.docstatus == 1 and quotation.valid_till:
		if getdate(quotation.valid_till) < getdate(nowdate()):
			return "Expired"

	if quotation.status == "Stopped":
		return "Stopped"

	return "Submitted" if quotation.docstatus == 1 else "Draft"
