# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import copy
from collections import OrderedDict

import frappe
from frappe import _, qb
from frappe.query_builder import Case, CustomFunction
from frappe.query_builder.functions import Coalesce, DateDiff, Max, Sum
from frappe.utils import date_diff, flt, getdate, nowdate


def execute(filters=None):
	if not filters:
		return [], [], None, []

	validate_filters(filters)

	columns = get_columns(filters)
	data = get_data(filters)
	so_elapsed_time = get_so_elapsed_time(data)

	if not data:
		return [], [], None, []

	data, chart_data = prepare_data(data, so_elapsed_time, filters)

	return columns, data, None, chart_data


def validate_filters(filters):
	from_date, to_date = filters.get("from_date"), filters.get("to_date")

	if not from_date and to_date:
		frappe.throw(_("From and To Dates are required."))
	elif date_diff(to_date, from_date) < 0:
		frappe.throw(_("To Date cannot be before From Date."))


def get_data(filters):
	so = qb.DocType("Sales Order")
	soi = qb.DocType("Sales Order Item")
	sii = qb.DocType("Sales Invoice Item")

	# Use the application's today (nowdate, System Settings timezone) rather than the database
	# server's CURRENT_DATE: the two differ by a day when the DB server runs in a different timezone
	# (e.g. UTC DB + IST app near midnight), which made delay_days non-deterministic on postgres CI.
	# DateDiff is cross-database: DATEDIFF() on MariaDB, date subtraction on postgres; it casts the
	# string date to a date on postgres. delivery_date is functionally dependent on the grouped
	# soi.name primary key, so this is valid under both.
	delay = DateDiff(nowdate(), soi.delivery_date)
	conversion_rate = Coalesce(so.conversion_rate, 1)

	query = (
		qb.from_(so)
		.join(soi)
		.on(soi.parent == so.name)
		.left_join(sii)
		.on((sii.so_detail == soi.name) & (sii.docstatus == 1))
		.select(
			so.transaction_date.as_("date"),
			soi.delivery_date.as_("delivery_date"),
			so.name.as_("sales_order"),
			so.status,
			so.customer,
			soi.item_code,
			delay.as_("delay_days"),
			Case().when(so.status.isin(["Completed", "To Bill"]), 0).else_(delay).as_("delay"),
			soi.qty,
			soi.delivered_qty,
			(soi.qty - soi.delivered_qty).as_("pending_qty"),
			Coalesce(Sum(sii.qty), 0).as_("billed_qty"),
			soi.base_amount.as_("amount"),
			(soi.delivered_qty * soi.base_rate).as_("delivered_qty_amount"),
			(soi.billed_amt * conversion_rate).as_("billed_amount"),
			(soi.base_amount - (soi.billed_amt * conversion_rate)).as_("pending_amount"),
			soi.warehouse.as_("warehouse"),
			so.company,
			soi.name,
			soi.description.as_("description"),
		)
		.where((so.status.notin(["Stopped", "On Hold"])) & (so.docstatus == 1))
		.groupby(soi.name, so.name)
		.orderby(so.transaction_date)
		.orderby(soi.item_code)
	)

	if filters.get("from_date") and filters.get("to_date"):
		query = query.where(so.transaction_date[filters.get("from_date") : filters.get("to_date")])
	if filters.get("company"):
		query = query.where(so.company == filters.get("company"))
	if filters.get("sales_order"):
		query = query.where(so.name.isin(filters.get("sales_order")))
	if filters.get("status"):
		query = query.where(so.status.isin(filters.get("status")))
	if filters.get("warehouse"):
		query = query.where(soi.warehouse == filters.get("warehouse"))

	return query.run(as_dict=True)


def get_so_elapsed_time(data):
	"""
	query SO's elapsed time till latest delivery note
	"""
	so_elapsed_time = OrderedDict()
	if data:
		sales_orders = [x.sales_order for x in data]

		so = qb.DocType("Sales Order")
		soi = qb.DocType("Sales Order Item")
		dn = qb.DocType("Delivery Note")
		dni = qb.DocType("Delivery Note Item")

		# TO_SECONDS is MariaDB-only. On postgres, subtracting dates yields days, so multiply
		# by 86400 for the equivalent second delta. so.transaction_date is neither aggregated nor
		# in the GROUP BY, but it is selectable under postgres' strict GROUP BY because it is
		# functionally dependent on the grouped so.name (a doctype's `name` is always the PK).
		if frappe.db.db_type == "postgres":
			elapsed_seconds = ((Max(dn.posting_date) - so.transaction_date) * 86400).as_("elapsed_seconds")
		else:
			to_seconds = CustomFunction("TO_SECONDS", ["date"])
			elapsed_seconds = (to_seconds(Max(dn.posting_date)) - to_seconds(so.transaction_date)).as_(
				"elapsed_seconds"
			)

		query = (
			qb.from_(so)
			.inner_join(soi)
			.on(soi.parent == so.name)
			.left_join(dni)
			.on(dni.so_detail == soi.name)
			.left_join(dn)
			.on(dni.parent == dn.name)
			.select(
				so.name.as_("sales_order"),
				soi.item_code.as_("so_item_code"),
				elapsed_seconds,
			)
			.where((so.name.isin(sales_orders)) & (dn.docstatus == 1))
			.orderby(so.name, soi.name)
			.groupby(soi.name, so.name)
		)
		dn_elapsed_time = query.run(as_dict=True)

		for e in dn_elapsed_time:
			key = (e.sales_order, e.so_item_code)
			so_elapsed_time[key] = e.elapsed_seconds

	return so_elapsed_time


def prepare_data(data, so_elapsed_time, filters):
	completed, pending = 0, 0

	if filters.get("group_by_so"):
		sales_order_map = {}

	for row in data:
		# sum data for chart
		completed += row["billed_amount"]
		pending += row["pending_amount"]

		# prepare data for report view
		row["qty_to_bill"] = flt(row["qty"]) - flt(row["billed_qty"])

		row["delay"] = 0 if row["delay"] and row["delay"] < 0 else row["delay"]

		row["time_taken_to_deliver"] = (
			so_elapsed_time.get((row.sales_order, row.item_code))
			if row["status"] in ("To Bill", "Completed")
			else 0
		)

		if filters.get("group_by_so"):
			so_name = row["sales_order"]

			if so_name not in sales_order_map:
				# create an entry
				row_copy = copy.deepcopy(row)
				sales_order_map[so_name] = row_copy
			else:
				# update existing entry
				so_row = sales_order_map[so_name]
				so_row["required_date"] = max(getdate(so_row["delivery_date"]), getdate(row["delivery_date"]))
				so_row["delay"] = (
					min(so_row["delay"], row["delay"])
					if row["delay"] and so_row["delay"]
					else so_row["delay"]
				)

				# sum numeric columns
				fields = [
					"qty",
					"delivered_qty",
					"pending_qty",
					"billed_qty",
					"qty_to_bill",
					"amount",
					"delivered_qty_amount",
					"billed_amount",
					"pending_amount",
				]
				for field in fields:
					so_row[field] = flt(row[field]) + flt(so_row[field])

	chart_data = prepare_chart_data(pending, completed)

	if filters.get("group_by_so"):
		data = []
		for so in sales_order_map:
			data.append(sales_order_map[so])
		return data, chart_data

	return data, chart_data


def prepare_chart_data(pending, completed):
	labels = [_("Amount to Bill"), _("Billed Amount")]

	return {
		"data": {"labels": labels, "datasets": [{"values": [pending, completed]}]},
		"type": "donut",
		"height": 300,
	}


def get_columns(filters):
	columns = [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 90},
		{
			"label": _("Sales Order"),
			"fieldname": "sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 160,
		},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 130},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 130,
		},
	]

	if not filters.get("group_by_so"):
		columns.append(
			{
				"label": _("Item Code"),
				"fieldname": "item_code",
				"fieldtype": "Link",
				"options": "Item",
				"width": 100,
			}
		)
		columns.append(
			{"label": _("Description"), "fieldname": "description", "fieldtype": "Small Text", "width": 100}
		)

	columns.extend(
		[
			{
				"label": _("Qty"),
				"fieldname": "qty",
				"fieldtype": "Float",
				"width": 120,
				"convertible": "qty",
			},
			{
				"label": _("Delivered Qty"),
				"fieldname": "delivered_qty",
				"fieldtype": "Float",
				"width": 120,
				"convertible": "qty",
			},
			{
				"label": _("Qty to Deliver"),
				"fieldname": "pending_qty",
				"fieldtype": "Float",
				"width": 120,
				"convertible": "qty",
			},
			{
				"label": _("Billed Qty"),
				"fieldname": "billed_qty",
				"fieldtype": "Float",
				"width": 80,
				"convertible": "qty",
			},
			{
				"label": _("Qty to Bill"),
				"fieldname": "qty_to_bill",
				"fieldtype": "Float",
				"width": 80,
				"convertible": "qty",
			},
			{
				"label": _("Amount"),
				"fieldname": "amount",
				"fieldtype": "Currency",
				"width": 110,
				"options": "Company:company:default_currency",
				"convertible": "rate",
			},
			{
				"label": _("Billed Amount"),
				"fieldname": "billed_amount",
				"fieldtype": "Currency",
				"width": 110,
				"options": "Company:company:default_currency",
				"convertible": "rate",
			},
			{
				"label": _("Pending Amount"),
				"fieldname": "pending_amount",
				"fieldtype": "Currency",
				"width": 130,
				"options": "Company:company:default_currency",
				"convertible": "rate",
			},
			{
				"label": _("Amount Delivered"),
				"fieldname": "delivered_qty_amount",
				"fieldtype": "Currency",
				"width": 100,
				"options": "Company:company:default_currency",
				"convertible": "rate",
			},
			{"label": _("Delivery Date"), "fieldname": "delivery_date", "fieldtype": "Date", "width": 120},
			{"label": _("Delay (in Days)"), "fieldname": "delay", "fieldtype": "Data", "width": 100},
			{
				"label": _("Time Taken to Deliver"),
				"fieldname": "time_taken_to_deliver",
				"fieldtype": "Duration",
				"width": 100,
			},
		]
	)
	if not filters.get("group_by_so"):
		columns.append(
			{
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 100,
			}
		)
	columns.append(
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 100,
		}
	)

	return columns
