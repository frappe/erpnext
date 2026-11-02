# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import Any, TypedDict

import frappe
from frappe import _
from frappe.query_builder.functions import Sum


class StockBalanceFilter(TypedDict):
	company: str | None
	warehouse: str | None
	show_disabled_warehouses: int | None


SLEntry = dict[str, Any]


def execute(filters=None):
	columns, data = [], []
	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data


def get_warehouse_wise_balance(filters: StockBalanceFilter) -> list[SLEntry]:
	sle = frappe.qb.DocType("Stock Ledger Entry")

	query = (
		frappe.qb.from_(sle)
		.select(sle.warehouse, Sum(sle.stock_value_difference).as_("stock_balance"))
		.where((sle.docstatus < 2) & (sle.is_cancelled == 0))
		.groupby(sle.warehouse)
	)

	if filters.get("company"):
		query = query.where(sle.company == filters.get("company"))

	data = query.run(as_list=True)
	return frappe._dict(data) if data else frappe._dict()


def get_warehouses(report_filters: StockBalanceFilter):
	return frappe.get_all(
		"Warehouse",
		fields=["name", "parent_warehouse", "is_group", "disabled"],
		filters={"company": report_filters.company},
		order_by="lft",
	)


def get_data(filters: StockBalanceFilter):
	warehouse_balance = get_warehouse_wise_balance(filters)
	warehouses = get_warehouses(filters)

	for warehouse in warehouses:
		warehouse.stock_balance = warehouse_balance.get(warehouse.name, 0) or 0.0

	update_indent(warehouses)
	set_balance_in_parent(warehouses)

	if filters.get("show_disabled_warehouses"):
		return warehouses

	return [warehouse for warehouse in warehouses if not warehouse.disabled or warehouse.stock_balance]


def update_indent(warehouses):
	# warehouses are ordered by lft, so a parent always comes before its children
	indent_by_name = {}
	for warehouse in warehouses:
		warehouse.indent = indent_by_name.get(warehouse.parent_warehouse, -1) + 1
		indent_by_name[warehouse.name] = warehouse.indent


def set_balance_in_parent(warehouses):
	warehouse_by_name = {warehouse.name: warehouse for warehouse in warehouses}

	# reverse lft order rolls up every child before its parent
	for warehouse in reversed(warehouses):
		if parent := warehouse_by_name.get(warehouse.parent_warehouse):
			parent.stock_balance += warehouse.stock_balance


def get_columns(filters: StockBalanceFilter) -> list[dict]:
	columns = [
		{
			"label": _("Warehouse"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 200,
		},
		{"label": _("Stock Balance"), "fieldname": "stock_balance", "fieldtype": "Float", "width": 150},
	]

	if filters.get("show_disabled_warehouses"):
		columns.append(
			{
				"label": _("Warehouse Disabled?"),
				"fieldname": "disabled",
				"fieldtype": "Check",
				"width": 200,
			}
		)

	return columns
