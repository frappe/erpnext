# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Coalesce, Max, Sum

Filters = frappe._dict
Row = frappe._dict
Data = list[Row]
Columns = list[dict[str, str]]
QueryArgs = dict[str, str]


def execute(filters: Filters) -> tuple[Columns, Data]:
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_data(filters: Filters) -> Data:
	wo = frappe.qb.DocType("Work Order")
	se = frappe.qb.DocType("Stock Entry")
	finished_items = get_finished_items(filters)

	query = (
		frappe.qb.from_(wo)
		.inner_join(se)
		.on(wo.name == se.work_order)
		.left_join(finished_items)
		.on(finished_items.stock_entry == se.name)
		.select(
			# grouped by se.work_order (== wo.name); the work-order columns are constant per group ->
			# Max() keeps the GROUP BY valid on postgres with the same value.
			Max(wo.name).as_("name"),
			Max(wo.status).as_("status"),
			Max(wo.production_item).as_("production_item"),
			Coalesce(Sum(finished_items.produced_qty), 0).as_("produced_qty"),
			Coalesce(Sum(finished_items.output_qty), 0).as_("output_qty"),
			Sum(se.process_loss_qty).as_("process_loss_qty"),
			Max(wo.qty).as_("qty_to_manufacture"),
			Sum(se.total_incoming_value).as_("total_fg_value"),
			Sum(se.total_outgoing_value).as_("total_rm_value"),
		)
		.where(get_stock_entry_conditions(se, filters))
		.groupby(se.work_order)
		.having(Sum(se.process_loss_qty) > 0)
	)

	if filters.get("item"):
		query = query.where(wo.production_item == filters.item)

	if filters.get("work_order"):
		query = query.where(wo.name == filters.work_order)

	data = query.run(as_dict=True)

	update_data_with_total_pl_value(data)

	return data


def get_finished_items(filters: Filters):
	wo = frappe.qb.DocType("Work Order")
	se = frappe.qb.DocType("Stock Entry")
	sed = frappe.qb.DocType("Stock Entry Detail")
	production_item_qty = Case().when(sed.item_code == wo.production_item, sed.transfer_qty).else_(0)
	return (
		frappe.qb.from_(sed)
		.inner_join(se)
		.on(sed.parent == se.name)
		.inner_join(wo)
		.on(se.work_order == wo.name)
		.select(
			sed.parent.as_("stock_entry"),
			Sum(production_item_qty).as_("produced_qty"),
			Sum(sed.transfer_qty).as_("output_qty"),
		)
		.where((sed.is_finished_item == 1) & get_stock_entry_conditions(se, filters))
		.groupby(sed.parent)
	).as_("finished_items")


def get_stock_entry_conditions(se, filters: Filters):
	return (
		(se.company == filters.company)
		& (se.docstatus == 1)
		& (se.purpose == "Manufacture")
		& se.posting_date.between(filters.from_date, filters.to_date)
	)


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
			"label": _("Qty To Manufacture"),
			"fieldname": "qty_to_manufacture",
			"fieldtype": "Float",
			"width": "150",
		},
		{
			"label": _("Manufactured Qty"),
			"fieldname": "produced_qty",
			"fieldtype": "Float",
			"width": "150",
		},
		{
			"label": _("Process Loss Qty"),
			"fieldname": "process_loss_qty",
			"fieldtype": "Float",
			"width": "150",
		},
		{
			"label": _("Process Loss Value"),
			"fieldname": "total_pl_value",
			"fieldtype": "Float",
			"width": "150",
		},
		{
			"label": _("Finished Goods Value"),
			"fieldname": "total_fg_value",
			"fieldtype": "Float",
			"width": "150",
		},
		{
			"label": _("Raw Material Value"),
			"fieldname": "total_rm_value",
			"fieldtype": "Float",
			"width": "150",
		},
	]


def update_data_with_total_pl_value(data: Data) -> None:
	for row in data:
		processed_qty = row["output_qty"] + row["process_loss_qty"]
		row["total_pl_value"] = row["process_loss_qty"] * row["total_fg_value"] / processed_qty
