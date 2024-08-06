# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt, today


def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns(filters)
	return columns, data


def get_columns(filters):
	columns = [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 200,
		}
	]

	if filters.show_item_name:
		columns.append(
			{
				"label": _("Item Name"),
				"fieldname": "item_name",
				"fieldtype": "Link",
				"options": "Item",
				"width": 200,
			}
		)

	columns.extend(
		[
			{
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 200,
			},
			{
				"label": _("Batch No"),
				"fieldname": "batch_no",
				"fieldtype": "Link",
				"width": 150,
				"options": "Batch",
			},
			{
				"label": _("Expiry Date"),
				"fieldname": "expiry_date",
				"fieldtype": "Date",
				"width": 120,
			},
			{"label": _("Balance Qty"), "fieldname": "balance_qty", "fieldtype": "Float", "width": 150},
		]
	)

	return columns


def get_data(filters):
	data = []
	batchwise_data = get_batchwise_data_from_stock_ledger(filters)
	batchwise_data = get_batchwise_data_from_serial_batch_bundle(batchwise_data, filters)

	data = parse_batchwise_data(batchwise_data)

	return data


def parse_batchwise_data(batchwise_data):
	data = []
	for key in batchwise_data:
		d = batchwise_data[key]
		if d.balance_qty == 0:
			continue

		data.append(d)

	return data


def get_batchwise_data_from_stock_ledger(filters):
	batchwise_data = frappe._dict({})

	table = frappe.qb.DocType("Stock Ledger Entry")
	batch = frappe.qb.DocType("Batch")

	query = (
		frappe.qb.from_(table)
		.inner_join(batch)
		.on(table.batch_no == batch.name)
		.select(
			table.item_code,
			table.batch_no,
			table.warehouse,
			batch.expiry_date,
			Sum(table.actual_qty).as_("balance_qty"),
		)
		.where(table.is_cancelled == 0)
		.groupby(table.batch_no, table.item_code, table.warehouse)
	)

	query = get_query_based_on_filters(query, batch, table, filters)

	for d in query.run(as_dict=True):
		key = (d.item_code, d.warehouse, d.batch_no)
		batchwise_data.setdefault(key, d)

	return batchwise_data


def get_batchwise_data_from_serial_batch_bundle(batchwise_data, filters):
	table = frappe.qb.DocType("Stock Ledger Entry")
	ch_table = frappe.qb.DocType("Serial and Batch Entry")
	batch = frappe.qb.DocType("Batch")

	query = (
		frappe.qb.from_(table)
		.inner_join(ch_table)
		.on(table.serial_and_batch_bundle == ch_table.parent)
		.inner_join(batch)
		.on(ch_table.batch_no == batch.name)
		.select(
			table.item_code,
			ch_table.batch_no,
			table.warehouse,
			batch.expiry_date,
			Sum(ch_table.qty).as_("balance_qty"),
		)
		.where((table.is_cancelled == 0) & (table.docstatus == 1))
		.groupby(ch_table.batch_no, table.item_code, ch_table.warehouse)
	)

	query = get_query_based_on_filters(query, batch, table, filters)

	for d in query.run(as_dict=True):
		key = (d.item_code, d.warehouse, d.batch_no)
		if key in batchwise_data:
			batchwise_data[key].balance_qty += flt(d.balance_qty)
		else:
			batchwise_data.setdefault(key, d)

	return batchwise_data


def get_query_based_on_filters(query, batch, table, filters):
	if filters.item_code:
		query = query.where(table.item_code == filters.item_code)

	if filters.batch_no:
		query = query.where(batch.name == filters.batch_no)

	if filters.to_date == today():
		if not filters.include_expired_batches:
			query = query.where((batch.expiry_date >= today()) | (batch.expiry_date.isnull()))

		query = query.where(batch.batch_qty > 0)

	else:
		query = query.where(table.posting_date <= filters.to_date)

	if filters.warehouse:
		lft, rgt = frappe.db.get_value("Warehouse", filters.warehouse, ["lft", "rgt"])
		warehouses = frappe.get_all(
			"Warehouse", filters={"lft": (">=", lft), "rgt": ("<=", rgt), "is_group": 0}, pluck="name"
		)

		query = query.where(table.warehouse.isin(warehouses))

	elif filters.warehouse_type:
		warehouses = frappe.get_all(
			"Warehouse", filters={"warehouse_type": filters.warehouse_type, "is_group": 0}, pluck="name"
		)

		query = query.where(table.warehouse.isin(warehouses))

	if filters.show_item_name:
		query = query.select(batch.item_name)

	return query
