# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import copy
from collections import OrderedDict

import frappe
from frappe import _, qb
from frappe.query_builder import Case, CustomFunction
from frappe.query_builder.functions import Coalesce, Max, Sum
from frappe.utils import date_diff, flt, nowdate
from frappe.utils.nestedset import get_descendants_of

import erpnext


def execute(filters=None):
	if not filters:
		return [], [], None, []

	filters = frappe._dict(filters)
	filters.company = filters.get("company") or erpnext.get_default_company()

	validate_filters(filters)

	columns = get_columns(filters)
	data = get_data(filters)
	so_elapsed_time = {} if filters.get("group_by_item") else get_so_elapsed_time(data)

	if not data:
		return [], [], None, []

	data, chart_data = prepare_data(data, so_elapsed_time, filters)

	return columns, data, None, chart_data


def validate_filters(filters):
	if not filters.get("company"):
		frappe.throw(_("{0} is mandatory").format(_("Company")))

	from_date, to_date = filters.get("from_date"), filters.get("to_date")

	if not from_date and to_date:
		frappe.throw(_("From and To Dates are required."))
	elif date_diff(to_date, from_date) < 0:
		frappe.throw(_("To Date cannot be before From Date."))

	if filters.get("group_by_so") and filters.get("group_by_item"):
		frappe.throw(_("Group the report by Sales Order or by Item, not both."))


def get_data(filters):
	permitted_orders = get_permitted_sales_orders(filters)
	if not permitted_orders:
		return []

	so = qb.DocType("Sales Order")
	soi = qb.DocType("Sales Order Item")
	sii = qb.DocType("Sales Invoice Item")
	si = qb.DocType("Sales Invoice")

	# use the app's today rather than the DB server's CURRENT_DATE so delay_days is timezone-stable
	datediff = CustomFunction("DATEDIFF", ["end_date", "start_date"])
	delay = datediff(nowdate(), soi.delivery_date)
	conversion_rate = Coalesce(so.conversion_rate, 1)
	is_closed = so.status == "Closed"
	no_delay = so.status.isin(["Completed", "To Bill", "Closed"])

	# credit notes don't reduce the order's billed_amt, so exclude them to keep billed qty in step
	counts_as_billed = (Coalesce(si.is_return, 0) == 0) | (
		Coalesce(si.update_billed_amount_in_sales_order, 0) == 1
	)

	query = (
		qb.from_(so)
		.join(soi)
		.on(soi.parent == so.name)
		.left_join(sii)
		.on((sii.so_detail == soi.name) & (sii.docstatus == 1))
		.left_join(si)
		.on(si.name == sii.parent)
		.select(
			so.transaction_date.as_("date"),
			soi.delivery_date.as_("delivery_date"),
			so.name.as_("sales_order"),
			so.status,
			so.customer,
			soi.item_code,
			soi.uom,
			delay.as_("delay_days"),
			Case().when(no_delay, 0).else_(delay).as_("delay"),
			soi.qty,
			soi.delivered_qty,
			Case().when(is_closed, 0).else_(soi.qty - soi.delivered_qty).as_("pending_qty"),
			(
				Coalesce(Sum(Case().when(counts_as_billed, sii.qty * sii.conversion_factor).else_(0)), 0)
				/ soi.conversion_factor
			).as_("billed_qty"),
			soi.base_amount.as_("amount"),
			(soi.delivered_qty * soi.base_rate).as_("delivered_qty_amount"),
			(soi.billed_amt * conversion_rate).as_("billed_amount"),
			Case()
			.when(is_closed, 0)
			.else_(soi.base_amount - (soi.billed_amt * conversion_rate))
			.as_("pending_amount"),
			soi.warehouse.as_("warehouse"),
			so.company,
			soi.name,
			soi.description.as_("description"),
		)
		.where(so.name.isin(permitted_orders))
		.groupby(soi.name, so.name)
		.orderby(so.transaction_date)
		.orderby(soi.item_code)
	)

	if filters.get("warehouse"):
		warehouses = [*get_descendants_of("Warehouse", filters.get("warehouse")), filters.get("warehouse")]
		query = query.where(soi.warehouse.isin(warehouses))

	return query.run(as_dict=True)


def get_permitted_sales_orders(filters):
	so_filters = [
		["Sales Order", "docstatus", "=", 1],
		["Sales Order", "company", "=", filters.get("company")],
		["Sales Order", "status", "not in", ["Stopped", "On Hold"]],
	]

	if filters.get("from_date") and filters.get("to_date"):
		so_filters.append(
			["Sales Order", "transaction_date", "between", [filters.get("from_date"), filters.get("to_date")]]
		)
	if filters.get("sales_order"):
		so_filters.append(["Sales Order", "name", "in", filters.get("sales_order")])
	if filters.get("status"):
		so_filters.append(["Sales Order", "status", "in", filters.get("status")])

	return frappe.qb.get_query(
		table="Sales Order",
		fields=["name"],
		filters=so_filters,
		ignore_permissions=False,
	).run(pluck="name")


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


AGGREGATED_FIELDS = (
	"qty",
	"delivered_qty",
	"pending_qty",
	"billed_qty",
	"qty_to_bill",
	"amount",
	"delivered_qty_amount",
	"billed_amount",
	"pending_amount",
)


def prepare_data(data, so_elapsed_time, filters):
	completed, pending = 0, 0

	for row in data:
		completed += row["billed_amount"]
		pending += row["pending_amount"]

		row["qty_to_bill"] = 0 if row["status"] == "Closed" else flt(row["qty"]) - flt(row["billed_qty"])
		row["delay"] = 0 if row["delay"] and row["delay"] < 0 else row["delay"]
		row["time_taken_to_deliver"] = (
			so_elapsed_time.get((row.sales_order, row.item_code))
			if row["status"] in ("To Bill", "Completed")
			else 0
		)

	chart_data = prepare_chart_data(pending, completed)

	if filters.get("group_by_so"):
		data = group_by_sales_order(data)
	elif filters.get("group_by_item"):
		data = group_by_item(data)

	return data, chart_data


def group_by_sales_order(data):
	sales_order_map = {}

	for row in data:
		group = sales_order_map.get(row["sales_order"])
		if not group:
			sales_order_map[row["sales_order"]] = copy.deepcopy(row)
			continue

		group["delay"] = least_delay(group["delay"], row["delay"])
		add_aggregated_fields(group, row)

	return list(sales_order_map.values())


def least_delay(*delays):
	# completed/closed/not-yet-due lines carry 0; ignore them so none masks an overdue line
	overdue = [d for d in delays if d]
	return min(overdue) if overdue else 0


def group_by_item(data):
	"""Group on company and UOM as well as the item.

	Quantities are in the line UOM and amounts are in the company currency, so neither sums
	across a second UOM of the same item or a second company.
	"""
	item_map = {}

	for row in data:
		key = (row["company"], row["item_code"], row["uom"])
		group = item_map.get(key)
		if not group:
			item_map[key] = copy.deepcopy(row)
			continue

		add_aggregated_fields(group, row)

	return sorted(item_map.values(), key=lambda row: (row["company"], row["item_code"], row["uom"]))


def add_aggregated_fields(group, row):
	for field in AGGREGATED_FIELDS:
		group[field] = flt(group[field]) + flt(row[field])


def prepare_chart_data(pending, completed):
	labels = [_("Amount to Bill"), _("Billed Amount")]

	return {
		"data": {"labels": labels, "datasets": [{"values": [pending, completed]}]},
		"type": "donut",
		"height": 300,
	}


def get_columns(filters):
	if filters.get("group_by_item"):
		return get_grouped_by_item_columns()

	columns = get_sales_order_columns()

	if not filters.get("group_by_so"):
		columns += get_item_columns()

	columns += get_quantity_columns() + get_amount_columns() + get_delivery_columns()

	if not filters.get("group_by_so"):
		columns.append(get_warehouse_column())

	columns.append(get_company_column())

	return columns


def get_grouped_by_item_columns():
	columns = [get_item_code_column(), get_uom_column()]
	columns += get_quantity_columns() + get_amount_columns()
	columns.append(get_company_column())

	return columns


def get_sales_order_columns():
	return [
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


def get_item_columns():
	return [
		get_item_code_column(),
		{"label": _("Description"), "fieldname": "description", "fieldtype": "Small Text", "width": 100},
	]


def get_item_code_column():
	return {
		"label": _("Item Code"),
		"fieldname": "item_code",
		"fieldtype": "Link",
		"options": "Item",
		"width": 100,
	}


def get_uom_column():
	return {
		"label": _("UOM"),
		"fieldname": "uom",
		"fieldtype": "Link",
		"options": "UOM",
		"width": 100,
	}


def get_quantity_columns():
	return [
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
	]


def get_amount_columns():
	return [
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
	]


def get_delivery_columns():
	return [
		{"label": _("Delivery Date"), "fieldname": "delivery_date", "fieldtype": "Date", "width": 120},
		{"label": _("Delay (in Days)"), "fieldname": "delay", "fieldtype": "Data", "width": 100},
		{
			"label": _("Time Taken to Deliver"),
			"fieldname": "time_taken_to_deliver",
			"fieldtype": "Duration",
			"width": 100,
		},
	]


def get_warehouse_column():
	return {
		"label": _("Warehouse"),
		"fieldname": "warehouse",
		"fieldtype": "Link",
		"options": "Warehouse",
		"width": 100,
	}


def get_company_column():
	return {
		"label": _("Company"),
		"fieldname": "company",
		"fieldtype": "Link",
		"options": "Company",
		"width": 100,
	}
