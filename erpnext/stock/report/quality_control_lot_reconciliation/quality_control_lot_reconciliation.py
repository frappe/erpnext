# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""Detective control for the quarantine subsystem.

The preventive guards funnel every entry into and exit out of a Quality Control
warehouse through controlled flows, so for each item the warehouse's ledger
balance should equal the outstanding (pending + rejected, not yet returned)
quantity of its Quality Control Lots. This report surfaces any drift — e.g.
from direct database writes that bypass the application layer.
"""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	return get_columns(), get_data(filters or {})


def get_columns():
	return [
		{
			"fieldname": "quality_warehouse",
			"label": _("Quality Control Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 220,
		},
		{
			"fieldname": "item_code",
			"label": _("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 200,
		},
		{
			"fieldname": "ledger_qty",
			"label": _("Ledger Qty"),
			"fieldtype": "Float",
			"width": 120,
		},
		{
			"fieldname": "pending_qty",
			"label": _("Pending in Lots"),
			"fieldtype": "Float",
			"width": 130,
		},
		{
			"fieldname": "rejected_qty",
			"label": _("Rejected in Lots"),
			"fieldtype": "Float",
			"width": 130,
		},
		{
			"fieldname": "difference",
			"label": _("Difference"),
			"fieldtype": "Float",
			"width": 120,
		},
	]


def get_data(filters):
	warehouse_filters = {"warehouse_type": "Quality", "disabled": 0, "is_group": 0}
	if filters.get("company"):
		warehouse_filters["company"] = filters.get("company")
	if filters.get("warehouse"):
		warehouse_filters["name"] = filters.get("warehouse")

	quality_warehouses = frappe.get_all("Warehouse", filters=warehouse_filters, pluck="name")
	if not quality_warehouses:
		return []

	# ledger balances per (warehouse, item)
	balances = {}
	for bin_row in frappe.get_all(
		"Bin",
		filters={"warehouse": ("in", quality_warehouses)},
		fields=["warehouse", "item_code", "actual_qty"],
	):
		if flt(bin_row.actual_qty):
			balances[(bin_row.warehouse, bin_row.item_code)] = flt(bin_row.actual_qty)

	# outstanding lot quantities per (warehouse, item)
	lots = {}
	for lot in frappe.get_all(
		"Quality Control Lot",
		filters={"quality_warehouse": ("in", quality_warehouses)},
		fields=["quality_warehouse", "item_code", "pending_qty", "rejected_qty"],
	):
		key = (lot.quality_warehouse, lot.item_code)
		entry = lots.setdefault(key, {"pending_qty": 0.0, "rejected_qty": 0.0})
		entry["pending_qty"] += flt(lot.pending_qty)
		entry["rejected_qty"] += flt(lot.rejected_qty)

	data = []
	for key in sorted(set(balances) | set(lots)):
		warehouse, item_code = key
		ledger_qty = balances.get(key, 0.0)
		pending_qty = lots.get(key, {}).get("pending_qty", 0.0)
		rejected_qty = lots.get(key, {}).get("rejected_qty", 0.0)
		difference = ledger_qty - pending_qty - rejected_qty

		if not (ledger_qty or pending_qty or rejected_qty):
			continue

		data.append(
			{
				"quality_warehouse": warehouse,
				"item_code": item_code,
				"ledger_qty": ledger_qty,
				"pending_qty": pending_qty,
				"rejected_qty": rejected_qty,
				"difference": difference,
			}
		)

	return data
