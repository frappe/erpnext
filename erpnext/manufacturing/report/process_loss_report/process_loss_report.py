# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import Dict, List, Tuple

import frappe
from frappe import _
from frappe.query_builder.functions import Sum

Filters = frappe._dict
Row = frappe._dict
Data = List[Row]
Columns = List[Dict[str, str]]
QueryArgs = Dict[str, str]


def execute(filters: Filters) -> Tuple[Columns, Data]:
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_data(filters: Filters) -> Data:
	wo = frappe.qb.DocType("Work Order")
	se = frappe.qb.DocType("Stock Entry")

	query = (
		frappe.qb.from_(wo)
		.inner_join(se)
		.on(wo.name == se.work_order)
		.select(
			wo.name,
			wo.status,
			wo.production_item,
			wo.qty,
			wo.produced_qty,
			wo.process_loss_qty,
			(wo.produced_qty - wo.process_loss_qty).as_("actual_produced_qty"),
			Sum(se.total_incoming_value).as_("total_fg_value"),
			Sum(se.total_outgoing_value).as_("total_rm_value"),
		)
		.where(
			(wo.process_loss_qty > 0)
			& (wo.company == filters.company)
			& (se.docstatus == 1)
			& (se.posting_date.between(filters.from_date, filters.to_date))
		)
		.groupby(se.work_order)
	)

	if "item" in filters:
		query.where(wo.production_item == filters.item)

	if "work_order" in filters:
		query.where(wo.name == filters.work_order)

	data = query.run(as_dict=True)

	update_data_with_total_pl_value(data)

	return data


def get_columns() -> Columns:
	return [
		{
			"label": _("Work Order"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Work Order",
			"width": "200",
		},
		{
			"label": _("Item"),
			"fieldname": "production_item",
			"fieldtype": "Link",
			"options": "Item",
			"width": "100",
		},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": "100"},
		{
			"label": _("Manufactured Qty"),
			"fieldname": "produced_qty",
			"fieldtype": "Float",
			"width": "150",
		},
		{"label": _("Loss Qty"), "fieldname": "process_loss_qty", "fieldtype": "Float", "width": "150"},
		{
			"label": _("Actual Manufactured Qty"),
			"fieldname": "actual_produced_qty",
			"fieldtype": "Float",
			"width": "150",
		},
		{"label": _("Loss Value"), "fieldname": "total_pl_value", "fieldtype": "Float", "width": "150"},
		{"label": _("FG Value"), "fieldname": "total_fg_value", "fieldtype": "Float", "width": "150"},
		{
			"label": _("Raw Material Value"),
			"fieldname": "total_rm_value",
			"fieldtype": "Float",
			"width": "150",
		},
	]


def update_data_with_total_pl_value(data: Data) -> None:
	for row in data:
		value_per_unit_fg = row["total_fg_value"] / row["actual_produced_qty"]
		row["total_pl_value"] = row["process_loss_qty"] * value_per_unit_fg
