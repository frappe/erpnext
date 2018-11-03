# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.selling.report.sales_analytics.sales_analytics import (get_columns, get_period,
	get_period_date_ranges, get_chart_data, get_rows, get_rows_by_group, get_data_list, get_item_entry,
	get_item_by_group, get_items, get_groups)


def execute(filters=None):
	columns = get_columns(filters)
	data = gen_data(filters)
	chart = get_chart_data(columns)

	return columns, data, None, chart

def get_supplier_by_group(filters):

	return frappe.db.sql("""select c.name, c.supplier_name as type_name, c.supplier_group as grp, g.lft, g.rgt
		from `tabSupplier` c , `tab{tree_type}` g
		where c.supplier_group = g.name"""
		.format(tree_type=filters["tree_type"]), as_dict=1)

def get_supplier():

	return frappe.get_list("Supplier", fields=["name", "supplier_name as type_name"])

def get_supplier_entry(filters):
	date_field = filters["doc_type"] == 'Purchase Order' and 'transaction_date' or 'posting_date'

	if filters["value_quantity"] == 'Value':
		select = "base_net_total as select_field"
	else:
		select = "total_qty as select_field"

	entry = frappe.get_all(filters["doc_type"],
		fields=["supplier as name", select, date_field],
		filters={
			"docstatus": 1,
			"company": filters["company"],
			date_field: ('between', [filters["from_date"], filters["to_date"]])
		}
	)

	return entry

def gen_data(filters):
	if filters["tree_type"] == 'Supplier':
		entry = get_supplier_entry(filters)
		suppliers = get_supplier()

		return get_rows(filters, entry, suppliers)

	elif filters["tree_type"] == 'Item':
		entry = get_item_entry(filters)
		items = get_items(filters)

		return get_rows(filters, entry, items)

	elif filters["tree_type"] == 'Supplier Group':
		supplier = get_supplier_by_group(filters)
		entry = get_supplier_entry(filters)

		return get_rows_by_group(filters, supplier, entry)

	elif filters["tree_type"] == 'Item Group':
		items = get_item_by_group()
		entry = get_item_entry(filters)

		return get_rows_by_group(filters, items, entry)