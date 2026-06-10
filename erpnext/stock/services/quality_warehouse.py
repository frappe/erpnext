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
