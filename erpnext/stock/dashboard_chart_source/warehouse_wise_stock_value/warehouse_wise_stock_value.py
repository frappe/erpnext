# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils.dashboard import cache_source

from erpnext.stock.utils import get_stock_value_from_bin


@frappe.whitelist()
@cache_source
def get(chart_name = None, chart = None, no_cache = None, filters = None, from_date = None,
	to_date = None, timespan = None, time_interval = None, heatmap_year = None):
	labels, datapoints = [], []
	filters = frappe.parse_json(filters)

	warehouse_filters = [['is_group', '=', 0]]
	if filters and filters.get("company"):
		warehouse_filters.append(['company', '=', filters.get("company")])

	warehouses = frappe.get_list("Warehouse", fields=['name'], filters=warehouse_filters, order_by='name')

	for wh in warehouses:
		balance = get_stock_value_from_bin(warehouse=wh.name)
		wh["balance"] = balance[0][0]

	warehouses  = [x for x in warehouses if not (x.get('balance') == None)]

	if not warehouses:
		return []

	sorted_warehouse_map = sorted(warehouses, key = lambda i: i['balance'], reverse=True)

	if len(sorted_warehouse_map) > 10:
		sorted_warehouse_map = sorted_warehouse_map[:10]

	for warehouse in sorted_warehouse_map:
		labels.append(_(warehouse.get("name")))
		datapoints.append(warehouse.get("balance"))

	return{
		"labels": labels,
		"datasets": [{
			"name": _("Stock Value"),
			"values": datapoints
		}],
		"type": "bar"
	}
