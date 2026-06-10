# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

# Document types that carry a party and can be an external transaction or an
# internal (inter-company) transfer.
PARTY_DOCTYPES = ("Purchase Receipt", "Purchase Invoice", "Delivery Note", "Sales Invoice")

# Direction matrix: which warehouse role(s) make sense for a given document type
# (and, for Stock Entry, a given purpose). A pure receipt is inbound-only, a pure
# issue is outbound-only, and transfer/manufacture-style movements expose both.
_INBOUND_ONLY = {"Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt", "Job Card"}
# Delivery Note / Sales Invoice are outbound for normal documents but inbound for
# returns (a customer return brings stock back in), so both roles are valid:
# Outbound inspects the delivery, Inbound inspects the return.
_RETURNABLE_OUTBOUND = {"Delivery Note", "Sales Invoice"}
_BOTH = {"Inbound", "Outbound"}
_STOCK_ENTRY_ROLES = {
	"Material Receipt": {"Inbound"},
	"Material Issue": {"Outbound"},
	"Send to Subcontractor": {"Outbound"},
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
			"Purchase Invoice",
			"Subcontracting Receipt",
			"Delivery Note",
			"Sales Invoice",
			"Stock Entry",
			"Job Card",
		]
		inspection_basis: DF.Literal["Sample", "Each Quantity"]
		inspection_template: DF.Link
		job_card_inspection_point: DF.Literal["", "Every Job Card", "Final Output Only"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		party_transaction_type: DF.Literal["", "External", "Internal Transfer"]
		quality_control_mode: DF.Literal["Quarantine", "Block", "Warn", "Monitor"]
		sample_size: DF.Float
		sample_size_is_percentage: DF.Check
		stock_entry_type: DF.Link | None
		supplier: DF.Link | None
		warehouse_role: DF.Literal["Inbound", "Outbound"]
	# end: auto-generated types

	pass


def validate_item_quality_triggers(doc, method=None):
	"""Validate the quality_triggers child rows on Item / Item Group.

	Wired via doc_events because a child doctype's own validate() is not invoked
	automatically by the framework.
	"""
	for row in doc.get("quality_triggers") or []:
		_validate_trigger_row(row)


def _validate_trigger_row(row):
	# Stock Entry Type only applies to Stock Entry rows.
	if row.stock_entry_type and row.document_type != "Stock Entry":
		frappe.throw(_("Row #{0}: Stock Entry Type applies only to Stock Entry.").format(row.idx))

	# External / Internal Transfer only applies to party documents.
	if row.get("party_transaction_type") and row.document_type not in PARTY_DOCTYPES:
		frappe.throw(
			_(
				"Row #{0}: Transaction Type (External / Internal Transfer) applies only to "
				"Purchase Receipt, Purchase Invoice, Delivery Note and Sales Invoice."
			).format(row.idx)
		)

	# Inspect On (Every Job Card / Final Output Only) only applies to Job Card rows.
	if row.get("job_card_inspection_point") and row.document_type != "Job Card":
		frappe.throw(_("Row #{0}: Inspect On applies only to Job Card.").format(row.idx))

	# Warehouse role must respect the direction implied by the document / Stock Entry Type.
	stock_entry_purpose = (
		frappe.db.get_value("Stock Entry Type", row.stock_entry_type, "purpose")
		if row.stock_entry_type
		else None
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
				"be quarantined. Use Block, Warn or Monitor instead."
			).format(row.idx)
		)

	# A Job Card gates the completion of an operation, not a stock movement, so it
	# cannot quarantine. Quarantine the produced stock with a Stock Entry trigger.
	if row.document_type == "Job Card" and row.quality_control_mode == "Quarantine":
		frappe.throw(
			_(
				"Row #{0}: Job Card supports Block, Warn or Monitor. To quarantine the produced "
				"stock, add a Stock Entry trigger instead."
			).format(row.idx)
		)
