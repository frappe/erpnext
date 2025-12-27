# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _

from erpnext.stock.doctype.batch.batch import get_batch_qty


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns() -> list[dict]:
	columns = [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 200,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": _("Batch"), "fieldname": "batch", "fieldtype": "Link", "options": "Batch", "width": 200},
		{"label": _("Batch Qty"), "fieldname": "batch_qty", "fieldtype": "Float", "width": 150},
		{"label": _("Stock Qty"), "fieldname": "stock_qty", "fieldtype": "Float", "width": 150},
		{"label": _("Difference"), "fieldname": "difference", "fieldtype": "Float", "width": 150},
	]

	return columns


def get_data(filters=None):
	filters = filters or {}

	item = filters.get("item")
	batch_no = filters.get("batch")

	batch_sle_data = (
		get_batch_qty(
			item_code=item,
			batch_no=batch_no,
			for_stock_levels=True,
			consider_negative_batches=True,
			ignore_reserved_stock=True,
		)
		or []
	)

	stock_qty_map = {}
	for row in batch_sle_data:
		batch = row.get("batch_no")
		if not batch:
			continue
		stock_qty_map[batch] = stock_qty_map.get(batch, 0) + (row.get("qty") or 0)

	batch = frappe.qb.DocType("Batch")

	query = (
		frappe.qb.from_(batch)
		.select(batch.name, batch.item, batch.item_name, batch.batch_qty)
		.where(batch.disabled == 0)
	)

	if item:
		query = query.where(batch.item == item)
	if batch_no:
		query = query.where(batch.name == batch_no)

	batch_records = query.run(as_dict=True) or []

	result = []
	for row in batch_records:
		name = row.get("name")
		batch_qty = row.get("batch_qty") or 0
		stock_qty = stock_qty_map.get(name, 0)
		difference = stock_qty - batch_qty

		if difference != 0:
			result.append(
				{
					"item_code": row.get("item"),
					"item_name": row.get("item_name"),
					"batch": name,
					"batch_qty": batch_qty,
					"stock_qty": stock_qty,
					"difference": difference,
				}
			)

	return result


@frappe.whitelist()
def update_batch_qty(selected_batches=None):
	if not selected_batches:
		return

	selected_batches = json.loads(selected_batches)
	for row in selected_batches:
		batch_name = row.get("batch")

		batches = get_batch_qty(
			batch_no=batch_name,
			item_code=row.get("item_code"),
			for_stock_levels=True,
			consider_negative_batches=True,
			ignore_reserved_stock=True,
		)
		batch_qty = 0.0
		if batches:
			for batch in batches:
				batch_qty += batch.get("qty")

		frappe.db.set_value("Batch", batch_name, "batch_qty", batch_qty)

	frappe.msgprint(_("Batch Qty updated successfully"), alert=True)
