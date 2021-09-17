# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils.data import comma_and


def execute(filters=None):
	# if not filters: filters = {}
	columns = get_columns()
	summ_data = []

	data = get_bom_stock(filters)
	qty_to_make = filters.get("qty_to_make")

	manufacture_details = get_manufacturer_records()
	for row in data:
		reqd_qty = qty_to_make * row.actual_qty
		last_pur_price = frappe.db.get_value("Item", row.item_code, "last_purchase_rate")

		summ_data.append(get_report_data(last_pur_price, reqd_qty, row, manufacture_details))
	return columns, summ_data

def get_report_data(last_pur_price, reqd_qty, row, manufacture_details):
	to_build = row.to_build if row.to_build > 0 else 0
	diff_qty = to_build - reqd_qty
	return [row.item_code, row.description,
		comma_and(manufacture_details.get(row.item_code, {}).get('manufacturer', []), add_quotes=False),
		comma_and(manufacture_details.get(row.item_code, {}).get('manufacturer_part', []), add_quotes=False),
		row.actual_qty, str(to_build),
		reqd_qty, diff_qty, last_pur_price]

def get_columns():
	"""return columns"""
	columns = [
		_("Item") + ":Link/Item:100",
		_("Description") + "::150",
		_("Manufacturer") + "::250",
		_("Manufacturer Part Number") + "::250",
		_("Qty") + ":Float:50",
		_("Stock Qty") + ":Float:100",
		_("Reqd Qty")+ ":Float:100",
		_("Diff Qty")+ ":Float:100",
		_("Last Purchase Price")+ ":Float:100",
	]
	return columns

def get_bom_stock(filters):
	conditions = ""
	bom = filters.get("bom")

	table = "`tabBOM Item`"
	qty_field = "qty"

	if filters.get("show_exploded_view"):
		table = "`tabBOM Explosion Item`"
		qty_field = "stock_qty"

	if filters.get("warehouse"):
		warehouse_details = frappe.db.get_value("Warehouse", filters.get("warehouse"), ["lft", "rgt"], as_dict=1)
		if warehouse_details:
			conditions += " and exists (select name from `tabWarehouse` wh \
				where wh.lft >= %s and wh.rgt <= %s and ledger.warehouse = wh.name)" % (warehouse_details.lft,
				warehouse_details.rgt)
		else:
			conditions += " and ledger.warehouse = %s" % frappe.db.escape(filters.get("warehouse"))

	else:
		conditions += ""

	return frappe.db.sql("""
			SELECT
				bom_item.item_code,
				bom_item.description,
				bom_item.{qty_field},
				ifnull(sum(ledger.actual_qty), 0) as actual_qty,
				ifnull(sum(FLOOR(ledger.actual_qty / bom_item.{qty_field})), 0) as to_build
			FROM
				{table} AS bom_item
				LEFT JOIN `tabBin` AS ledger
				ON bom_item.item_code = ledger.item_code
				{conditions}

			WHERE
				bom_item.parent = '{bom}' and bom_item.parenttype='BOM'

			GROUP BY bom_item.item_code""".format(qty_field=qty_field, table=table, conditions=conditions, bom=bom), as_dict=1)

def get_manufacturer_records():
	details = frappe.get_list('Item Manufacturer', fields = ["manufacturer", "manufacturer_part_no", "parent"])
	manufacture_details = frappe._dict()
	for detail in details:
		dic = manufacture_details.setdefault(detail.get('parent'), {})
		dic.setdefault('manufacturer', []).append(detail.get('manufacturer'))
		dic.setdefault('manufacturer_part', []).append(detail.get('manufacturer_part_no'))

	return manufacture_details
