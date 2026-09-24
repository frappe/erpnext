import frappe
from frappe import _

from erpnext.subcontracting.report.utils import get_inward_order_columns, get_inward_order_filters


def execute(filters=None):
	return get_columns(), get_data(filters)


def get_data(filters):
	finished_goods = get_finished_goods(filters)
	raw_materials = get_raw_materials({row.subcontracting_inward_order for row in finished_goods})

	data = []
	for finished_good in finished_goods:
		data.extend(get_finished_good_rows(finished_good, raw_materials.get(finished_good.order_item, [])))

	return data


def get_finished_goods(filters):
	order_filters = get_inward_order_filters(filters)
	if filters.get("subcontracting_inward_order"):
		order_filters.append(["name", "=", filters.subcontracting_inward_order])

	return frappe.get_list(
		"Subcontracting Inward Order",
		fields=[
			"name as subcontracting_inward_order",
			"transaction_date",
			"customer",
			"status",
			"items.name as order_item",
			"items.item_code",
			"items.stock_uom",
			"items.qty",
			"items.produced_qty",
			"items.delivered_qty",
			"items.returned_qty",
		],
		filters=order_filters,
		order_by="transaction_date, name, items.idx",
	)


def get_raw_materials(orders):
	if not orders:
		return {}

	raw_materials = {}
	for row in frappe.get_all(
		"Subcontracting Inward Order Received Item",
		fields=[
			"reference_name",
			"rm_item_code",
			"stock_uom as rm_stock_uom",
			"required_qty",
			"received_qty",
			"consumed_qty",
			"returned_qty as rm_returned_qty",
		],
		filters={"parent": ["in", list(orders)], "is_customer_provided_item": 1},
		order_by="idx",
	):
		raw_materials.setdefault(row.reference_name, []).append(row)

	return raw_materials


def get_finished_good_rows(finished_good, raw_materials):
	rows = raw_materials or [{}]
	return [{**finished_good, **rows[0]}, *rows[1:]]


def get_columns():
	return [
		*get_inward_order_columns(),
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
		{
			"label": _("Finished Good"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{"label": _("UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 80},
		{"label": _("Order Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
		{"label": _("Produced Qty"), "fieldname": "produced_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Delivered Qty"), "fieldname": "delivered_qty", "fieldtype": "Float", "width": 110},
		{
			"label": _("Returned by Customer"),
			"fieldname": "returned_qty",
			"fieldtype": "Float",
			"width": 150,
		},
		{
			"label": _("Raw Material"),
			"fieldname": "rm_item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{"label": _("UOM"), "fieldname": "rm_stock_uom", "fieldtype": "Link", "options": "UOM", "width": 80},
		{"label": _("Required Qty"), "fieldname": "required_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Received Qty"), "fieldname": "received_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Consumed Qty"), "fieldname": "consumed_qty", "fieldtype": "Float", "width": 110},
		{
			"label": _("Returned to Customer"),
			"fieldname": "rm_returned_qty",
			"fieldtype": "Float",
			"width": 150,
		},
	]
