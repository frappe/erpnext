# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import Any, Dict, List, Optional, TypedDict

import frappe
from frappe import _
from frappe.query_builder.functions import Sum


class StockBalanceFilter(TypedDict):
	company: Optional[str]
	warehouse: Optional[str]


SLEntry = Dict[str, Any]


def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_warehouse_wise_balance(filters: StockBalanceFilter) -> List[SLEntry]:
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
		fields=["name", "parent_warehouse", "is_group"],
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

	return warehouses


def update_indent(warehouses):
	for warehouse in warehouses:

		def add_indent(warehouse, indent):
			warehouse.indent = indent
			for child in warehouses:
				if child.parent_warehouse == warehouse.name:
					add_indent(child, indent + 1)

		if warehouse.is_group:
			add_indent(warehouse, warehouse.indent or 0)


def set_balance_in_parent(warehouses):
	# sort warehouses by indent in descending order
	warehouses = sorted(warehouses, key=lambda x: x.get("indent", 0), reverse=1)

	for warehouse in warehouses:

		def update_balance(warehouse, balance):
			for parent in warehouses:
				if warehouse.parent_warehouse == parent.name:
					parent.stock_balance += balance

		update_balance(warehouse, warehouse.stock_balance)


def get_columns():
	return [
		{
			"label": _("Warehouse"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 200,
		},
		{"label": _("Stock Balance"), "fieldname": "stock_balance", "fieldtype": "Float", "width": 150},
	]
