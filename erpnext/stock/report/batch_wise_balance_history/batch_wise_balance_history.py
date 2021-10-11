# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

from typing import Dict, List, OrderedDict, Tuple

import frappe
from frappe import _
from frappe.utils import cint, flt

Filters = frappe._dict
Row = frappe._dict
Data = List[Row]
Conditions = str
Columns = List[Dict[str, str]]
ItemMap = Dict[str, Row]
ItemBatchWarehouseKey = Tuple[str, str, str]
ItemBatchWarehouseMap = OrderedDict[ItemBatchWarehouseKey, Row]


def execute(filters: Filters) -> Tuple[Columns, Data]:
	validate_filters(filters)
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def validate_filters(filters: Filters) -> None:
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if not filters.get("to_date"):
		frappe.throw(_("'To Date' is required"))

	if from_date > to_date:
		frappe.throw(_("From Date must be before To Date"))


def get_columns() -> Columns:
	return [
		{
			'label': _('Item'),
			'fieldname': 'item_code',
			'fieldtype': 'Link',
			'options': 'Item',
			'width': '100'
		},
		{
			'label': _('Item Name'),
			'fieldname': 'item_name',
			'fieldtype': 'Data',
			'width': '150',
		},
		{
			'label': _('Description'),
			'fieldname': 'description',
			'fieldtype': 'Data',
			'width': '150',
		},
		{
			'label': _('Batch'),
			'fieldname': 'batch_no',
			'fieldtype': 'Link',
			'options': 'Batch',
			'width': '100',
		},
		{
			'label': _('Warehouse'),
			'fieldname': 'warehouse',
			'fieldtype': 'Link',
			'options': 'Warehouse',
			'width': '100',
		},
		{
			'label': _('Opening Qty'),
			'fieldname': 'opening_qty',
			'fieldtype': 'Float',
			'width': '90',
		},
		{
			'label': _('In Qty'),
			'fieldname': 'in_qty',
			'fieldtype': 'Float',
			'width': '80',
		},
		{
			'label': _('Out Qty'),
			'fieldname': 'out_qty',
			'fieldtype': 'Float',
			'width': '80',
		},
		{
			'label': _('Balance Qty'),
			'fieldname': 'balance_qty',
			'fieldtype': 'Float',
			'width': '90',
		},
		{
			'label': _('UOM'),
			'fieldname': 'stock_uom',
			'fieldtype': 'Data',
			'width': '90',
		},
	]


def get_data(filters: Filters) -> Data:
	float_precision = cint(frappe.db.get_default("float_precision")) or 3
	conditions = get_conditions(filters)
	entries = get_stock_ledger_entries(conditions)
	ibw_map = get_item_batch_warehouse_to_qtys_map(entries)
	item_map = get_item_map(filters)
	data = []

	for (item_code, batch_no, warehouse), qtys in ibw_map.items():
		row = {}
		item_details = item_map[item_code]
		row.update({
			'item_code': item_code,
			'batch_no': batch_no,
			'warehouse': warehouse,
		})
		row.update(item_details)

		opening_qty = qtys.get('opening_qty')
		in_qty = qtys.get('in_qty')
		out_qty = qtys.get('out_qty')
		balance_qty = opening_qty + in_qty - out_qty

		row.update({
			'opening_qty': flt(opening_qty, float_precision),
			'in_qty': flt(in_qty, float_precision),
			'out_qty': flt(out_qty, float_precision),
			'balance_qty': flt(balance_qty, float_precision)
		})
		data.append(row)

	return data


def get_conditions(filters: Filters) -> Conditions:
	conditions = ""
	conditions += " AND posting_date >= '%s'" % filters["from_date"]
	conditions += " AND posting_date <= '%s'" % filters["to_date"]

	for field in ["item_code", "warehouse", "batch_no", "company"]:
		field_value = filters.get(field)
		if not field_value:
			continue
		conditions += " AND {0} = {1}".format(field, frappe.db.escape(filters.get(field)))
		field_value = frappe.db.escape(field_value)
		conditions += f" AND {field} = {field_value}"

	return conditions


def get_stock_ledger_entries(conditions: Conditions) -> Data:
	return frappe.db.sql(f"""
		SELECT
			item_code, batch_no, warehouse, posting_date, actual_qty,
			qty_after_transaction - actual_qty as qty_before_transaction,
			voucher_type
		FROM `tabStock Ledger Entry`
		WHERE
			is_cancelled = 0
			AND docstatus < 2
			AND ifnull(batch_no, '') != ''
			{conditions}
		ORDER BY
			item_code,
			batch_no,
			timestamp(posting_date, posting_time)
			ASC""".format(conditions=conditions), as_dict=1)


def get_item_batch_warehouse_to_qtys_map(entries: Data) -> ItemBatchWarehouseMap:
	ibw_map = OrderedDict()
	for entry in entries:
		key = (
			entry.get('item_code'),
			entry.get('batch_no'),
			entry.get('warehouse'),
		)
		if key not in ibw_map:
			ibw_map[key] = {
				'opening_qty': entry.get('qty_before_transaction'),
				'in_qty': 0,
				'out_qty': 0,
			}

		actual_qty = entry.get('actual_qty')
		if actual_qty > 0:
			ibw_map[key]['in_qty'] += actual_qty
		else:
			ibw_map[key]['out_qty'] += abs(actual_qty)
	return ibw_map


def get_item_map(filters: Filters) -> ItemMap:
	item_map = {}
	condition = ""
	item_code = filters.get("item_code")
	if item_code:
		condition = f"WHERE item_code = '{frappe.db.escape(item_code)}'"

	item_list = frappe.db.sql("""
		SELECT name, item_name, description, stock_uom
		FROM tabItem
		{condition}""".format(condition=condition), as_dict=1)

	for d in item_list:
		item_map.setdefault(d.name, d)
		del item_map[d.name]['name']

	return item_map
