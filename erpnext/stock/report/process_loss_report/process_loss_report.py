# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import Dict, List, Tuple

import frappe
from frappe import _

Filters = frappe._dict
Row = frappe._dict
Data = List[Row]
Columns = List[Dict[str, str]]
QueryArgs = Dict[str, str]

def execute(filters: Filters) -> Tuple[Columns, Data]:
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_data(filters: Filters) -> Data:
	query_args = get_query_args(filters)
	data = run_query(query_args)
	update_data_with_total_pl_value(data)
	return data

def get_columns() -> Columns:
	return [
		{
			'label': _('Work Order'),
			'fieldname': 'name',
			'fieldtype': 'Link',
			'options': 'Work Order',
			'width': '200'
		},
		{
			'label': _('Item'),
			'fieldname': 'production_item',
			'fieldtype': 'Link',
			'options': 'Item',
			'width': '100'
		},
		{
			'label': _('Status'),
			'fieldname': 'status',
			'fieldtype': 'Data',
			'width': '100'
		},
		{
			'label': _('Manufactured Qty'),
			'fieldname': 'produced_qty',
			'fieldtype': 'Float',
			'width': '150'
		},
		{
			'label': _('Loss Qty'),
			'fieldname': 'process_loss_qty',
			'fieldtype': 'Float',
			'width': '150'
		},
		{
			'label': _('Actual Manufactured Qty'),
			'fieldname': 'actual_produced_qty',
			'fieldtype': 'Float',
			'width': '150'
		},
		{
			'label': _('Loss Value'),
			'fieldname': 'total_pl_value',
			'fieldtype': 'Float',
			'width': '150'
		},
		{
			'label': _('FG Value'),
			'fieldname': 'total_fg_value',
			'fieldtype': 'Float',
			'width': '150'
		},
		{
			'label': _('Raw Material Value'),
			'fieldname': 'total_rm_value',
			'fieldtype': 'Float',
			'width': '150'
		}
	]

def get_query_args(filters: Filters) -> QueryArgs:
	query_args = {}
	query_args.update(filters)
	query_args.update(
		get_filter_conditions(filters)
	)
	return query_args

def run_query(query_args: QueryArgs) -> Data:
	return frappe.db.sql("""
		SELECT
			wo.name, wo.status, wo.production_item, wo.qty,
			wo.produced_qty, wo.process_loss_qty,
			(wo.produced_qty - wo.process_loss_qty) as actual_produced_qty,
			sum(se.total_incoming_value) as total_fg_value,
			sum(se.total_outgoing_value) as total_rm_value
		FROM
			`tabWork Order` wo INNER JOIN `tabStock Entry` se
			ON wo.name=se.work_order
		WHERE
			process_loss_qty > 0
			AND wo.company = %(company)s
			AND se.docstatus = 1
			AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s
			{item_filter}
			{work_order_filter}
		GROUP BY
			se.work_order
	""".format(**query_args), query_args, as_dict=1, debug=1)

def update_data_with_total_pl_value(data: Data) -> None:
	for row in data:
		value_per_unit_fg = row['total_fg_value'] / row['actual_produced_qty']
		row['total_pl_value'] = row['process_loss_qty'] * value_per_unit_fg

def get_filter_conditions(filters: Filters) -> QueryArgs:
	filter_conditions = dict(item_filter="", work_order_filter="")
	if "item" in filters:
		production_item = filters.get("item")
		filter_conditions.update(
			{"item_filter": f"AND wo.production_item='{production_item}'"}
		)
	if "work_order" in filters:
		work_order_name = filters.get("work_order")
		filter_conditions.update(
			{"work_order_filter": f"AND wo.name='{work_order_name}'"}
		)
	return filter_conditions
