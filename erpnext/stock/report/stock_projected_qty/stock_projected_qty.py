# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)

def get_columns():
	return [_("Item Code") + ":Link/Item:140", _("Item Name") + "::100", _("Description") + "::200",
		_("Item Group") + ":Link/Item Group:100", _("Brand") + ":Link/Brand:100", _("Warehouse") + ":Link/Warehouse:120",
		_("UOM") + ":Link/UOM:100", _("Actual Qty") + ":Float:100", _("Planned Qty") + ":Float:100",
		_("Requested Qty") + ":Float:110", _("Ordered Qty") + ":Float:100", _("Reserved Qty") + ":Float:100",
		_("Projected Qty") + ":Float:100", _("Reorder Level") + ":Float:100", _("Reorder Qty") + ":Float:100",
		_("Shortage Qty") + ":Float:100"]

def get_data(filters):
	item_map = {}
	warehouse_company = {}
	data = []

	for bin in get_bin_list(filters):
		item = item_map.setdefault(bin.item_code, frappe.get_doc("Item", bin.item_code))
		company = warehouse_company.setdefault(bin.warehouse, frappe.db.get_value("Warehouse", bin.warehouse, "company"))

		if filters.brand and filters.brand != item.brand:
			continue

		elif filters.company and filters.company != company:
			continue

		re_order_level = re_order_qty = 0

		if bin.warehouse==item.default_warehouse:
			re_order_level = item.re_order_level or 0
			re_order_qty = item.re_order_qty or 0

		for d in item.get("reorder_levels"):
			if d.warehouse == bin.warehouse:
				re_order_level = d.warehouse_reorder_level
				re_order_qty = d.warehouse_reorder_qty

		data.append([item.name, item.item_name, item.description, item.item_group, item.brand, bin.warehouse,
			item.stock_uom, bin.actual_qty, bin.planned_qty, bin.indented_qty, bin.ordered_qty, bin.reserved_qty,
			bin.projected_qty, re_order_level, re_order_qty, re_order_level - bin.projected_qty])

	return data

def get_bin_list(filters):
	bin_filters = frappe._dict()
	if filters.item_code:
		bin_filters.item_code = filters.item_code
	if filters.warehouse:
		bin_filters.warehouse = filters.warehouse

	bin_list = frappe.get_all("Bin", fields=["item_code", "warehouse",
		"actual_qty", "planned_qty", "indented_qty", "ordered_qty", "reserved_qty", "projected_qty"],
		filters=bin_filters, order_by="item_code, warehouse")

	return bin_list
