# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import copy

import frappe
from frappe import _
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import date_diff, flt, getdate

import erpnext
from erpnext.stock.doctype.purchase_receipt.services.billing_status import (
	get_invoiced_qty_against_po_items,
)


def execute(filters=None):
	if not filters:
		return [], []

	filters = frappe._dict(filters)
	filters.company = filters.get("company") or erpnext.get_default_company()

	validate_filters(filters)

	columns = get_columns(filters)
	data = get_data(filters)

	if not data:
		return [], [], None, []

	update_received_amount(data)
	update_billed_qty(data)

	data, chart_data = prepare_data(data, filters)

	return columns, data, None, chart_data


def validate_filters(filters):
	if not filters.get("company"):
		frappe.throw(_("{0} is mandatory").format(_("Company")))

	from_date, to_date = filters.get("from_date"), filters.get("to_date")

	if not from_date and to_date:
		frappe.throw(_("From and To Dates are required."))
	elif date_diff(to_date, from_date) < 0:
		frappe.throw(_("To Date cannot be before From Date."))

	if filters.get("group_by_po") and filters.get("group_by_item"):
		frappe.throw(_("Group the report by Purchase Order or by Item, not both."))


def get_data(filters):
	po = frappe.qb.DocType("Purchase Order")
	po_item = frappe.qb.DocType("Purchase Order Item")

	query = (
		frappe.qb.from_(po)
		.inner_join(po_item)
		.on(po_item.parent == po.name)
		.select(
			po.transaction_date.as_("date"),
			po_item.schedule_date.as_("required_date"),
			po_item.project,
			po.name.as_("purchase_order"),
			po.status,
			po.supplier,
			po_item.item_code,
			po_item.uom,
			po_item.qty,
			po_item.received_qty,
			(po_item.qty - po_item.received_qty).as_("pending_qty"),
			po_item.base_amount.as_("amount"),
			(po_item.billed_amt * IfNull(po.conversion_rate, 1)).as_("billed_amount"),
			(po_item.base_amount - (po_item.billed_amt * IfNull(po.conversion_rate, 1))).as_(
				"pending_amount"
			),
			po.set_warehouse.as_("warehouse"),
			po.company,
			po_item.name,
		)
		.where((po_item.parent == po.name) & (po.status.notin(("Stopped", "On Hold"))) & (po.docstatus == 1))
		.where(po.company == filters.get("company"))
		.orderby(po.transaction_date)
	)

	if filters.get("name"):
		query = query.where(po.name.isin(filters.get("name")))

	if filters.get("from_date") and filters.get("to_date"):
		query = query.where(po.transaction_date.between(filters.get("from_date"), filters.get("to_date")))

	if filters.get("status"):
		query = query.where(po.status.isin(filters.get("status")))

	if filters.get("project"):
		query = query.where(po_item.project == filters.get("project"))

	data = query.run(as_dict=True)

	return data


def update_received_amount(data):
	pr_data = get_received_amount_data(data)

	for row in data:
		row.received_qty_amount = flt(pr_data.get(row.name))


def update_billed_qty(data):
	billed_qty = get_invoiced_qty_against_po_items([row.name for row in data])

	for row in data:
		row.billed_qty = flt(billed_qty.get(row.name))


def get_received_amount_data(data):
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	po_items = [row.name for row in data]

	if not po_items:
		return frappe._dict()

	query = (
		frappe.qb.from_(pr)
		.inner_join(pr_item)
		.on(pr_item.parent == pr.name)
		.select(
			pr_item.purchase_order_item,
			Sum(pr_item.base_amount).as_("received_qty_amount"),
		)
		.where((pr.docstatus == 1) & (pr_item.purchase_order_item.isin(po_items)))
		.groupby(pr_item.purchase_order_item)
	)

	data = query.run()

	if not data:
		return frappe._dict()

	return frappe._dict(data)


AGGREGATED_FIELDS = (
	"qty",
	"received_qty",
	"pending_qty",
	"billed_qty",
	"qty_to_bill",
	"amount",
	"received_qty_amount",
	"billed_amount",
	"pending_amount",
)


def prepare_data(data, filters):
	completed, pending = 0, 0

	for row in data:
		completed += row["billed_amount"]
		pending += row["pending_amount"]

		row["qty_to_bill"] = flt(row["qty"]) - flt(row["billed_qty"])

	chart_data = prepare_chart_data(pending, completed)

	if filters.get("group_by_po"):
		data = group_by_purchase_order(data)
	elif filters.get("group_by_item"):
		data = group_by_item(data)

	return data, chart_data


def group_by_purchase_order(data):
	purchase_order_map = {}

	for row in data:
		group = purchase_order_map.get(row["purchase_order"])
		if not group:
			purchase_order_map[row["purchase_order"]] = copy.deepcopy(row)
			continue

		group["required_date"] = min(getdate(group["required_date"]), getdate(row["required_date"]))
		add_aggregated_fields(group, row)

	return list(purchase_order_map.values())


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

	columns = get_purchase_order_columns()

	if not filters.get("group_by_po"):
		columns.append(get_item_code_column())

	columns += get_quantity_columns() + get_amount_columns()
	columns += [get_warehouse_column(), get_company_column()]

	return columns


def get_grouped_by_item_columns():
	columns = [get_item_code_column(), get_uom_column()]
	columns += get_quantity_columns() + get_amount_columns()
	columns.append(get_company_column())

	return columns


def get_purchase_order_columns():
	return [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 90},
		{"label": _("Required By"), "fieldname": "required_date", "fieldtype": "Date", "width": 90},
		{
			"label": _("Purchase Order"),
			"fieldname": "purchase_order",
			"fieldtype": "Link",
			"options": "Purchase Order",
			"width": 160,
		},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 130},
		{
			"label": _("Supplier"),
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 130,
		},
		{
			"label": _("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 130,
		},
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
			"label": _("Received Qty"),
			"fieldname": "received_qty",
			"fieldtype": "Float",
			"width": 120,
			"convertible": "qty",
		},
		{
			"label": _("Pending Qty"),
			"fieldname": "pending_qty",
			"fieldtype": "Float",
			"width": 80,
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
			"label": _("Received Qty Amount"),
			"fieldname": "received_qty_amount",
			"fieldtype": "Currency",
			"width": 130,
			"options": "Company:company:default_currency",
			"convertible": "rate",
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
