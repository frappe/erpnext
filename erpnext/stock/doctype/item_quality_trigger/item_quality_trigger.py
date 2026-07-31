# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

# Document types that carry a party and can be an external transaction or an
# internal (inter-company) transfer.
PARTY_DOCTYPES = (
	"Purchase Receipt",
	"Purchase Invoice",
	"Goods Inward Note",
	"Delivery Note",
	"Sales Invoice",
)

# Direction matrix: which warehouse role(s) make sense for a given document type
# (and, for Stock Entry, a given purpose). A pure receipt is inbound-only, a pure
# issue is outbound-only, and transfer/manufacture-style movements expose both.
_INBOUND_ONLY = {"Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt", "Goods Inward Note"}
# Delivery Note / Sales Invoice are outbound for normal documents but inbound for
# returns (a customer return brings stock back in), so both roles are valid:
# Outbound inspects the delivery, Inbound inspects the return.
_RETURNABLE_OUTBOUND = {"Delivery Note", "Sales Invoice"}
_BOTH = {"Inbound", "Outbound"}
_STOCK_ENTRY_ROLES = {
	"Material Receipt": {"Inbound"},
	"Material Issue": {"Outbound"},
	"Material Consumption for Manufacture": {"Outbound"},
	"Send to Subcontractor": {"Outbound"},
	# subcontracting inward flow: the customer's material arrives with a
	# receipt or a return of what we delivered; deliveries and raw material
	# going back to the customer only ever leave
	"Receive from Customer": {"Inbound"},
	"Subcontracting Return": {"Inbound"},
	"Subcontracting Delivery": {"Outbound"},
	"Return Raw Material to Customer": {"Outbound"},
	"Material Transfer": set(_BOTH),
	"Material Transfer for Manufacture": set(_BOTH),
	"Manufacture": set(_BOTH),
	"Repack": set(_BOTH),
	"Disassemble": set(_BOTH),
}


def allowed_warehouse_roles(document_type: str, stock_entry_purpose: str | None = None) -> set[str]:
	"""Warehouse roles valid for a document type / Stock Entry purpose."""
	if document_type in _INBOUND_ONLY:
		return {"Inbound"}
	if document_type in _RETURNABLE_OUTBOUND:
		return set(_BOTH)
	if document_type == "Stock Entry":
		if not stock_entry_purpose:
			return set(_BOTH)
		return set(_STOCK_ENTRY_ROLES.get(stock_entry_purpose, _BOTH))
	return set(_BOTH)


class ItemQualityTrigger(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		applicable_warehouse: DF.Link | None
		condition: DF.Code | None
		customer: DF.Link | None
		document_type: DF.Literal[
			"Purchase Receipt",
			"Goods Inward Note",
			"Purchase Invoice",
			"Subcontracting Receipt",
			"Delivery Note",
			"Sales Invoice",
			"Stock Entry",
		]
		inspection_basis: DF.Literal["Sample", "Each Quantity"]
		inspection_template: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		party_transaction_type: DF.Literal["External", "Internal Transfer"]
		quality_control_mode: DF.Literal["Quarantine", "Block", "Warn"]
		retest_interval_days: DF.Int
		sample_size: DF.Float
		sample_size_is_percentage: DF.Check
		stock_entry_type: DF.Link | None
		supplier: DF.Link | None
		trigger_type: DF.Literal["Transaction", "Periodic Re-test"]
		warehouse_role: DF.Literal["Inbound", "Outbound"]
	# end: auto-generated types

	pass


def validate_item_quality_triggers(doc, method=None):
	"""Validate the quality_triggers child rows on Item / Item Group.

	Called from the Item and Item Group controllers because a child doctype's
	own validate() is not invoked automatically by the framework.
	"""
	rows = doc.get("quality_triggers") or []
	for row in rows:
		_validate_trigger_row(row)
		if doc.doctype == "Item" and row.get("trigger_type") == "Periodic Re-test" and not doc.has_batch_no:
			# the re-test clock lives on the Batch; an Item Group row is fine —
			# it applies only to the group's batch-tracked items
			frappe.throw(
				_(
					"Row #{0}: A Periodic Re-test trigger needs batch tracking — the re-test "
					"schedule lives on the batch. Enable Has Batch No on the item first."
				).format(row.idx)
			)
	_validate_no_overlapping_rows(rows)


def _scopes_overlap(first, second):
	"""Whether two trigger rows can match the same movement (blank = wildcard)."""
	if first.get("trigger_type") != second.get("trigger_type"):
		return False
	if first.get("trigger_type") == "Periodic Re-test":
		return True  # one re-test interval per item

	if first.document_type != second.document_type:
		return False
	if (first.warehouse_role or "") != (second.warehouse_role or ""):
		return False
	# rows with a condition may legitimately share a scope — the condition decides
	if first.get("condition") or second.get("condition"):
		return False

	def wildcard_equal(a, b):
		return not a or not b or a == b

	return all(
		wildcard_equal(first.get(fieldname), second.get(fieldname))
		for fieldname in (
			"stock_entry_type",
			"applicable_warehouse",
			"party_transaction_type",
			"supplier",
			"customer",
		)
	)


def _validate_no_overlapping_rows(rows):
	"""Two triggers matching the same movement make resolution ambiguous —
	whichever sits first would silently win."""
	for index, row in enumerate(rows):
		for other in rows[index + 1 :]:
			if _scopes_overlap(row, other):
				frappe.throw(
					_(
						"Rows #{0} and #{1} overlap: both can match the same movement, making it "
						"ambiguous which inspection settings apply. Narrow one of them or remove it."
					).format(row.idx, other.idx),
					title=_("Overlapping Quality Triggers"),
				)


def _validate_condition_syntax(row):
	"""Reject a condition the sandbox will not accept, while the author is still looking at it.

	Applies the exact gate frappe.safe_eval applies at runtime — NFKC normalisation
	and its blocked-node check — so a condition that saves is one that will
	evaluate. Nothing is executed here; the expression is only parsed.
	"""
	if not row.get("condition"):
		return

	import unicodedata

	from frappe.utils.safe_exec import _validate_safe_eval_syntax

	try:
		_validate_safe_eval_syntax(unicodedata.normalize("NFKC", row.condition))
	except SyntaxError as exception:
		frappe.throw(
			_("Row #{0}: Condition is not a valid sandboxed expression — {1}").format(
				row.idx, frappe.bold(exception.msg or str(exception))
			),
			title=_("Invalid Condition"),
		)


def _validate_trigger_row(row):
	# Without a template the inspection is verdict-style, which is fine for a
	# sample — but Each Quantity generates its per-unit readings from the
	# template's parameters, so it cannot do without one.
	if row.inspection_basis == "Each Quantity" and not row.inspection_template:
		frappe.throw(
			_(
				"Row #{0}: An Each Quantity trigger needs an Inspection Template — the per-unit "
				"readings are generated from its parameters."
			).format(row.idx)
		)

	if row.get("sample_size_is_percentage") and flt(row.sample_size) > 100:
		frappe.throw(_("Row #{0}: A percentage sample size cannot exceed 100.").format(row.idx))

	_validate_condition_syntax(row)

	# Periodic Re-test rows are interval-driven and always quarantine; none of the
	# transaction dimensions (document type, direction, parties) apply to them.
	if row.get("trigger_type") == "Periodic Re-test":
		if not row.retest_interval_days or row.retest_interval_days < 1:
			frappe.throw(
				_(
					"Row #{0}: A Periodic Re-test trigger needs a re-test interval of at least one day."
				).format(row.idx)
			)
		row.quality_control_mode = "Quarantine"
		# none of the transaction dimensions apply to an interval-driven trigger;
		# clear any values lingering from before the row was switched over
		for fieldname in (
			"document_type",
			"warehouse_role",
			"stock_entry_type",
			"party_transaction_type",
			"applicable_warehouse",
			"supplier",
			"customer",
			"condition",
		):
			row.set(fieldname, None)
		return

	if not row.document_type:
		frappe.throw(_("Row #{0}: Document Type is required for a Transaction trigger.").format(row.idx))

	# Stock Entry Type only applies to Stock Entry rows.
	if row.stock_entry_type and row.document_type != "Stock Entry":
		frappe.throw(_("Row #{0}: Stock Entry Type applies only to Stock Entry.").format(row.idx))

	# External / Internal Transfer only applies to party documents. The field
	# defaults to External, so it is cleared (not rejected) on other doctypes.
	if row.get("party_transaction_type") and row.document_type not in PARTY_DOCTYPES:
		row.party_transaction_type = None

	# a blanket Stock Entry trigger is ambiguous about direction and intent:
	# one row per Stock Entry Type, always
	if (
		row.document_type == "Stock Entry"
		and (row.get("trigger_type") or "") != "Periodic Re-test"
		and not row.stock_entry_type
	):
		frappe.throw(
			_("Row #{0}: Select a Stock Entry Type for the Stock Entry trigger.").format(row.idx),
			title=_("Stock Entry Type Missing"),
		)

	# Warehouse role must respect the direction implied by the document / Stock Entry Type.
	stock_entry_purpose = (
		frappe.db.get_value("Stock Entry Type", row.stock_entry_type, "purpose")
		if row.stock_entry_type
		else None
	)

	# custody holds goods, not stock: there is nothing to route to a Quality
	# Control warehouse before a receipt exists — inspect with Block or Warn
	if row.document_type == "Goods Inward Note" and row.quality_control_mode == "Quarantine":
		frappe.throw(
			_(
				"Row #{0}: A Goods Inward Note holds goods in custody, not stock — there is "
				"nothing to quarantine yet. Use Block or Warn, or trigger on the receipt instead."
			).format(row.idx),
			title=_("Quarantine Needs Stock"),
		)

	# a Quality Control Release is the outcome of an inspection — it is exempt
	# from inspection processing and cannot trigger one
	if stock_entry_purpose == "Quality Control Release":
		frappe.throw(
			_(
				"Row #{0}: A Quality Control Release cannot trigger an inspection — it is the outcome of one."
			).format(row.idx)
		)
	allowed = allowed_warehouse_roles(row.document_type, stock_entry_purpose)
	context = f" ({row.stock_entry_type})" if row.stock_entry_type else ""

	if len(allowed) == 1:
		(only,) = tuple(allowed)
		if row.warehouse_role and row.warehouse_role != only:
			frappe.throw(
				_("Row #{0}: {1}{2} can only use the {3} warehouse role.").format(
					row.idx, row.document_type, context, only
				)
			)
		# auto-set so the user need not pick the only valid direction
		row.warehouse_role = only
	else:
		if not row.warehouse_role:
			frappe.throw(
				_("Row #{0}: Select a warehouse role (Inbound or Outbound) for {1}{2}.").format(
					row.idx, row.document_type, context
				)
			)
		if row.warehouse_role not in allowed:
			frappe.throw(
				_("Row #{0}: {1}{2} cannot use the {3} warehouse role.").format(
					row.idx, row.document_type, context, row.warehouse_role
				)
			)

	# Quarantine holds incoming stock, so it is only meaningful on inbound rows.
	# Checked after the role is resolved (it may have been auto-set above).
	if row.quality_control_mode == "Quarantine" and row.warehouse_role == "Outbound":
		frappe.throw(
			_(
				"Row #{0}: Quarantine applies only to inbound movements — outbound stock cannot "
				"be quarantined. Use Block or Warn instead."
			).format(row.idx)
		)
