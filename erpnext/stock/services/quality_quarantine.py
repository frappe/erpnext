# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""Quarantine actions: mint Quality Control Lots when stock lands in a Quality Control warehouse.

This is deliberately route-agnostic — it reacts to a positive movement into a
Quality warehouse rather than re-resolving the trigger, so it works no matter how
the stock got there (receipt, transfer, redirect).
"""

import frappe
from frappe import _
from frappe.utils import flt, get_link_to_form

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
				).format(
					point.row.idx,
					get_link_to_form("Item", point.item_code),
					get_link_to_form("Warehouse", point.warehouse),
				),
				title=_("Quality Control Warehouse Missing"),
			)

		point.row.set(target_fieldname, quality_warehouse)
		_redirect_draft_bundle(point.row, quality_warehouse)
		frappe.msgprint(
			_("Row #{0}: Item {1} is routed to {2} for quality inspection.").format(
				point.row.idx,
				get_link_to_form("Item", point.item_code),
				get_link_to_form("Warehouse", quality_warehouse),
			),
			alert=True,
		)


def _redirect_draft_bundle(row, quality_warehouse):
	"""A draft Serial and Batch Bundle built before routing still points at the
	original warehouse — carry it along, or its validation rightly refuses."""
	bundle = row.get("serial_and_batch_bundle")
	if not bundle:
		return

	info = frappe.db.get_value("Serial and Batch Bundle", bundle, ["docstatus", "warehouse"], as_dict=True)
	if not info or info.docstatus != 0 or info.warehouse == quality_warehouse:
		return

	frappe.db.set_value(
		"Serial and Batch Bundle", bundle, "warehouse", quality_warehouse, update_modified=False
	)
	entry = frappe.qb.DocType("Serial and Batch Entry")
	frappe.qb.update(entry).set(entry.warehouse, quality_warehouse).where(entry.parent == bundle).run()


def validate_quality_warehouse_usage(doc):
	"""A Quality Control warehouse only receives stock that requires quarantine.

	Allowed inbound movements: those whose trigger resolves to Quarantine (the
	routed flow, or a direct receipt of a quarantine-triggered item) and items
	under a Periodic Re-test trigger (the scheduler's transfer). Anything else —
	parking ordinary stock in quarantine — is refused: it would sit locked behind
	the exit guard with no inspection path to release it.
	"""
	points = {(id(point.row), point.role): point for point in resolve_inspection_points(doc)}
	retest_items = {}

	for row, role, warehouse in movements_of(doc):
		if role != INBOUND or not is_quality_warehouse(warehouse):
			continue

		point = points.get((id(row), INBOUND))
		if point and point.quality_control_mode == "Quarantine":
			continue

		item_code = row.get("item_code")
		if item_code not in retest_items:
			from erpnext.stock.services.quality_retest import get_retest_trigger

			retest_items[item_code] = bool(get_retest_trigger(item_code))
		if retest_items[item_code]:
			continue

		frappe.throw(
			_(
				"Row #{0}: {1} is a Quality Control warehouse — it only receives stock that "
				"requires quarantine. Item {2} has no Quarantine trigger for this movement; "
				"receive it into a normal warehouse instead."
			).format(row.idx, get_link_to_form("Warehouse", warehouse), get_link_to_form("Item", item_code)),
			title=_("Quality Control Warehouse"),
		)


def stamp_tracking_on_outward_row(
	row, *, item_code, warehouse, qty, company, batch_no=None, serial_nos=None, voucher_type="Stock Entry"
):
	"""Stamp batch / serial identity on a generated outward row, honouring Stock Settings.

	With use_serial_batch_fields enabled the legacy fields carry the (single)
	batch or the serial list; otherwise a Serial and Batch Bundle is created for
	the outward leg. Serial-tracked rows without an explicit list auto-pick.
	"""
	from frappe.utils import cint

	if not batch_no and not serial_nos:
		has_serial_no = frappe.get_cached_value("Item", item_code, "has_serial_no")
		if not has_serial_no:
			return row

	if cint(frappe.db.get_single_value("Stock Settings", "use_serial_batch_fields")):
		row["use_serial_batch_fields"] = 1
		if batch_no:
			row["batch_no"] = batch_no
		if serial_nos:
			row["serial_no"] = "\n".join(serial_nos)
		return row

	from erpnext.stock.serial_batch_bundle import SerialBatchCreation

	args = {
		"item_code": item_code,
		"warehouse": warehouse,
		"actual_qty": -flt(qty),
		"qty": -flt(qty),
		"type_of_transaction": "Outward",
		"voucher_type": voucher_type,
		"company": company,
		"do_not_submit": True,
	}
	if serial_nos:
		args["serial_nos"] = serial_nos
	if batch_no:
		args["batches"] = frappe._dict({batch_no: qty})

	bundle = SerialBatchCreation(args).make_serial_and_batch_bundle()
	if bundle.get("name"):
		row["serial_and_batch_bundle"] = bundle.name
	return row


def sync_source_document_quality_status(source_doctype, source_name):
	"""Aggregate a document's lot statuses onto its Quality Status field."""
	if not source_doctype or not source_name:
		return
	if not frappe.get_meta(source_doctype).has_field("quality_status"):
		return

	statuses = set(
		frappe.get_all(
			"Quality Control Lot",
			filters={"source_document_type": source_doctype, "source_document": source_name},
			pluck="status",
		)
	)

	if "Under Inspection" in statuses:
		value = "Under Inspection"
	elif "Awaiting Release" in statuses:
		value = "Awaiting Release"
	elif "Partially Released" in statuses:
		value = "Partially Released"
	elif statuses == {"Released"}:
		value = "Released"
	elif statuses == {"Rejected"}:
		value = "Rejected"
	elif statuses:
		value = "Inspection Completed"
	else:
		value = None

	frappe.db.set_value(source_doctype, source_name, "quality_status", value, update_modified=False)


def _lots_minted_by(doc):
	return frappe.get_all(
		"Quality Control Lot",
		filters={"source_document_type": doc.doctype, "source_document": doc.name},
		fields=["name", "accepted_qty", "rejected_qty"],
	)


def block_cancel_when_lot_decided(doc, method=None):
	"""A lot that already released or rejected quantity blocks the cancellation —
	that stock has left quarantine, so reversing the deposit would go negative.
	Runs before_cancel: the guard must speak before the stock ledger reversal
	throws its raw negative-stock error.
	"""
	for lot in _lots_minted_by(doc):
		if flt(lot.accepted_qty) or flt(lot.rejected_qty):
			frappe.throw(
				_(
					"Cannot cancel: Quality Control Lot {0} created by this document has already been "
					"released or rejected. Unwind the Quality Control Release or purchase return first."
				).format(get_link_to_form("Quality Control Lot", lot.name)),
				title=_("Quality Control Lot In Use"),
			)


def handle_source_document_cancel(doc, method=None):
	"""Cascade a source-document cancellation onto its Quality Control Lots.

	An untouched lot (nothing released or rejected yet) is deleted along with the
	reversed stock; block_cancel_when_lot_decided already refused everything else.
	"""
	for lot in _lots_minted_by(doc):
		_unlink_cancelled_lot_references(lot.name)
		frappe.delete_doc("Quality Control Lot", lot.name, ignore_permissions=True)


def _unlink_cancelled_lot_references(lot_name):
	"""Shed links to the lot held by cancelled documents so it can be deleted.

	A fully unwound lot may still be referenced by its cancelled Quality Control
	Releases and inspections — their bookings are already reversed, but frappe
	refuses to delete a referenced document. Draft references are left alone and
	block the deletion, exactly like any other dangling draft.
	"""
	releases = frappe.get_all(
		"Stock Entry", filters={"quality_control_lot": lot_name, "docstatus": 2}, pluck="name"
	)
	for release in releases:
		frappe.db.set_value("Stock Entry", release, "quality_control_lot", None, update_modified=False)

	inspections = frappe.get_all(
		"Quality Inspection",
		filters={"reference_type": "Quality Control Lot", "reference_name": lot_name, "docstatus": 2},
		pluck="name",
	)
	for inspection in inspections:
		frappe.db.set_value(
			"Quality Inspection",
			inspection,
			{"reference_type": None, "reference_name": None},
			update_modified=False,
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
				).format(row.idx, get_link_to_form("Warehouse", row.warehouse)),
				title=_("Quality Control Warehouse"),
			)


def create_quality_control_lots(doc, method=None):
	"""Mint a Quality Control Lot for each item moving into a Quality warehouse on this document."""
	from erpnext.stock.services.quality_retest import get_retest_trigger

	points_by_row = {id(point.row): point for point in resolve_inspection_points(doc)}

	for row, role, warehouse in movements_of(doc):
		if role != INBOUND or not is_quality_warehouse(warehouse):
			continue

		# a customer return carries negative quantities; the lot records the
		# absolute quantity that physically entered the Quality Control warehouse
		received_qty = abs(flt(row.get("transfer_qty") or row.get("stock_qty") or row.get("qty")))
		if not received_qty:
			continue

		# one lot per batch: a row carrying several batches in its bundle splits,
		# so every lot keeps the batch guarantees (release, return, re-test)
		batch_no = row.get("batch_no")
		bundle = row.get("serial_and_batch_bundle")
		if not batch_no and not bundle:
			# tracking auto-created during submission (series-named serials,
			# batches and their bundle) is stamped on the database row only;
			# the in-memory child row stays bare
			db_tracking = (
				frappe.db.get_value(
					row.doctype, row.name, ["batch_no", "serial_and_batch_bundle"], as_dict=True
				)
				or frappe._dict()
			)
			batch_no = db_tracking.batch_no
			bundle = db_tracking.serial_and_batch_bundle

		batch_qty_map = {}
		if batch_no:
			batch_qty_map[batch_no] = received_qty
		elif bundle:
			for entry in frappe.get_all(
				"Serial and Batch Entry",
				filters={"parent": bundle, "batch_no": ("is", "set")},
				fields=["batch_no", "qty"],
			):
				batch_qty_map[entry.batch_no] = batch_qty_map.get(entry.batch_no, 0) + abs(flt(entry.qty))
		if not batch_qty_map:
			batch_qty_map = {None: received_qty}

		# carry the inspection template/basis from the trigger that caused the
		# quarantine; periodic re-test transfers fall back to the re-test trigger
		point = points_by_row.get(id(row))
		template = point.inspection_template if point else None
		basis = point.inspection_basis if point else None
		if not template:
			retest_trigger = get_retest_trigger(row.get("item_code"))
			if retest_trigger:
				template = retest_trigger.inspection_template
				basis = retest_trigger.inspection_basis

		for batch_no, batch_qty in batch_qty_map.items():
			lot = frappe.get_doc(
				{
					"doctype": "Quality Control Lot",
					"item_code": row.get("item_code"),
					"company": doc.get("company"),
					"quality_warehouse": warehouse,
					"batch_no": batch_no,
					"received_qty": batch_qty,
					"source_document_type": doc.doctype,
					"source_document": doc.name,
					"inspection_template": template,
				}
			)
			if basis:
				lot.inspection_basis = basis
			lot.insert(ignore_permissions=True)


def remind_pending_quality_inspections():
	"""Daily: nudge Quality Managers about lots awaiting inspection too long.

	Quarantined stock that nobody decides is working capital standing still;
	the threshold lives in Stock Settings and zero disables the reminder.
	"""
	from frappe.utils import add_days, cint, today

	days = cint(frappe.db.get_single_value("Stock Settings", "pending_quality_inspection_reminder_days"))
	if days < 1:
		return

	lots = frappe.get_all(
		"Quality Control Lot",
		filters={"creation": ("<", add_days(today(), -days))},
		fields=["name", "item_code", "received_qty", "decided_qty"],
		order_by="creation",
	)
	pending = [lot for lot in lots if flt(lot.received_qty) > flt(lot.decided_qty)]
	if not pending:
		return

	quality_managers = frappe.get_all(
		"Has Role",
		filters={"role": "Quality Manager", "parenttype": "User"},
		pluck="parent",
	)
	enabled = set(frappe.get_all("User", filters={"enabled": 1}, pluck="name"))

	subject = _("{0} Quality Control Lot(s) have been awaiting inspection for over {1} day(s)").format(
		len(pending), days
	)
	details = "<br>".join(
		_("{0}: {1} ({2} of {3} undecided)").format(
			get_link_to_form("Quality Control Lot", lot.name),
			lot.item_code,
			flt(lot.received_qty) - flt(lot.decided_qty),
			lot.received_qty,
		)
		for lot in pending[:20]
	)

	for user in quality_managers:
		if user not in enabled:
			continue
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": user,
				"type": "Alert",
				"document_type": "Quality Control Lot",
				"document_name": pending[0].name,
				"subject": subject,
				"email_content": details,
			}
		).insert(ignore_permissions=True)
