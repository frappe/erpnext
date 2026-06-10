# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""Helpers for the Quality Control warehouse that holds stock quarantined for inspection."""

import frappe

QUALITY_WAREHOUSE_TYPE = "Quality"
TRANSIT_WAREHOUSE_TYPE = "Transit"


def is_quality_warehouse(warehouse: str | None) -> bool:
	"""Whether a warehouse is a Quality Control warehouse holding quarantined stock."""
	if not warehouse:
		return False
	return frappe.get_cached_value("Warehouse", warehouse, "warehouse_type") == QUALITY_WAREHOUSE_TYPE


def is_transit_warehouse(warehouse: str | None) -> bool:
	"""Whether a warehouse is an in-transit (dummy) warehouse used by transit transfers."""
	if not warehouse:
		return False
	return frappe.get_cached_value("Warehouse", warehouse, "warehouse_type") == TRANSIT_WAREHOUSE_TYPE


def get_quality_warehouse(warehouse: str | None) -> str | None:
	"""The Quality Control warehouse that stock from ``warehouse`` is quarantined into, if any."""
	if not warehouse:
		return None
	return frappe.get_cached_value("Warehouse", warehouse, "quality_warehouse")


def validate_quality_warehouse_exit(sle):
	"""Block consuming stock out of a Quality Control warehouse.

	Quarantined stock is non-nettable: the only movements allowed to take it out
	are a Quality Control Release stock entry (accepted stock to the store) and a
	purchase return (rejected stock back to the supplier). Cancellation reversals
	are exempt — undoing the document that deposited the stock is legitimate and
	is reconciled against the Quality Control Lot separately.

	Called for every new Stock Ledger Entry, so it covers every voucher type
	uniformly without per-doctype checks.
	"""
	from frappe import _
	from frappe.utils import flt

	if sle.get("is_cancelled") or flt(sle.get("actual_qty")) >= 0:
		return

	if not is_quality_warehouse(sle.get("warehouse")):
		return

	voucher_type, voucher_no = sle.get("voucher_type"), sle.get("voucher_no")

	if voucher_type == "Stock Entry":
		if frappe.db.get_value("Stock Entry", voucher_no, "purpose") == "Quality Control Release":
			return
	elif voucher_type in ("Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"):
		if frappe.db.get_value(voucher_type, voucher_no, "is_return"):
			return

	frappe.throw(
		_(
			"Stock of {0} in {1} is under quality hold and cannot be consumed until its Quality "
			"Inspection is decided. Accepted stock leaves with a Quality Control Release stock "
			"entry; rejected purchased goods can also leave with a purchase return."
		).format(frappe.bold(sle.get("item_code")), frappe.bold(sle.get("warehouse"))),
		title=_("Stock Under Quality Hold"),
	)
