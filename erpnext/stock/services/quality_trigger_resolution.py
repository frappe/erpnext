# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""Resolve which quality inspections a stock transaction requires.

Each item row of a stock voucher is decomposed into directional movements
(inbound into a target warehouse, outbound out of a source warehouse). Each
movement is matched against the Item / Item Group quality triggers, most-specific
first, to produce the set of required inspection points.

This module only *resolves* points; enforcing them (block / warn / quarantine)
is wired separately.
"""

import frappe
from frappe import _
from frappe.utils import flt, get_link_to_form
from frappe.utils.nestedset import get_ancestors_of

from erpnext.stock.services.quality_warehouse import is_transit_warehouse

INBOUND = "Inbound"
OUTBOUND = "Outbound"


def _reverse(role):
	return INBOUND if role == OUTBOUND else OUTBOUND


def movements_of(doc):
	"""Yield (row, role, warehouse) for each directional stock movement on a doc.

	Sales/Purchase Invoices only move stock when update_stock is set. A return
	reverses the stock direction: a sales (Delivery Note / Sales Invoice) return
	brings stock back in, a purchase return sends it back out.
	"""
	doctype = doc.doctype
	inbound_natural = doctype in ("Purchase Receipt", "Subcontracting Receipt", "Purchase Invoice")
	role = INBOUND if inbound_natural else OUTBOUND
	if doc.get("is_return"):
		role = _reverse(role)

	if doctype == "Goods Inward Note":
		# custody, not stock: the goods are inbound but sit in no warehouse yet
		for row in doc.get("items") or []:
			yield row, INBOUND, None
		return

	if doctype in ("Purchase Receipt", "Subcontracting Receipt"):
		for row in doc.get("items") or []:
			if row.get("warehouse"):
				yield row, role, row.warehouse

	elif doctype == "Purchase Invoice":
		if doc.get("update_stock"):
			for row in doc.get("items") or []:
				if row.get("warehouse"):
					yield row, role, row.warehouse

	elif doctype == "Delivery Note":
		for row in doc.get("items") or []:
			if row.get("warehouse"):
				yield row, role, row.warehouse

	elif doctype == "Sales Invoice":
		if doc.get("update_stock"):
			for row in doc.get("items") or []:
				if row.get("warehouse"):
					yield row, role, row.warehouse

	elif doctype == "Stock Entry":
		# In-transit transfers move stock through a dummy Transit warehouse, which
		# is not a real inspection point: skip the first entry's move into transit
		# and the end entry's move out of transit. The real source-out and
		# target-in legs still apply.
		for row in doc.get("items") or []:
			t_warehouse = row.get("t_warehouse")
			if t_warehouse and not is_transit_warehouse(t_warehouse):
				yield row, INBOUND, t_warehouse
			s_warehouse = row.get("s_warehouse")
			if s_warehouse and not is_transit_warehouse(s_warehouse):
				yield row, OUTBOUND, s_warehouse


def _ordered_triggers(item_code):
	"""Triggers that apply to an item, most-specific first.

	Item-level rows win over Item Group rows; nearer Item Group ancestors win over
	farther ones (root last).
	"""
	rows = frappe.get_all(
		"Item Quality Trigger",
		filters={"parenttype": "Item", "parent": item_code},
		fields=["*"],
		order_by="idx",
	)

	item_group = frappe.get_cached_value("Item", item_code, "item_group")
	if item_group:
		# nearest ancestor first (lft desc), root last
		for group in [item_group, *get_ancestors_of("Item Group", item_group)]:
			rows += frappe.get_all(
				"Item Quality Trigger",
				filters={"parenttype": "Item Group", "parent": group},
				fields=["*"],
				order_by="idx",
			)
	return rows


def item_has_trigger_for_doctype(item_code, document_type):
	"""Whether an item (or its Item Group ancestors) has any trigger for a doctype.

	Used to offer the "Make Quality Inspection" button. Looser than full
	resolution (it ignores warehouse / role / party specifics) on purpose — the
	precise gate is applied at submission.
	"""
	return any(trigger.document_type == document_type for trigger in _ordered_triggers(item_code))


def get_trigger_for_doctype(item_code, document_type):
	"""The item's most specific trigger for a document type, or None.

	Looser than full resolution (warehouse / party specifics ignored), used for
	form defaults; the precise gate is applied at submission.
	"""
	for trigger in _ordered_triggers(item_code):
		if trigger.document_type == document_type:
			return trigger
	return None


def get_inspection_basis(item_code, document_type):
	"""The inspection basis (Sample / Each Quantity) of the item's most specific
	trigger for a document type. Items without a trigger inspect on a sample."""
	trigger = get_trigger_for_doctype(item_code, document_type)
	return (trigger.inspection_basis if trigger else None) or "Sample"


def get_sample_size(trigger, qty):
	"""The sample to inspect for a quantity, per the trigger's configuration.

	A percentage is taken of the quantity and rounded up — a sample is at least
	one unit — and a fixed size is capped at the quantity on hand.
	"""
	import math

	from frappe.utils import flt

	if not trigger or not flt(trigger.sample_size):
		return None

	qty = flt(qty)
	if trigger.sample_size_is_percentage:
		return min(qty, math.ceil(qty * flt(trigger.sample_size) / 100)) if qty else None

	return min(qty, flt(trigger.sample_size)) if qty else flt(trigger.sample_size)


def _is_internal_transfer(doc):
	return bool(doc.get("is_internal_supplier") or doc.get("is_internal_customer"))


def _trigger_matches(trigger, doc, row, role, warehouse):
	if trigger.document_type != doc.doctype:
		return False
	if trigger.warehouse_role and trigger.warehouse_role != role:
		return False
	if trigger.applicable_warehouse and trigger.applicable_warehouse != warehouse:
		return False

	# Stock Entry Type filter (blank = any type)
	if doc.doctype == "Stock Entry" and trigger.stock_entry_type:
		if trigger.stock_entry_type != doc.get("stock_entry_type"):
			return False

	# party filters (blank = any supplier / customer)
	if trigger.supplier and doc.get("supplier") != trigger.supplier:
		return False
	if trigger.customer and doc.get("customer") != trigger.customer:
		return False

	# External / Internal Transfer filter (blank = both)
	if trigger.party_transaction_type:
		internal = _is_internal_transfer(doc)
		if trigger.party_transaction_type == "Internal Transfer" and not internal:
			return False
		if trigger.party_transaction_type == "External" and internal:
			return False

	# optional Python condition against the row / doc
	if trigger.condition:
		try:
			if not frappe.safe_eval(trigger.condition, None, {"doc": doc, "row": row}):
				return False
		except Exception:
			return False

	return True


def _decided_in_custody(doc, row):
	"""Whether a custody inspection already decided this receiving row's goods."""
	if doc.doctype not in ("Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"):
		return False
	if not row.get("goods_inward_note"):
		return False

	from erpnext.stock.doctype.goods_inward_note.goods_inward_note import ORDER_REFERENCE_FIELDS

	order_item_field = ORDER_REFERENCE_FIELDS[doc.doctype][1]
	note_rows = frappe.get_all(
		"Goods Inward Note Item",
		filters={"parent": row.goods_inward_note, "order_item": row.get(order_item_field)},
		pluck="name",
	)
	if not note_rows:
		return False

	# partial verdicts are safe to exempt: the receipt is capped to decided units
	return bool(
		frappe.db.exists(
			"Quality Inspection",
			{
				"reference_type": "Goods Inward Note",
				"child_row_reference": ("in", note_rows),
				"docstatus": 1,
			},
		)
	)


def resolve_inspection_points(doc):
	"""Return the inspection points a transaction requires.

	One point per matching movement, using the most-specific trigger. Movements
	with no matching trigger produce nothing.
	"""
	points = []
	triggers_by_item = {}

	for row, role, warehouse in movements_of(doc):
		item_code = row.get("item_code")
		if not item_code:
			continue

		# goods decided by a custody inspection are not re-inspected on receipt
		if role == INBOUND and _decided_in_custody(doc, row):
			continue

		if item_code not in triggers_by_item:
			triggers_by_item[item_code] = _ordered_triggers(item_code)

		for trigger in triggers_by_item[item_code]:
			if _trigger_matches(trigger, doc, row, role, warehouse):
				points.append(
					frappe._dict(
						item_code=item_code,
						qty=row.get("stock_qty") or row.get("qty"),
						role=role,
						warehouse=warehouse,
						row=row,
						trigger=trigger,
						inspection_template=trigger.inspection_template,
						quality_control_mode=trigger.quality_control_mode,
						inspection_basis=trigger.inspection_basis,
					)
				)
				break  # most-specific wins

	return points


def get_reference_row_tracking(child_doctype, row_name):
	"""The tracking values of a referenced child row, tolerant of doctypes
	without tracking columns (a Goods Inward Note row has none)."""
	meta = frappe.get_meta(child_doctype)
	fields = [
		field for field in ("serial_no", "batch_no", "serial_and_batch_bundle") if meta.has_field(field)
	]
	if not fields:
		return frappe._dict()
	return frappe.db.get_value(child_doctype, row_name, fields, as_dict=True) or frappe._dict()


def get_row_serial_nos(row):
	"""The serial numbers a transaction row carries (legacy field or bundle)."""
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

	serials = set()
	if row.get("serial_no"):
		serials.update(get_serial_nos(row.get("serial_no")))
	if row.get("serial_and_batch_bundle"):
		serials.update(
			frappe.get_all(
				"Serial and Batch Entry",
				filters={"parent": row.get("serial_and_batch_bundle"), "serial_no": ("is", "set")},
				pluck="serial_no",
			)
		)
	return serials


def get_row_batch_nos(row):
	"""The batch numbers a transaction row carries (legacy field or bundle)."""
	batches = set()
	if row.get("batch_no"):
		batches.add(row.get("batch_no"))
	if row.get("serial_and_batch_bundle"):
		batches.update(
			frappe.get_all(
				"Serial and Batch Entry",
				filters={"parent": row.get("serial_and_batch_bundle"), "batch_no": ("is", "set")},
				pluck="batch_no",
			)
		)
	return batches


def get_row_batch_qty(row, batch_no):
	"""How much of a batch a transaction row carries, in stock units."""
	if row.get("serial_and_batch_bundle"):
		entries = frappe.get_all(
			"Serial and Batch Entry",
			filters={"parent": row.get("serial_and_batch_bundle"), "batch_no": batch_no},
			pluck="qty",
		)
		if entries:
			return sum(abs(flt(qty)) for qty in entries)
	if row.get("batch_no") == batch_no:
		return abs(flt(row.get("stock_qty") or row.get("transfer_qty") or row.get("qty")))
	return 0


def validate_inspected_serial_consistency(doc, method=None):
	"""Every inspection bound to a row must describe the row's identity.

	An inspection names specific units or a batch; if the row no longer
	carries them (changed after the inspection), the recorded verdict says
	nothing about the stock actually moving and must be cancelled. Enforced at
	submission for every row-bound inspection, regardless of mode — and
	re-checked on submit, when inward documents have materialised their
	auto-created serials and bundles that validate time cannot see.
	"""
	if doc.docstatus != 1:
		return

	child_doctype = "Stock Entry Detail" if doc.doctype == "Stock Entry" else doc.doctype + " Item"

	for row in doc.get("items") or []:
		inspections = _row_inspections(doc, row)
		if not inspections:
			continue

		# inward documents materialise serials/bundles during submission via
		# direct writes — the in-memory row may be stale, the database is not
		db_row = frappe.db.get_value(
			child_doctype, row.name, ["serial_no", "serial_and_batch_bundle", "batch_no"], as_dict=True
		)
		row_serials = get_row_serial_nos(row) or (get_row_serial_nos(db_row) if db_row else set())
		row_batches = get_row_batch_nos(row) or (get_row_batch_nos(db_row) if db_row else set())

		for inspection in inspections:
			link = frappe.utils.get_link_to_form("Quality Inspection", inspection.name)
			sampled = _inspection_serials(inspection)
			if sampled and row_serials:
				missing = sampled - row_serials
				if missing:
					frappe.throw(
						_(
							"Row #{0}: Quality Inspection {1} sampled serial number(s) {2}, which this "
							"row does not carry. Cancel {1} and inspect the stock actually moving."
						).format(row.idx, link, frappe.bold(", ".join(sorted(missing)))),
						title=_("Inspected Serials Mismatch"),
					)

			if inspection.batch_no and row_batches and inspection.batch_no not in row_batches:
				frappe.throw(
					_(
						"Row #{0}: Quality Inspection {1} covers batch {2}, which this row does not "
						"carry. Cancel {1} and inspect the stock actually moving."
					).format(row.idx, link, get_link_to_form("Batch", inspection.batch_no)),
					title=_("Inspected Batch Mismatch"),
				)

			if inspection.batch_no and inspection.batch_no in row_batches:
				batch_qty = get_row_batch_qty(row, inspection.batch_no) or (
					get_row_batch_qty(db_row, inspection.batch_no) if db_row else 0
				)
				if batch_qty and flt(inspection.sample_size) > batch_qty:
					frappe.throw(
						_(
							"Row #{0}: Quality Inspection {1} samples {2} unit(s) of batch {3}, but "
							"this row carries only {4}."
						).format(
							row.idx,
							link,
							flt(inspection.sample_size),
							get_link_to_form("Batch", inspection.batch_no),
							batch_qty,
						),
						title=_("Sample Larger Than Batch"),
					)


@frappe.whitelist()
def get_inspection_outcomes(doc: dict | str):
	"""Propose the accepted/rejected split each row's decided inspection implies.

	For documents that receive stock without quarantine (Block / Warn modes),
	the inspection verdict does not move anything by itself — the row's
	accepted and rejected quantities do. This reads each row's submitted
	inspection and proposes the matching split: rejected count from the
	unit readings (or the whole row on an outright rejection), rejected
	serials into the rejected serial field, and a Rejected warehouse when the
	company has exactly one. Rows whose current split already matches are
	skipped; everything returned stays editable on the form.
	"""
	import json

	from frappe.utils import cint, flt

	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

	if isinstance(doc, str):
		doc = json.loads(doc)
	doc = frappe._dict(doc)

	frappe.has_permission(doc.doctype, "write", throw=True)
	frappe.has_permission("Quality Inspection", "read", throw=True)
	if doc.doctype not in ("Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"):
		return []
	if doc.doctype == "Purchase Invoice" and not cint(doc.update_stock):
		return []

	outcomes = []
	for row in doc.get("items") or []:
		row = frappe._dict(row)
		if not row.quality_inspection:
			continue

		if frappe.db.get_value("Quality Inspection", row.quality_inspection, "docstatus") != 1:
			continue

		info = frappe.get_doc("Quality Inspection", row.quality_inspection)
		received_qty = flt(row.received_qty) or flt(row.qty) + flt(row.rejected_qty)
		rejected_serials = None
		if info.get("unit_readings"):
			rejected_qty = min(flt(info.rejected_unit_quantity), received_qty)
			rejected_serials = info.get_unit_serials("Rejected")
		elif info.status == "Rejected":
			rejected_qty = received_qty
		elif info.status == "Accepted":
			rejected_qty = 0.0
		else:
			# partially accepted without per-unit verdicts: nothing says which units
			continue

		outcome = {"idx": row.idx, "qty": received_qty - rejected_qty, "rejected_qty": rejected_qty}

		row_serials = get_serial_nos(row.serial_no) if row.serial_no else []
		split_serials = list(get_serial_nos(row.rejected_serial_no)) if row.rejected_serial_no else []
		all_serials = row_serials + [serial for serial in split_serials if serial not in row_serials]
		if all_serials:
			if rejected_serials is None:
				rejected_serials = all_serials if rejected_qty else []
			rejected_in_row = [serial for serial in all_serials if serial in set(rejected_serials)]
			accepted_in_row = [serial for serial in all_serials if serial not in set(rejected_serials)]
			# only a clean one-serial-per-unit match redistributes the fields
			if len(rejected_in_row) == int(rejected_qty):
				outcome["serial_no"] = "\n".join(accepted_in_row)
				outcome["rejected_serial_no"] = "\n".join(rejected_in_row)

		if rejected_qty and not row.rejected_warehouse and not doc.rejected_warehouse:
			rejected_warehouses = frappe.get_all(
				"Warehouse",
				filters={
					"warehouse_type": "Rejected",
					"company": doc.company,
					"is_group": 0,
					"disabled": 0,
				},
				pluck="name",
			)
			if len(rejected_warehouses) == 1:
				outcome["rejected_warehouse"] = rejected_warehouses[0]

		unchanged = all(
			outcome[field]
			== ((row.get(field) or "") if isinstance(outcome[field], str) else flt(row.get(field)))
			for field in outcome
			if field != "idx"
		)
		if not unchanged:
			outcomes.append(outcome)

	return outcomes


def enforce_inspection_points(doc):
	"""Enforce Block / Warn inspection points on a stock transaction.

	Quarantine is handled by warehouse routing and does not gate the document
	here. Block stops submission when the row's Quality Inspection is missing,
	unsubmitted or rejected; Warn only flags it.
	"""
	from frappe.utils import get_link_to_form

	submitting = doc.docstatus == 1

	for point in resolve_inspection_points(doc):
		if point.quality_control_mode not in ("Block", "Warn"):
			continue

		block = point.quality_control_mode == "Block"
		row = point.row
		qi = row.get("quality_inspection")

		if not qi:
			if block:
				msg = _("Row #{0}: Quality Inspection is required for Item {1}.").format(
					row.idx, get_link_to_form("Item", row.get("item_code"))
				)
				if submitting:
					frappe.throw(msg, title=_("Inspection Required"))
				else:
					frappe.msgprint(msg, title=_("Inspection Required"), indicator="orange", alert=True)
			else:
				# Warn never demands — it nudges
				frappe.msgprint(
					_("Row #{0}: Quality Inspection not created for Item {1}.").format(
						row.idx, get_link_to_form("Item", row.get("item_code"))
					),
					indicator="orange",
					alert=True,
				)
			continue

		if not submitting:
			continue

		info = frappe.db.get_value("Quality Inspection", qi, ["docstatus", "status"], as_dict=True)
		link = get_link_to_form("Quality Inspection", qi)
		msg = None
		if not info or info.docstatus != 1:
			msg = _("Row #{0}: Quality Inspection {1} is not submitted.").format(row.idx, link)
		elif info.status == "Rejected":
			msg = _("Row #{0}: Quality Inspection {1} was rejected.").format(row.idx, link)

		if msg:
			if block:
				frappe.throw(msg, title=_("Quality Inspection"))
			else:
				frappe.msgprint(msg, title=_("Quality Inspection"), indicator="orange", alert=True)
			continue

		if block:
			_validate_batches_covered(doc, row)


def _validate_batches_covered(doc, row):
	"""Batches known before submission must each carry a verdict.

	A sample vouches for its whole row, so serials need no unit-by-unit
	coverage — but a batch is a quality boundary of its own, and each one
	moving needs a submitted inspection naming it. Auto-created batches are
	born at the document's submission and cannot be pre-inspected — rows
	without one are exempt.
	"""
	from frappe.utils import get_link_to_form

	row_batches = get_row_batch_nos(row)
	if not row_batches:
		return

	covered = {inspection.batch_no for inspection in _row_inspections(doc, row) if inspection.batch_no}
	missing = sorted(row_batches - covered)
	if missing:
		frappe.throw(
			_(
				"Row #{0}: batch(es) {1} carry no verdict — every batch moving must be covered "
				"by a submitted Quality Inspection naming it."
			).format(
				row.idx,
				", ".join(get_link_to_form("Batch", batch) for batch in missing),
			),
			title=_("Batches Not Inspected"),
		)


def _row_inspections(doc, row):
	"""Every submitted inspection bound to this document row."""
	if not row.get("name"):
		return []
	return frappe.get_all(
		"Quality Inspection",
		filters={
			"reference_type": doc.doctype,
			"reference_name": doc.name,
			"child_row_reference": row.name,
			"docstatus": 1,
		},
		fields=["name", "serial_no", "batch_no", "sample_size"],
	)


def _inspection_serials(inspection):
	"""The serials a verdict names — sampled on the document or per unit."""
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

	serials = set(get_serial_nos(inspection.serial_no or ""))
	serials.update(
		frappe.get_all(
			"Quality Inspection Reading Entry",
			filters={
				"parent": inspection.name,
				"parentfield": "unit_readings",
				"serial_no": ("is", "set"),
			},
			pluck="serial_no",
		)
	)
	return serials
