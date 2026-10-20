# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from collections import defaultdict

import frappe
from frappe import _
from frappe.core.doctype.user_permission.user_permission import get_user_permissions
from frappe.permissions import get_allowed_docs_for_doctype
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import date_diff, flt, today


def execute(filters=None):
	validate_filters(filters)

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def validate_filters(filters):
	if not filters:
		frappe.throw(_("Please select the required filters"))

	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if not filters.get("to_date"):
		frappe.throw(_("'To Date' is required"))


def get_columns():
	return [
		_("Item") + ":Link/Item:150",
		_("Item Name") + "::150",
		_("Batch") + ":Link/Batch:150",
		_("Stock UOM") + ":Link/UOM:100",
		_("Quantity") + ":Float:100",
		_("Expires On") + ":Date:100",
		_("Expiry (In Days)") + ":Int:130",
	]


def get_data(filters):
	data = []

	for batch in get_batch_details(filters):
		data.append(
			[
				batch.item,
				batch.item_name,
				batch.name,
				batch.stock_uom,
				batch.batch_qty,
				batch.expiry_date,
				date_diff(batch.expiry_date, today()) if batch.expiry_date else None,
			]
		)

	return data


def get_batch_details(filters):
	batch = frappe.qb.DocType("Batch")
	query = (
		frappe.qb.from_(batch)
		.select(
			batch.name,
			batch.creation,
			batch.expiry_date,
			batch.item,
			batch.item_name,
			batch.stock_uom,
			batch.batch_qty,
		)
		.where(
			(batch.disabled == 0)
			& (batch.batch_qty > 0)
			& (batch.expiry_date >= filters["from_date"])
			& (batch.expiry_date <= filters["to_date"])
		)
		.orderby(batch.expiry_date)
		.orderby(batch.creation)
	)

	if filters.get("item"):
		query = query.where(batch.item == filters["item"])

	batches = query.run(as_dict=True)
	set_permitted_batch_qty(batches)

	return [batch for batch in batches if flt(batch.batch_qty) > 0]


def set_permitted_batch_qty(batches):
	warehouses = get_allowed_docs_for_doctype(
		get_user_permissions().get("Warehouse", []), "Stock Ledger Entry"
	)
	if not batches or not warehouses:
		return

	batch_qty = get_batch_qty_in_warehouses([batch.name for batch in batches], warehouses)
	for batch in batches:
		batch.batch_qty = batch_qty.get(batch.name, 0.0)


def get_batch_qty_in_warehouses(batch_nos, warehouses):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	entry = frappe.qb.DocType("Serial and Batch Entry")
	condition = (sle.is_cancelled == 0) & (sle.warehouse.isin(warehouses))

	bundle_qty = (
		frappe.qb.from_(sle)
		.inner_join(entry)
		.on(entry.parent == sle.serial_and_batch_bundle)
		.select(entry.batch_no, Sum(entry.qty))
		.where(condition & (entry.batch_no.isin(batch_nos)))
		.groupby(entry.batch_no)
	).run()

	ledger_qty = (
		frappe.qb.from_(sle)
		.select(sle.batch_no, Sum(sle.actual_qty))
		.where(condition & (sle.batch_no.isin(batch_nos)) & (IfNull(sle.serial_and_batch_bundle, "") == ""))
		.groupby(sle.batch_no)
	).run()

	batch_qty = defaultdict(float)
	for batch_no, qty in [*bundle_qty, *ledger_qty]:
		batch_qty[batch_no] += flt(qty)

	return batch_qty
