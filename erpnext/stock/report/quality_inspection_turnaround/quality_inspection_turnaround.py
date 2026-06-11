# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""How long quarantined stock waits for its verdicts.

One row per Quality Control Lot: when it entered quarantine, when the first
verdict landed, when it was fully decided, and how many units still wait —
quarantined stock nobody decides is working capital standing still.
"""

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, today


def execute(filters=None):
	return get_columns(), get_data(frappe._dict(filters or {}))


def get_columns():
	return [
		{
			"fieldname": "quality_control_lot",
			"label": _("Quality Control Lot"),
			"fieldtype": "Link",
			"options": "Quality Control Lot",
			"width": 180,
		},
		{
			"fieldname": "item_code",
			"label": _("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 160,
		},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 130},
		{"fieldname": "received_qty", "label": _("Received Qty"), "fieldtype": "Float", "width": 110},
		{"fieldname": "undecided_qty", "label": _("Undecided Qty"), "fieldtype": "Float", "width": 110},
		{"fieldname": "quarantined_on", "label": _("Quarantined On"), "fieldtype": "Date", "width": 120},
		{
			"fieldname": "first_verdict_on",
			"label": _("First Verdict On"),
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"fieldname": "days_to_first_verdict",
			"label": _("Days To First Verdict"),
			"fieldtype": "Int",
			"width": 130,
		},
		{
			"fieldname": "fully_decided_on",
			"label": _("Fully Decided On"),
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"fieldname": "days_to_decide",
			"label": _("Days To Decide"),
			"fieldtype": "Int",
			"width": 120,
		},
	]


def get_data(filters):
	lot_filters = {}
	if filters.get("company"):
		lot_filters["company"] = filters.company
	if filters.get("item_code"):
		lot_filters["item_code"] = filters.item_code
	if filters.get("quality_warehouse"):
		lot_filters["quality_warehouse"] = filters.quality_warehouse
	if filters.get("from_date") and filters.get("to_date"):
		lot_filters["creation"] = ("between", [filters.from_date, filters.to_date])
	elif filters.get("from_date"):
		lot_filters["creation"] = (">=", filters.from_date)
	elif filters.get("to_date"):
		lot_filters["creation"] = ("<=", filters.to_date)

	lots = frappe.get_all(
		"Quality Control Lot",
		filters=lot_filters,
		fields=["name", "item_code", "status", "received_qty", "decided_qty", "creation"],
		order_by="creation",
	)

	data = []
	for lot in lots:
		undecided_qty = flt(lot.received_qty) - flt(lot.decided_qty)
		if filters.get("pending_only") and undecided_qty <= 0:
			continue

		verdict_dates = frappe.get_all(
			"Quality Inspection",
			filters={
				"reference_type": "Quality Control Lot",
				"reference_name": lot.name,
				"docstatus": 1,
			},
			pluck="report_date",
			order_by="report_date",
		)

		quarantined_on = getdate(lot.creation)
		first_verdict_on = verdict_dates[0] if verdict_dates else None
		fully_decided_on = verdict_dates[-1] if verdict_dates and undecided_qty <= 0 else None

		data.append(
			{
				"quality_control_lot": lot.name,
				"item_code": lot.item_code,
				"status": lot.status,
				"received_qty": lot.received_qty,
				"undecided_qty": undecided_qty,
				"quarantined_on": quarantined_on,
				"first_verdict_on": first_verdict_on,
				"days_to_first_verdict": date_diff(first_verdict_on, quarantined_on)
				if first_verdict_on
				else date_diff(today(), quarantined_on),
				"fully_decided_on": fully_decided_on,
				"days_to_decide": date_diff(fully_decided_on, quarantined_on) if fully_decided_on else None,
			}
		)

	return data
