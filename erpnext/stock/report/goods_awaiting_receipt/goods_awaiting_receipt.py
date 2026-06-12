# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""What sits in custody, where, and for how long.

One row per outstanding Goods Inward Note item: goods that physically arrived
but are not stock yet — waiting at a gate, in customs, in a yard — with the
days they have waited. Goods nobody receives are deliveries standing still.
"""

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, today


def execute(filters=None):
	return get_columns(), get_data(frappe._dict(filters or {}))


def get_columns():
	return [
		{
			"fieldname": "goods_inward_note",
			"label": _("Goods Inward Note"),
			"fieldtype": "Link",
			"options": "Goods Inward Note",
			"width": 170,
		},
		{
			"fieldname": "current_inward_location",
			"label": _("Current Location"),
			"fieldtype": "Link",
			"options": "Inward Location",
			"width": 150,
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 150,
		},
		{
			"fieldname": "order",
			"label": _("Order"),
			"fieldtype": "Dynamic Link",
			"options": "order_type",
			"width": 160,
		},
		{"fieldname": "order_type", "label": _("Order Type"), "fieldtype": "Data", "hidden": 1},
		{
			"fieldname": "item_code",
			"label": _("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 160,
		},
		{"fieldname": "awaiting_qty", "label": _("Awaiting Qty"), "fieldtype": "Float", "width": 110},
		{"fieldname": "arrived_on", "label": _("Arrived On"), "fieldtype": "Date", "width": 110},
		{"fieldname": "days_in_custody", "label": _("Days In Custody"), "fieldtype": "Int", "width": 120},
	]


def get_data(filters):
	note_filters = {"docstatus": 1, "status": ("in", ["In Custody", "Partially Received"])}
	for field in ("company", "supplier", "current_inward_location"):
		if filters.get(field):
			note_filters[field] = filters[field]

	notes = frappe.get_all(
		"Goods Inward Note",
		filters=note_filters,
		fields=["name", "supplier", "order_type", "order", "current_inward_location", "arrived_on"],
		order_by="arrived_on",
	)

	data = []
	for note in notes:
		item_filters = {"parent": note.name}
		if filters.get("item_code"):
			item_filters["item_code"] = filters.item_code
		for row in frappe.get_all(
			"Goods Inward Note Item",
			filters=item_filters,
			fields=["item_code", "qty", "received_qty", "returned_qty"],
			order_by="idx",
		):
			awaiting = flt(row.qty) - flt(row.received_qty) - flt(row.returned_qty)
			if awaiting <= 0:
				continue
			data.append(
				{
					"goods_inward_note": note.name,
					"current_inward_location": note.current_inward_location,
					"supplier": note.supplier,
					"order": note.order,
					"order_type": note.order_type,
					"item_code": row.item_code,
					"awaiting_qty": awaiting,
					"arrived_on": getdate(note.arrived_on),
					"days_in_custody": date_diff(today(), getdate(note.arrived_on)),
				}
			)
	return data
