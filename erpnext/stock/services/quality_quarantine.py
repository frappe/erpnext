# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""Quarantine actions: mint Quality Control Lots when stock lands in a Quality Control warehouse.

This is deliberately route-agnostic — it reacts to a positive movement into a
Quality warehouse rather than re-resolving the trigger, so it works no matter how
the stock got there (receipt, transfer, redirect).
"""

import frappe
from frappe import _
from frappe.utils import flt

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


def get_release_warehouse(quality_warehouse):
	"""The store warehouse to release accepted stock into.

	Resolved by reverse lookup: the warehouse whose quality_warehouse points at
	this Quality Control warehouse. Ambiguous (several stores sharing one Quality
	Control warehouse) resolves to None — the user releases manually and picks the
	target.
	"""
	stores = frappe.get_all(
		"Warehouse", filters={"quality_warehouse": quality_warehouse, "disabled": 0}, pluck="name"
	)
	return stores[0] if len(stores) == 1 else None


def process_inspection_result(doc, method=None):
	"""React to a submitted Quality Inspection that decides a Quality Control Lot.

	Accepted: auto-create a Quality Control Release moving the pending quantity to
	the store warehouse (when it can be resolved unambiguously). Rejected: record
	the rejection on the lot — the stock stays quarantined until it is sent back
	with a purchase return.
	"""
	if doc.reference_type != "Quality Control Lot" or not doc.reference_name:
		return

	lot = frappe.get_doc("Quality Control Lot", doc.reference_name)
	if not flt(lot.pending_qty):
		return

	if doc.status == "Rejected":
		lot.rejected_qty = flt(lot.rejected_qty) + flt(lot.pending_qty)
		lot.flags.ignore_permissions = True
		lot.save()
		return

	release_warehouse = get_release_warehouse(lot.quality_warehouse)
	if not release_warehouse:
		frappe.msgprint(
			_(
				"Quality Control Lot {0} is accepted, but no unique release warehouse points at {1}. "
				"Create the Quality Control Release manually."
			).format(frappe.bold(lot.name), frappe.bold(lot.quality_warehouse)),
			alert=True,
		)
		return

	release = frappe.new_doc("Stock Entry")
	release.purpose = "Quality Control Release"
	release.stock_entry_type = "Quality Control Release"
	release.company = lot.company
	release.quality_control_lot = lot.name
	release.append(
		"items",
		{
			"item_code": lot.item_code,
			"qty": lot.pending_qty,
			"s_warehouse": lot.quality_warehouse,
			"t_warehouse": release_warehouse,
			"batch_no": lot.batch_no,
		},
	)
	release.flags.ignore_permissions = True
	release.insert()
	release.submit()

	frappe.msgprint(
		_("Quality Control Release {0} created: {1} released to {2}.").format(
			frappe.utils.get_link_to_form("Stock Entry", release.name),
			lot.pending_qty,
			frappe.bold(release_warehouse),
		),
		alert=True,
	)


def handle_source_document_cancel(doc, method=None):
	"""Cascade a source-document cancellation onto its Quality Control Lots.

	An untouched lot (nothing released or rejected yet) is deleted along with the
	reversed stock. A lot that already released or rejected quantity blocks the
	cancellation — the Quality Control Release or purchase return must be
	unwound first, mirroring how ERPNext blocks cancelling documents with
	downstream submitted documents.
	"""
	lots = frappe.get_all(
		"Quality Control Lot",
		filters={"source_document_type": doc.doctype, "source_document": doc.name},
		fields=["name", "accepted_qty", "rejected_qty"],
	)

	for lot in lots:
		if flt(lot.accepted_qty) or flt(lot.rejected_qty):
			frappe.throw(
				_(
					"Cannot cancel: Quality Control Lot {0} created by this document has already been "
					"released or rejected. Unwind the Quality Control Release or purchase return first."
				).format(frappe.bold(lot.name)),
				title=_("Quality Control Lot In Use"),
			)
		frappe.delete_doc("Quality Control Lot", lot.name, ignore_permissions=True)


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
