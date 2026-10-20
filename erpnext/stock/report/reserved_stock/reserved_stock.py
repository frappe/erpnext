# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Date
from frappe.utils import flt
from pypika.terms import ValueWrapper

AVAILABLE_QTY_INDEX = 9


def execute(filters=None):
	columns, data = [], []

	validate_filters(filters)

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def validate_filters(filters):
	if not filters:
		frappe.throw(_("Please set filters"))

	for field in ["company", "from_date", "to_date"]:
		if not filters.get(field):
			frappe.throw(_("Please set {0}").format(field))

	if filters.get("from_date") > filters.get("to_date"):
		frappe.throw(_("From Date cannot be greater than To Date"))


def get_data(filters):
	sre = frappe.qb.DocType("Stock Reservation Entry")
	query = frappe.qb.get_query(
		"Stock Reservation Entry",
		fields=[
			sre.creation,
			sre.warehouse,
			sre.item_code,
			sre.stock_uom,
			sre.voucher_qty,
			sre.reserved_qty,
			sre.delivered_qty,
			sre.transferred_qty,
			sre.consumed_qty,
			ValueWrapper(0).as_("available_qty"),
			sre.voucher_type,
			sre.voucher_no,
			sre.from_voucher_type,
			sre.from_voucher_no,
			sre.name.as_("stock_reservation_entry"),
			sre.status,
			sre.project,
			sre.company,
		],
		ignore_permissions=False,
	).where(
		(sre.docstatus == 1)
		& (sre.company == filters.get("company"))
		& ((Date(sre.creation) >= filters.get("from_date")) & (Date(sre.creation) <= filters.get("to_date")))
	)

	for field in [
		"item_code",
		"warehouse",
		"voucher_type",
		"voucher_no",
		"from_voucher_type",
		"from_voucher_no",
		"reservation_based_on",
		"status",
		"project",
	]:
		if value := filters.get(field):
			query = query.where(sre[field] == value)

	if value := filters.get("stock_reservation_entry"):
		query = query.where(sre.name == value)

	data = query.run(as_list=True)
	set_available_qty(data)

	return data


def set_available_qty(data):
	if not data:
		return

	bin = frappe.qb.DocType("Bin")
	free_qty = {
		(item_code, warehouse): flt(actual_qty) - flt(reserved_stock)
		for item_code, warehouse, actual_qty, reserved_stock in (
			frappe.qb.from_(bin)
			.select(bin.item_code, bin.warehouse, bin.actual_qty, bin.reserved_stock)
			.where(
				(bin.item_code.isin({row[2] for row in data}))
				& (bin.warehouse.isin({row[1] for row in data}))
			)
			.run()
		)
	}

	for row in data:
		row[AVAILABLE_QTY_INDEX] = free_qty.get((row[2], row[1]), 0.0)


def get_columns():
	columns = [
		{
			"label": _("Date"),
			"fieldname": "date",
			"fieldtype": "Datetime",
			"width": 150,
		},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 150,
		},
		{
			"fieldname": "item_code",
			"label": _("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 100,
		},
		{
			"fieldname": "stock_uom",
			"label": _("Stock UOM"),
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100,
		},
		{
			"fieldname": "voucher_qty",
			"label": _("Voucher Qty"),
			"fieldtype": "Float",
			"width": 110,
			"convertible": "qty",
		},
		{
			"fieldname": "reserved_qty",
			"label": _("Reserved Qty"),
			"fieldtype": "Float",
			"width": 110,
			"convertible": "qty",
		},
		{
			"fieldname": "delivered_qty",
			"label": _("Delivered Qty"),
			"fieldtype": "Float",
			"width": 110,
			"convertible": "qty",
		},
		{
			"fieldname": "transferred_qty",
			"label": _("Transferred Qty"),
			"fieldtype": "Float",
			"width": 110,
			"convertible": "qty",
		},
		{
			"fieldname": "consumed_qty",
			"label": _("Consumed Qty"),
			"fieldtype": "Float",
			"width": 110,
			"convertible": "qty",
		},
		{
			"fieldname": "available_qty",
			"label": _("Available Qty to Reserve"),
			"fieldtype": "Float",
			"width": 120,
			"convertible": "qty",
		},
		{
			"fieldname": "voucher_type",
			"label": _("Voucher Type"),
			"fieldtype": "Link",
			"options": "DocType",
			"width": 110,
		},
		{
			"fieldname": "voucher_no",
			"label": _("Voucher No"),
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 120,
		},
		{
			"fieldname": "from_voucher_type",
			"label": _("From Voucher Type"),
			"fieldtype": "Link",
			"options": "DocType",
			"width": 110,
		},
		{
			"fieldname": "from_voucher_no",
			"label": _("From Voucher No"),
			"fieldtype": "Dynamic Link",
			"options": "from_voucher_type",
			"width": 120,
		},
		{
			"fieldname": "stock_reservation_entry",
			"label": _("Stock Reservation Entry"),
			"fieldtype": "Link",
			"options": "Stock Reservation Entry",
			"width": 150,
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 100,
		},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 110,
		},
	]

	return columns
