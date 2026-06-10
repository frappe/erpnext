# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""Quarantine actions: mint Quality Control Lots when stock lands in a Quality Control warehouse.

This is deliberately route-agnostic — it reacts to a positive movement into a
Quality warehouse rather than re-resolving the trigger, so it works no matter how
the stock got there (receipt, transfer, redirect).
"""

import frappe
from frappe import _

from erpnext.stock.services.quality_trigger_resolution import (
	INBOUND,
	movements_of,
	resolve_inspection_points,
)
from erpnext.stock.services.quality_warehouse import get_quality_warehouse, is_quality_warehouse


def apply_quarantine_routing(doc):
	"""Redirect Quarantine-triggered inbound rows into the Quality Control warehouse.

	Runs at validate time so the document still submits freely — the gate is on
	the stock (quarantined in the Quality Control warehouse until released), not
	on the document. Rows already pointed at a Quality Control warehouse are left
	alone, which also makes the routing idempotent across repeated validations.
	"""
	target_fieldname = "t_warehouse" if doc.doctype == "Stock Entry" else "warehouse"

	for point in resolve_inspection_points(doc):
		if point.quality_control_mode != "Quarantine" or point.role != INBOUND:
			continue
		if is_quality_warehouse(point.warehouse):
			continue

		quality_warehouse = get_quality_warehouse(point.warehouse)
		if not quality_warehouse:
			frappe.throw(
				_(
					"Row #{0}: Item {1} requires quarantine for quality inspection, but warehouse {2} "
					"has no Quality Control Warehouse configured."
				).format(point.row.idx, frappe.bold(point.item_code), frappe.bold(point.warehouse)),
				title=_("Quality Control Warehouse Missing"),
			)

		point.row.set(target_fieldname, quality_warehouse)
		frappe.msgprint(
			_("Row #{0}: Item {1} is routed to {2} for quality inspection.").format(
				point.row.idx, frappe.bold(point.item_code), frappe.bold(quality_warehouse)
			),
			alert=True,
		)


def block_stock_reconciliation_on_quality_warehouse(doc, method=None):
	"""Stock Reconciliation may not touch a Quality Control warehouse.

	Reconciliation sets absolute quantities, which would silently desynchronise
	the warehouse balance from its Quality Control Lots. Quarantined stock only
	moves through controlled flows (release / return / cancellation).
	"""
	for row in doc.get("items") or []:
		if is_quality_warehouse(row.get("warehouse")):
			frappe.throw(
				_(
					"Row #{0}: {1} is a Quality Control warehouse. Stock Reconciliation is not "
					"allowed on quarantined stock."
				).format(row.idx, frappe.bold(row.warehouse)),
				title=_("Quality Control Warehouse"),
			)


def create_quality_control_lots(doc, method=None):
	"""Mint a Quality Control Lot for each item moving into a Quality warehouse on this document."""
	for row, role, warehouse in movements_of(doc):
		if role != INBOUND or not is_quality_warehouse(warehouse):
			continue

		received_qty = row.get("transfer_qty") or row.get("stock_qty") or row.get("qty")
		if not received_qty:
			continue

		frappe.get_doc(
			{
				"doctype": "Quality Control Lot",
				"item_code": row.get("item_code"),
				"company": doc.get("company"),
				"quality_warehouse": warehouse,
				"batch_no": row.get("batch_no"),
				"received_qty": received_qty,
				"source_document_type": doc.doctype,
				"source_document": doc.name,
			}
		).insert(ignore_permissions=True)
