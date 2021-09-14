from __future__ import unicode_literals

import frappe
from frappe.model.db_query import DatabaseQuery
from frappe.utils import flt, nowdate

from erpnext.stock.utils import get_stock_balance


@frappe.whitelist()
def get_data(item_code=None, warehouse=None, parent_warehouse=None,
	company=None, start=0, sort_by="stock_capacity", sort_order="desc"):
	"""Return data to render the warehouse capacity dashboard."""
	filters = get_filters(item_code, warehouse, parent_warehouse, company)

	no_permission, filters = get_warehouse_filter_based_on_permissions(filters)
	if no_permission:
		return []

	capacity_data = get_warehouse_capacity_data(filters, start)

	asc_desc = -1 if sort_order == "desc" else 1
	capacity_data = sorted(capacity_data, key = lambda i: (i[sort_by] * asc_desc))

	return capacity_data

def get_filters(item_code=None, warehouse=None, parent_warehouse=None,
	company=None):
	filters = [['disable', '=', 0]]
	if item_code:
		filters.append(['item_code', '=', item_code])
	if warehouse:
		filters.append(['warehouse', '=', warehouse])
	if company:
		filters.append(['company', '=', company])
	if parent_warehouse:
		lft, rgt = frappe.db.get_value("Warehouse", parent_warehouse, ["lft", "rgt"])
		warehouses = frappe.db.sql_list("""
			select name from `tabWarehouse`
			where lft >=%s and rgt<=%s
		""", (lft, rgt))
		filters.append(['warehouse', 'in', warehouses])
	return filters

def get_warehouse_filter_based_on_permissions(filters):
	try:
		# check if user has any restrictions based on user permissions on warehouse
		if DatabaseQuery('Warehouse', user=frappe.session.user).build_match_conditions():
			filters.append(['warehouse', 'in', [w.name for w in frappe.get_list('Warehouse')]])
		return False, filters
	except frappe.PermissionError:
		# user does not have access on warehouse
		return True, []

def get_warehouse_capacity_data(filters, start):
	capacity_data = frappe.db.get_all('Putaway Rule',
		fields=['item_code', 'warehouse','stock_capacity', 'company'],
		filters=filters,
		limit_start=start,
		limit_page_length='11'
	)

	for entry in capacity_data:
		balance_qty = get_stock_balance(entry.item_code, entry.warehouse, nowdate()) or 0
		entry.update({
			'actual_qty': balance_qty,
			'percent_occupied': flt((flt(balance_qty) / flt(entry.stock_capacity)) * 100, 0)
		})

	return capacity_data
