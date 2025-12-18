# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Date


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
		{"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 150},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 150},
		{"label": _("Batch"), "fieldname": "batch", "fieldtype": "Link", "options": "Batch", "width": 150},
		{"label": _("Quantity"), "fieldname": "quantity", "fieldtype": "Float", "width": 100},
		{
			"label": _("Stock UOM"),
			"fieldname": "stock_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100,
		},
		{"label": _("Expires On"), "fieldname": "expires_on", "fieldtype": "Date", "width": 100},
		{"label": _("Expiry (In Days)"), "fieldname": "expiry_in_days", "fieldtype": "Int", "width": 130},
		{
			"label": _("Batch ID"),
			"fieldname": "batch_id",
			"fieldtype": "Link",
			"options": "Batch",
			"width": 100,
			"hidden": 1,
		},
	]


def get_data(filters):
	data = []
	title_field = frappe.get_meta("Batch", cached=True).get_title_field()

	for batch in get_batch_details(filters):
		data.append(
			[
				batch.item,
				batch.item_name,
				batch[title_field],
				batch.batch_qty,
				batch.stock_uom,
				batch.expiry_date,
				max((batch.expiry_date - frappe.utils.datetime.date.today()).days, 0)
				if batch.expiry_date
				else None,
				batch.name,
			]
		)

	return data


def get_batch_details(filters):
	batch = frappe.qb.DocType("Batch")
	title_field = frappe.get_meta("Batch", cached=True).get_title_field()
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
			batch[title_field],
		)
		.where(
			(batch.disabled == 0)
			& (batch.batch_qty > 0)
			& ((Date(batch.creation) >= filters["from_date"]) & (Date(batch.creation) <= filters["to_date"]))
		)
		.orderby(batch.creation)
	)

	if filters.get("item"):
		query = query.where(batch.item == filters["item"])

	return query.run(as_dict=True)
