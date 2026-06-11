# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""Where rejections come from: by supplier, item or inspection parameter.

Supplier and item views aggregate the Quality Control Lot ledger; the
parameter view counts rejected readings (sampled and per-unit alike), naming
the checks that fail most.
"""

import frappe
from frappe import _
from frappe.utils import flt

PURCHASE_DOCTYPES = ("Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	group_by = filters.group_by or "Supplier"

	if group_by == "Parameter":
		return get_parameter_columns(), get_parameter_data(filters)
	return get_lot_columns(group_by), get_lot_data(filters, group_by)


def get_lot_columns(group_by):
	group_column = {
		"fieldname": "group_value",
		"label": _(group_by),
		"fieldtype": "Link",
		"options": "Supplier" if group_by == "Supplier" else "Item",
		"width": 240,
	}
	return [
		group_column,
		{"fieldname": "lots", "label": _("Lots"), "fieldtype": "Int", "width": 80},
		{"fieldname": "received_qty", "label": _("Received Qty"), "fieldtype": "Float", "width": 120},
		{"fieldname": "rejected_qty", "label": _("Rejected Qty"), "fieldtype": "Float", "width": 120},
		{
			"fieldname": "rejection_rate",
			"label": _("Rejection Rate (%)"),
			"fieldtype": "Percent",
			"width": 140,
		},
	]


def get_lot_data(filters, group_by):
	lots = frappe.get_all(
		"Quality Control Lot",
		filters=get_lot_filters(filters),
		fields=[
			"item_code",
			"received_qty",
			"rejected_qty",
			"source_document_type",
			"source_document",
		],
	)

	suppliers = {}
	rows = {}
	for lot in lots:
		if group_by == "Supplier":
			key = get_supplier(lot, suppliers)
			if not key:
				continue
		else:
			key = lot.item_code

		row = rows.setdefault(key, {"group_value": key, "lots": 0, "received_qty": 0, "rejected_qty": 0})
		row["lots"] += 1
		row["received_qty"] += flt(lot.received_qty)
		row["rejected_qty"] += flt(lot.rejected_qty)

	for row in rows.values():
		row["rejection_rate"] = row["rejected_qty"] / row["received_qty"] * 100 if row["received_qty"] else 0

	return sorted(rows.values(), key=lambda row: row["rejected_qty"], reverse=True)


def get_supplier(lot, cache):
	if lot.source_document_type not in PURCHASE_DOCTYPES or not lot.source_document:
		return None
	key = (lot.source_document_type, lot.source_document)
	if key not in cache:
		cache[key] = frappe.db.get_value(lot.source_document_type, lot.source_document, "supplier")
	return cache[key]


def get_lot_filters(filters):
	lot_filters = {}
	if filters.get("company"):
		lot_filters["company"] = filters.company
	if filters.get("item_code"):
		lot_filters["item_code"] = filters.item_code
	if filters.get("from_date"):
		lot_filters["creation"] = (">=", filters.from_date)
	if filters.get("to_date"):
		lot_filters.setdefault("creation", ("<=", filters.to_date))
		if filters.get("from_date"):
			lot_filters["creation"] = ("between", [filters.from_date, filters.to_date])
	return lot_filters


def get_parameter_columns():
	return [
		{
			"fieldname": "specification",
			"label": _("Parameter"),
			"fieldtype": "Link",
			"options": "Quality Inspection Parameter",
			"width": 280,
		},
		{"fieldname": "rejections", "label": _("Rejected Readings"), "fieldtype": "Int", "width": 160},
	]


def get_parameter_data(filters):
	inspection_filters = {"docstatus": 1}
	if filters.get("company"):
		inspection_filters["company"] = filters.company
	if filters.get("item_code"):
		inspection_filters["item_code"] = filters.item_code
	if filters.get("from_date") and filters.get("to_date"):
		inspection_filters["report_date"] = ("between", [filters.from_date, filters.to_date])
	elif filters.get("from_date"):
		inspection_filters["report_date"] = (">=", filters.from_date)
	elif filters.get("to_date"):
		inspection_filters["report_date"] = ("<=", filters.to_date)

	inspections = frappe.get_all("Quality Inspection", filters=inspection_filters, pluck="name")
	if not inspections:
		return []

	counts = {}
	for table, parentfield in (
		("Quality Inspection Reading", "readings"),
		("Quality Inspection Reading Entry", "unit_readings"),
	):
		for row in frappe.get_all(
			table,
			filters={
				"parent": ("in", inspections),
				"parentfield": parentfield,
				"status": "Rejected",
			},
			fields=["specification"],
		):
			counts[row.specification] = counts.get(row.specification, 0) + 1

	return sorted(
		({"specification": name, "rejections": count} for name, count in counts.items()),
		key=lambda row: row["rejections"],
		reverse=True,
	)
