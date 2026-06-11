# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""Releases out of quarantine: the verdict's consequences on the Quality Control Lot.

A submitted Quality Inspection books its accepted/rejected increment on the lot
and auto-releases accepted stock when a unique store exists; manual releases and
rejected-stock dispositions are built from the lot. Serial guards union across
every verdict of the lot — never a rejected or undecided serial leaves.
"""

import frappe
from frappe import _
from frappe.utils import flt, get_link_to_form

from erpnext.stock.services.quality_quarantine import stamp_tracking_on_outward_row


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

	The verdict books its increment on the lot — per-unit counts for an Each
	Quantity inspection, the decided quantity otherwise — and the accepted part
	auto-releases when a unique store points at the Quality Control warehouse.
	"""
	if doc.reference_type != "Quality Control Lot" or not doc.reference_name:
		return

	lot = frappe.get_doc("Quality Control Lot", doc.reference_name)
	undecided_qty = lot.undecided_qty()
	if undecided_qty <= 0:
		return

	if lot.batch_no:
		from erpnext.stock.services.quality_retest import schedule_next_retest

		schedule_next_retest(lot.item_code, lot.batch_no)

	# the inspection's basis governs (the lot's is the fetched proposal, which
	# the inspector may override); inspections may decide the lot in parts, so
	# every increment is bounded by what no earlier verdict has decided
	if doc.get("inspection_basis") == "Each Quantity" and not doc.get("manual_inspection"):
		accepted_qty = min(flt(doc.accepted_unit_quantity), undecided_qty)
		rejected_qty = min(flt(doc.rejected_unit_quantity), undecided_qty - accepted_qty)
	else:
		decided_qty = min(flt(doc.decided_quantity) or undecided_qty, undecided_qty)
		if doc.status == "Rejected":
			accepted_qty, rejected_qty = 0.0, decided_qty
		else:
			accepted_qty, rejected_qty = decided_qty, 0.0

	lot.decided_qty = flt(lot.decided_qty) + accepted_qty + rejected_qty
	if rejected_qty:
		lot.rejected_qty = flt(lot.rejected_qty) + rejected_qty
	# save unconditionally: the deciding inspection is on record now, so the
	# status recomputes even when nothing books yet (Awaiting Release when the
	# release cannot run automatically)
	lot.flags.ignore_permissions = True
	lot.save()

	if not accepted_qty:
		return

	release_warehouse = get_release_warehouse(lot.quality_warehouse)
	if not release_warehouse:
		frappe.msgprint(
			_(
				"Quality Control Lot {0} is accepted, but no unique release warehouse points at {1}. "
				"Create the Quality Control Release manually."
			).format(
				get_link_to_form("Quality Control Lot", lot.name),
				get_link_to_form("Warehouse", lot.quality_warehouse),
			),
			alert=True,
		)
		return

	accepted_serials = None
	if doc.get("unit_readings"):
		accepted_serials = doc.get_unit_serials("Accepted") or None
	elif _union_unit_serials(lot, "Rejected") | _union_unit_serials(lot, "Accepted"):
		# a verdict-less remainder after per-unit tranches: release exactly the
		# serials no verdict rejected and no other verdict claimed
		accepted_serials = _accepted_serials_awaiting_release(lot)

	release = frappe.new_doc("Stock Entry")
	release.purpose = "Quality Control Release"
	release.stock_entry_type = "Quality Control Release"
	release.company = lot.company
	release.quality_control_lot = lot.name
	release_row = {
		"item_code": lot.item_code,
		"qty": accepted_qty,
		"s_warehouse": lot.quality_warehouse,
		"t_warehouse": release_warehouse,
	}
	stamp_tracking_on_outward_row(
		release_row,
		item_code=lot.item_code,
		warehouse=lot.quality_warehouse,
		qty=accepted_qty,
		company=lot.company,
		batch_no=lot.batch_no,
		serial_nos=accepted_serials,
	)
	release.append("items", release_row)
	release.flags.ignore_permissions = True
	release.insert()
	release.submit()

	frappe.msgprint(
		_("Quality Control Release {0} created: {1} released to {2}.").format(
			frappe.utils.get_link_to_form("Stock Entry", release.name),
			accepted_qty,
			get_link_to_form("Warehouse", release_warehouse),
		),
		alert=True,
	)


def reverse_inspection_result(doc, method=None):
	"""Cancelling a deciding inspection unwinds its increment on the lot.

	The lot's only verdict: its Quality Control Releases are cancelled (stock
	returns to quarantine) and the booked quantities cleared, so the lot is
	back under inspection in full. One verdict of several: only its decided and
	rejected increments are removed — and the cancellation is refused while
	physical bookings (releases, returns, dispositions) exceed what the
	remaining verdicts support, mirroring every other dependency chain here.
	"""
	if doc.reference_type != "Quality Control Lot" or not doc.reference_name:
		return
	if not frappe.db.exists("Quality Control Lot", doc.reference_name):
		return

	lot = frappe.get_doc("Quality Control Lot", doc.reference_name)
	other_verdicts = frappe.get_all(
		"Quality Inspection",
		filters={
			"reference_type": "Quality Control Lot",
			"reference_name": lot.name,
			"docstatus": 1,
			"name": ("!=", doc.name),
		},
		pluck="name",
	)

	if not other_verdicts:
		if flt(lot.returned_qty) or flt(lot.disposed_qty):
			frappe.throw(
				_(
					"Cannot cancel: a purchase return or disposition is already booked against "
					"Quality Control Lot {0}. Unwind it first."
				).format(get_link_to_form("Quality Control Lot", lot.name)),
				title=_("Rejected Stock Already Moved"),
			)

		releases = frappe.get_all(
			"Stock Entry",
			filters={"quality_control_lot": lot.name, "docstatus": 1},
			pluck="name",
		)
		for name in releases:
			release = frappe.get_doc("Stock Entry", name)
			release.flags.ignore_permissions = True
			release.cancel()

		lot.reload()
		lot.decided_qty = 0
		lot.rejected_qty = 0
		lot.flags.ignore_permissions = True
		lot.save()
		return

	# one verdict of several: remove its increment, keep the rest standing
	if doc.get("inspection_basis") == "Each Quantity" and not doc.get("manual_inspection"):
		accepted_qty = flt(doc.accepted_unit_quantity)
		rejected_qty = flt(doc.rejected_unit_quantity)
	elif doc.status == "Rejected":
		accepted_qty, rejected_qty = 0.0, flt(doc.decided_quantity)
	else:
		accepted_qty, rejected_qty = flt(doc.decided_quantity), 0.0

	remaining_decided = flt(lot.decided_qty) - accepted_qty - rejected_qty
	remaining_rejected = flt(lot.rejected_qty) - rejected_qty

	if remaining_rejected < flt(lot.returned_qty) + flt(lot.disposed_qty):
		frappe.throw(
			_(
				"Cannot cancel: returns or dispositions already moved more rejected stock of "
				"Quality Control Lot {0} than the remaining verdicts cover. Unwind them first."
			).format(get_link_to_form("Quality Control Lot", lot.name)),
			title=_("Rejected Stock Already Moved"),
		)
	if remaining_decided - remaining_rejected < flt(lot.accepted_qty):
		frappe.throw(
			_(
				"Cannot cancel: releases already moved more accepted stock of Quality Control "
				"Lot {0} than the remaining verdicts cover. Unwind the releases first."
			).format(get_link_to_form("Quality Control Lot", lot.name)),
			title=_("Accepted Stock Already Released"),
		)

	lot.decided_qty = remaining_decided
	lot.rejected_qty = remaining_rejected
	lot.flags.ignore_permissions = True
	lot.save()


@frappe.whitelist()
def make_release_for_lot(lot_name: str, release_warehouse: str | None = None):
	"""A Quality Control Release pre-filled with the lot's accepted stock.

	The path for when the automatic release could not run — typically several
	stores share one Quality Control warehouse, so no unique release target
	exists. Pre-filled with the quantity the inspection accepted that is still
	in quarantine, the lot's batch and exactly the accepted serials; the caller
	(or the form) picks the target warehouse.
	"""
	frappe.has_permission("Stock Entry", "create", throw=True)
	lot = frappe.get_doc("Quality Control Lot", lot_name)
	lot.check_permission("read")

	if (
		not lot.quality_inspection
		or frappe.db.get_value("Quality Inspection", lot.quality_inspection, "docstatus") != 1
	):
		frappe.throw(
			_(
				"Quality Control Lot {0} has no submitted Quality Inspection. Stock cannot leave "
				"quarantine without a recorded inspection decision."
			).format(get_link_to_form("Quality Control Lot", lot.name)),
			title=_("Inspection Pending"),
		)

	accepted_qty = lot.awaiting_release_qty()
	if accepted_qty <= 0:
		frappe.throw(
			_("Quality Control Lot {0} has no accepted quantity awaiting release.").format(
				get_link_to_form("Quality Control Lot", lot.name)
			)
		)

	accepted_serials = _accepted_serials_awaiting_release(lot)
	if accepted_serials:
		accepted_serials = accepted_serials[: int(accepted_qty)]

	stock_uom = frappe.get_cached_value("Item", lot.item_code, "stock_uom")
	entry = frappe.new_doc("Stock Entry")
	entry.purpose = "Quality Control Release"
	entry.stock_entry_type = "Quality Control Release"
	entry.company = lot.company
	entry.quality_control_lot = lot.name
	row = {
		"item_code": lot.item_code,
		"qty": accepted_qty,
		"uom": stock_uom,
		"stock_uom": stock_uom,
		"conversion_factor": 1,
		"s_warehouse": lot.quality_warehouse,
		"t_warehouse": release_warehouse or get_release_warehouse(lot.quality_warehouse),
	}
	stamp_tracking_on_outward_row(
		row,
		item_code=lot.item_code,
		warehouse=lot.quality_warehouse,
		qty=accepted_qty,
		company=lot.company,
		batch_no=lot.batch_no,
		serial_nos=accepted_serials,
	)
	entry.append("items", row)
	return entry


@frappe.whitelist()
def make_rejected_stock_transfer_for_lot(lot_name: str):
	"""A Quality Control Release moving the lot's rejected stock to a Rejected warehouse.

	The other disposition for rejected stock besides a purchase return: out of
	quarantine into a Rejected warehouse, where normal stock rules take over
	(scrap with a Material Issue, rework, sale as scrap). Pre-filled with the
	rejected quantity still in quarantine, the lot's batch and exactly the
	rejected serials; the target is resolved when the company has a single
	Rejected warehouse, otherwise the user picks it.
	"""
	frappe.has_permission("Stock Entry", "create", throw=True)
	lot = frappe.get_doc("Quality Control Lot", lot_name)
	lot.check_permission("read")

	outstanding = flt(lot.rejected_qty) - flt(lot.returned_qty) - flt(lot.disposed_qty)
	if outstanding <= 0:
		frappe.throw(
			_("Quality Control Lot {0} has no rejected quantity in quarantine.").format(
				get_link_to_form("Quality Control Lot", lot.name)
			)
		)

	rejected_warehouses = frappe.get_all(
		"Warehouse",
		filters={
			"warehouse_type": "Rejected",
			"company": lot.company,
			"is_group": 0,
			"disabled": 0,
		},
		pluck="name",
	)
	if not rejected_warehouses:
		frappe.throw(
			_(
				"No Rejected warehouse exists for {0}. Create a warehouse with type Rejected to "
				"move rejected stock out of quarantine."
			).format(get_link_to_form("Company", lot.company)),
			title=_("Rejected Warehouse Missing"),
		)

	entry = frappe.new_doc("Stock Entry")
	entry.purpose = "Quality Control Release"
	entry.stock_entry_type = "Quality Control Release"
	entry.company = lot.company
	entry.quality_control_lot = lot.name
	stock_uom = frappe.get_cached_value("Item", lot.item_code, "stock_uom")
	row = {
		"item_code": lot.item_code,
		"qty": outstanding,
		"uom": stock_uom,
		"stock_uom": stock_uom,
		"conversion_factor": 1,
		"s_warehouse": lot.quality_warehouse,
		"t_warehouse": rejected_warehouses[0] if len(rejected_warehouses) == 1 else None,
	}
	stamp_tracking_on_outward_row(
		row,
		item_code=lot.item_code,
		warehouse=lot.quality_warehouse,
		qty=outstanding,
		company=lot.company,
		batch_no=lot.batch_no,
		serial_nos=_rejected_serials_awaiting_return(lot, outstanding),
	)
	entry.append("items", row)
	return entry


def _submitted_inspections_of(lot):
	return frappe.get_all(
		"Quality Inspection",
		filters={
			"reference_type": "Quality Control Lot",
			"reference_name": lot.name,
			"docstatus": 1,
		},
		pluck="name",
	)


def _union_unit_serials(lot, status):
	"""The serials every submitted verdict of the lot gave this status."""
	serials = set()
	for name in _submitted_inspections_of(lot):
		inspection = frappe.get_doc("Quality Inspection", name)
		if inspection.get("unit_readings"):
			serials.update(inspection.get_unit_serials(status))
	return serials


def _accepted_serials_awaiting_release(lot):
	"""The serials a release may move: accepted by a verdict, or — once the lot
	is fully decided — claimed by no per-unit verdict at all (a verdict-less
	remainder), and still in the Quality Control warehouse. Never a rejected or
	undecided serial."""
	allowed = _union_unit_serials(lot, "Accepted")
	if lot.undecided_qty() <= 0:
		# fully decided: serials no per-unit verdict claimed belong to a
		# verdict-less remainder verdict (partial verdicts of serialized items
		# must name their units, so nothing here is undecided)
		from erpnext.stock.doctype.quality_control_lot.quality_control_lot import get_serial_numbers

		claimed = allowed | _union_unit_serials(lot, "Rejected")
		allowed = allowed | {
			row["serial_no"] for row in get_serial_numbers(lot.name) if row["serial_no"] not in claimed
		}

	return (
		sorted(
			serial
			for serial in allowed
			if frappe.db.get_value("Serial No", serial, "warehouse") == lot.quality_warehouse
		)
		or None
	)


def _rejected_serials_awaiting_return(lot, outstanding):
	"""The rejected units' serials that are still in the Quality Control warehouse."""
	rejected = sorted(_union_unit_serials(lot, "Rejected"))
	if not rejected:
		return None
	still_held = [
		serial
		for serial in rejected
		if frappe.db.get_value("Serial No", serial, "warehouse") == lot.quality_warehouse
	]
	return still_held[: int(outstanding)] or None
