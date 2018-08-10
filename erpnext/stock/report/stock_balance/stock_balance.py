# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, now
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition

from six import iteritems


def execute(filters = None):

	if not filters: filters = {}
	# validate_filters(filters)

	columns = get_columns(filters) or []
	data = get_data(filters) or []

	return columns, data

def get_columns(filters):
	"""return columns"""

	uom = filters.get('by_uom') or 'Stock UOM'
	columns = [
		_("Item")+":Link/Item:100",
		_("Item Name")+"::150",
		_("Item Group")+":Link/Item Group:100",
		_("Brand")+":Link/Brand:90",
		_("Description")+"::140",
		_("Warehouse")+":Link/Warehouse:100",
		_(uom)+":Link/UOM:90",
		_("Opening Qty")+":Float:100",
		_("Opening Value")+":Float:110",
		_("In Qty")+":Float:80",
		_("In Value")+":Float:80",
		_("Out Qty")+":Float:80",
		_("Out Value")+":Float:80",
		_("Balance Qty")+":Float:100",
		_("Balance Value")+":Float:100",
		_("Valuation Rate")+":Float:90",
		_("Reorder Level")+":Float:80",
		_("Reorder Qty")+":Float:80",
		_("Company")+":Link/Company:100"
	]

	return columns

def get_conditions(filters):
	conditions = []
	if filters.get('brand'):
		conditions.append(" it.brand = %(brand)s ")

	if filters.get('item_group'):
		conditions.append(""" it.item_group IN (SELECT ig.name
			FROM `tabItem Group` ig
			INNER JOIN `tabItem Group` igg on igg.name = %(item_group)s
			AND ig.lft BETWEEN igg.lft AND igg.rgt
		)""")


	if filters.get('warehouse'):
		conditions.append("""
			sle.warehouse in (SELECT wh.name
		    FROM `tabWarehouse` wh
		    INNER JOIN `tabWarehouse` whh on whh.name = %(warehouse)s
		    AND wh.is_group = 0
		    AND wh.disabled = 0
		    AND wh.lft BETWEEN whh.lft AND whh.rgt
		    ORDER BY wh.name)
		""")

	return " AND ".join(conditions)

def get_join_condition(filters):

	if filters.get('by_uom') == 'Stock UOM':
		return 'inner join `tabUOM Conversion Detail` uom on uom.parent=it.name and uom.uom=it.stock_uom '

	if filters.get('by_uom') == 'Sales UOM':
		return 'inner join `tabUOM Conversion Detail` uom on uom.parent=it.name and \
		((uom.uom=it.sales_uom and IFNULL(it.sales_uom, "") != "") or \
		(uom.uom=it.stock_uom and IFNULL(it.sales_uom, "") = "")) '

	if filters.get('by_uom') == 'Purchase UOM':
		return 'inner join `tabUOM Conversion Detail` uom on uom.parent=it.name and \
		((uom.uom=it.purchase_uom and IFNULL(it.purchase_uom, "") != "") or \
		(uom.uom=it.stock_uom and IFNULL(it.purchase_uom, "") = "")) '


def get_data(filters):

	condition_filter = get_conditions(filters) or ''

	if condition_filter:
		condition_filter = " and " + condition_filter

	join_condition = get_join_condition(filters)

	query = """
		SELECT sle.item_code
		,it.item_name
		,it.item_group
		,it.brand
		,it.description
		,sle.warehouse
		,sle.stock_uom
		,SUM( IF(sle.posting_date < %(from_date)s, sle.actual_qty, 0)) as opening_qty
		,SUM( IF(sle.posting_date < %(from_date)s, sle.stock_value_difference, 0)) as opening_value
		,SUM( IF(sle.actual_qty > 0 AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s, (sle.actual_qty/COALESCE(uom.conversion_factor, 1)), 0)) as in_qty
		,SUM( IF(sle.actual_qty > 0 AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s, sle.stock_value_difference, 0)) as in_value
		,SUM( IF(sle.actual_qty < 0 AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s, abs((sle.actual_qty/COALESCE(uom.conversion_factor, 1))), 0)) as out_qty
		,SUM( IF(sle.actual_qty < 0 AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s, abs(sle.stock_value_difference), 0)) as out_value
		,SUM((sle.actual_qty/COALESCE(uom.conversion_factor, 1))) as balance_qty
		,SUM(sle.stock_value_difference) as balance_value
		,bin.valuation_rate
		,itr.warehouse_reorder_level
		,itr.warehouse_reorder_qty
		,sle.company
		FROM `tabStock Ledger Entry` sle
		INNER JOIN `tabItem` it
		ON sle.docstatus = 1
		AND it.item_code = sle.item_code
		{condition_filter}
		{join_condition}
		INNER JOIN `tabBin` bin
		on bin.item_code = sle.item_code
		AND bin.warehouse = sle.warehouse
		LEFT JOIN `tabItem Reorder` itr
		ON itr.parent = it.name
		AND sle.warehouse = itr.warehouse
		GROUP BY sle.item_code, sle.warehouse
		HAVING SUM(sle.actual_qty) > 0
	"""

	return frappe.db.sql(query.format(condition_filter=condition_filter, join_condition=join_condition), filters)
