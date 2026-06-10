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


def resolve_job_card_inspection(job_card, production_item=None):
	"""Return the matching Job Card trigger for a job card's output, or None.

	Job Card triggers only apply when the Work Order tracks semi-finished goods —
	that is the only mode where each job card produces an identifiable output.
	"Final Output Only" rows match just the job card whose finished good is the
	work order's production item; "Every Job Card" rows match them all.
	"""
	if not job_card.get("track_semi_finished_goods") or not job_card.get("finished_good"):
		return None

	if production_item is None and job_card.get("work_order"):
		production_item = frappe.db.get_value("Work Order", job_card.work_order, "production_item")
	is_final_output = job_card.finished_good == production_item

	for trigger in _ordered_triggers(job_card.finished_good):
		if trigger.document_type != "Job Card":
			continue
		if trigger.applicable_warehouse and trigger.applicable_warehouse != job_card.get("target_warehouse"):
			continue
		if trigger.job_card_inspection_point == "Final Output Only" and not is_final_output:
			continue
		if trigger.condition:
			try:
				if not frappe.safe_eval(trigger.condition, None, {"doc": job_card}):
					continue
			except Exception:
				continue
		return trigger

	return None


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
			msg = _("Row #{0}: Quality Inspection is required for Item {1}.").format(
				row.idx, frappe.bold(row.get("item_code"))
			)
			if block and submitting:
				frappe.throw(msg, title=_("Inspection Required"))
			else:
				frappe.msgprint(
					msg, title=_("Inspection Required"), indicator="orange" if submitting else "blue"
				)
			continue

		if not submitting:
			continue

		info = frappe.db.get_value("Quality Inspection", qi, ["docstatus", "status"], as_dict=True)
		link = get_link_to_form("Quality Inspection", qi)
		if not info or info.docstatus != 1:
			msg = _("Row #{0}: Quality Inspection {1} is not submitted.").format(row.idx, link)
		elif info.status == "Rejected":
			msg = _("Row #{0}: Quality Inspection {1} was rejected.").format(row.idx, link)
		else:
			continue

		if block:
			frappe.throw(msg, title=_("Quality Inspection"))
		else:
			frappe.msgprint(msg, title=_("Quality Inspection"), indicator="orange", alert=True)
