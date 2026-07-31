# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""How long quarantined stock waits for its verdicts.

One row per Quality Control Lot: when it entered quarantine, when the first
verdict landed, when it was fully decided, and how many units still wait —
quarantined stock nobody decides is working capital standing still.
"""

import frappe
from frappe import _
from frappe.query_builder.functions import IfNull
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
	lot = frappe.qb.DocType("Quality Control Lot")
	quarantined_on = IfNull(lot.source_posting_datetime, lot.creation)

	query = (
		frappe.qb.from_(lot)
		.select(
			lot.name,
			lot.item_code,
			lot.status,
			lot.received_qty,
			lot.decided_qty,
			quarantined_on.as_("quarantined_on"),
		)
		.orderby(quarantined_on)
	)

	if filters.get("company"):
		query = query.where(lot.company == filters.company)
	if filters.get("item_code"):
		query = query.where(lot.item_code == filters.item_code)
	if filters.get("quality_warehouse"):
		query = query.where(lot.quality_warehouse == filters.quality_warehouse)
	if filters.get("from_date"):
		query = query.where(quarantined_on >= filters.from_date)
	if filters.get("to_date"):
		query = query.where(quarantined_on <= filters.to_date)

	lots = query.run(as_dict=True)

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

		quarantined_on = getdate(lot.quarantined_on)
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
