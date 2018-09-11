# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, today

def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)

def get_columns():
	return [_("Item Code") + ":Link/Item:140", _("Item Name") + "::100", _("Description") + "::200",
		_("Item Group") + ":Link/Item Group:100", _("Brand") + ":Link/Brand:100", _("Warehouse") + ":Link/Warehouse:120",
		_("UOM") + ":Link/UOM:100", _("Actual Qty") + ":Float:100", _("Planned Qty") + ":Float:100",
		_("Requested Qty") + ":Float:110", _("Ordered Qty") + ":Float:100",
		_("Reserved Qty") + ":Float:100", _("Reserved Qty for Production") + ":Float:100",
		_("Reserved for sub contracting") + ":Float:100",
		_("Projected Qty") + ":Float:100", _("Reorder Level") + ":Float:100", _("Reorder Qty") + ":Float:100",
		_("Shortage Qty") + ":Float:100"]

def get_data(filters):
	bin_list = get_bin_list(filters)
	item_map = get_item_map(filters.get("item_code"))
	warehouse_company = {}
	data = []

	for bin in bin_list:
		item = item_map.get(bin.item_code)

		if not item:
			# likely an item that has reached its end of life
			continue

		# item = item_map.setdefault(bin.item_code, get_item(bin.item_code))
		company = warehouse_company.setdefault(bin.warehouse,
			frappe.db.get_value("Warehouse", bin.warehouse, "company"))

		if filters.brand and filters.brand != item.brand:
			continue
			
		elif filters.item_group and filters.item_group != item.item_group:
			continue

		elif filters.company and filters.company != company:
			continue

		re_order_level = re_order_qty = 0

		for d in item.get("reorder_levels"):
			if d.warehouse == bin.warehouse:
				re_order_level = d.warehouse_reorder_level
				re_order_qty = d.warehouse_reorder_qty

		shortage_qty = re_order_level - flt(bin.projected_qty) if (re_order_level or re_order_qty) else 0

		data.append([item.name, item.item_name, item.description, item.item_group, item.brand, bin.warehouse,
			item.stock_uom, bin.actual_qty, bin.planned_qty, bin.indented_qty, bin.ordered_qty,
			bin.reserved_qty, bin.reserved_qty_for_production, bin.reserved_qty_for_sub_contract,
			bin.projected_qty, re_order_level, re_order_qty, shortage_qty])

	return data

def get_bin_list(filters):
	conditions = []
	
	if filters.item_code:
		conditions.append("item_code = '%s' "%filters.item_code)
		
	if filters.warehouse:
		warehouse_details = frappe.db.get_value("Warehouse", filters.warehouse, ["lft", "rgt"], as_dict=1)

		if warehouse_details:
			conditions.append(" exists (select name from `tabWarehouse` wh \
				where wh.lft >= %s and wh.rgt <= %s and bin.warehouse = wh.name)"%(warehouse_details.lft,
				warehouse_details.rgt))

	bin_list = frappe.db.sql("""select item_code, warehouse, actual_qty, planned_qty, indented_qty,
		ordered_qty, reserved_qty, reserved_qty_for_production, reserved_qty_for_sub_contract, projected_qty
		from tabBin bin {conditions} order by item_code, warehouse
		""".format(conditions=" where " + " and ".join(conditions) if conditions else ""), as_dict=1)

	return bin_list

def get_item_map(item_code):
	"""Optimization: get only the item doc and re_order_levels table"""

	condition = ""
	if item_code:
		condition = 'and item_code = "{0}"'.format(frappe.db.escape(item_code, percent=False))

	items = frappe.db.sql("""select * from `tabItem` item
		where is_stock_item = 1
		and disabled=0
		{condition}
		and (end_of_life > %(today)s or end_of_life is null or end_of_life='0000-00-00')
		and exists (select name from `tabBin` bin where bin.item_code=item.name)"""\
		.format(condition=condition), {"today": today()}, as_dict=True)

	condition = ""
	if item_code:
		condition = 'where parent="{0}"'.format(frappe.db.escape(item_code, percent=False))

	reorder_levels = frappe._dict()
	for ir in frappe.db.sql("""select * from `tabItem Reorder` {condition}""".format(condition=condition), as_dict=1):
		if ir.parent not in reorder_levels:
			reorder_levels[ir.parent] = []

		reorder_levels[ir.parent].append(ir)

	item_map = frappe._dict()
	for item in items:
		item["reorder_levels"] = reorder_levels.get(item.name) or []
		item_map[item.name] = item

	return item_map
