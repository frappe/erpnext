# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import flt, today, cint
from frappe.desk.query_report import group_report_data
from erpnext.stock.utils import update_included_uom_in_dict_report
from frappe.desk.reportview import build_match_conditions

def execute(filters=None):
	show_item_name = frappe.defaults.get_global_default('item_naming_by') != "Item Name"

	filters = frappe._dict(filters or {})
	include_uom = filters.get("include_uom")
	columns = get_columns(filters, show_item_name)
	bin_list = get_bin_list(filters)
	item_map = get_item_map(filters.get("item_code"), include_uom)

	warehouse_company = {}
	data = []
	conversion_factors = []
	for bin in bin_list:
		item = item_map.get(bin.item_code)

		if not item:
			# likely an item that has reached its end of life
			continue

		# item = item_map.setdefault(bin.item_code, get_item(bin.item_code))
		company = warehouse_company.setdefault(bin.warehouse,
			frappe.get_cached_value("Warehouse", bin.warehouse, "company"))

		if filters.brand and filters.brand != item.brand:
			continue

		if filters.item_source and filters.item_source != item.item_source:
			continue
			
		elif filters.item_group and filters.item_group != item.item_group:
			continue

		elif filters.company and filters.company != company:
			continue

		alt_uom_size = item.alt_uom_size if filters.qty_field == "Contents Qty" and item.alt_uom else 1.0

		re_order_level = re_order_qty = 0

		for d in item.get("reorder_levels"):
			if d.warehouse == bin.warehouse:
				re_order_level = d.warehouse_reorder_level
				re_order_qty = d.warehouse_reorder_qty

		shortage_qty = 0
		if (re_order_level or re_order_qty) and re_order_level > bin.projected_qty:
			shortage_qty = re_order_level - flt(bin.projected_qty)

		data.append({
			"item_code": item.name,
			"item_name": item.item_name,
			"disable_item_formatter": cint(show_item_name),
			"item_group": item.item_group,
			"brand": item.brand,
			"warehouse": bin.warehouse,
			"uom": item.alt_uom or item.stock_uom if filters.qty_field == "Contents Qty" else item.stock_uom,
			"actual_qty": bin.actual_qty * alt_uom_size,
			"planned_qty": bin.planned_qty * alt_uom_size,
			"indented_qty": bin.indented_qty * alt_uom_size,
			"ordered_qty": bin.ordered_qty * alt_uom_size,
			"reserved_qty": bin.reserved_qty * alt_uom_size,
			"reserved_qty_for_production": bin.reserved_qty_for_production * alt_uom_size,
			"reserved_qty_for_sub_contract": bin.reserved_qty_for_sub_contract * alt_uom_size,
			"projected_qty": bin.projected_qty * alt_uom_size,
			"re_order_level": re_order_level * alt_uom_size,
			"re_order_qty": re_order_qty * alt_uom_size,
			"shortage_qty": shortage_qty * alt_uom_size
		})

		if include_uom:
			conversion_factors.append(flt(item.conversion_factor) * alt_uom_size)

	update_included_uom_in_dict_report(columns, data, include_uom, conversion_factors)

	grouped_data = get_grouped_data(columns, data, filters, item_map)

	return columns, grouped_data


def get_grouped_data(columns, data, filters, item_map):
	group_by = []
	for i in range(2):
		group_label = filters.get("group_by_" + str(i + 1), "").replace("Group by ", "")

		if not group_label or group_label == "Ungrouped":
			continue
		elif group_label == "Item":
			group_field = "item_code"
		else:
			group_field = scrub(group_label)

		group_by.append(group_field)

	if not group_by:
		return data

	total_fields = [c['fieldname'] for c in columns if c['fieldtype'] in ['Float', 'Currency', 'Int']]

	def postprocess_group(group_object, grouped_by):
		if not group_object.group_field:
			group_object.totals['item_code'] = "'Total'"
		elif group_object.group_field == 'item_code':
			group_object.totals['item_code'] = group_object.group_value

			copy_fields = ['item_name', 'item_group', 'brand', 'uom', 'disable_item_formatter']
			for f in copy_fields:
				group_object.totals[f] = group_object.rows[0][f]
		else:
			group_object.totals['item_code'] = "'{0}: {1}'".format(group_object.group_label, group_object.group_value)

	return group_report_data(data, group_by, total_fields=total_fields, postprocess_group=postprocess_group)


def get_columns(filters, show_item_name=True):
	item_col_width = 150 if filters.get('group_by_1', 'Ungrouped') != 'Ungrouped' or filters.get('group_by_2', 'Ungrouped') != 'Ungrouped'\
		else 100

	columns = [
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": item_col_width if show_item_name else 250},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 120},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 50},
		{"label": _("Actual Qty"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 100, "convertible": "qty"},
		{"label": _("Projected Qty"), "fieldname": "projected_qty", "fieldtype": "Float", "width": 100, "convertible": "qty"},
		{"label": _("Ordered (PO)"), "fieldname": "ordered_qty", "fieldtype": "Float", "width": 110, "convertible": "qty"},
		{"label": _("Reserved (SO)"), "fieldname": "reserved_qty", "fieldtype": "Float", "width": 110, "convertible": "qty"},
		{"label": _("Planned (WO)"), "fieldname": "planned_qty", "fieldtype": "Float", "width": 110, "convertible": "qty"},
		{"label": _("Requested (MREQ)"), "fieldname": "indented_qty", "fieldtype": "Float", "width": 130, "convertible": "qty"},
		{"label": _("Reserved (WO)"), "fieldname": "reserved_qty_for_production", "fieldtype": "Float",
			"width": 110, "convertible": "qty"},
		{"label": _("Reserved (Subcontracting)"), "fieldname": "reserved_qty_for_sub_contract", "fieldtype": "Float",
			"width": 110, "convertible": "qty"},
		{"label": _("Reorder Level"), "fieldname": "re_order_level", "fieldtype": "Float", "width": 110, "convertible": "qty"},
		{"label": _("Reorder Qty"), "fieldname": "re_order_qty", "fieldtype": "Float", "width": 110, "convertible": "qty"},
		{"label": _("Shortage Qty"), "fieldname": "shortage_qty", "fieldtype": "Float", "width": 110, "convertible": "qty"},
		{"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 100},
		{"label": _("Brand"), "fieldname": "brand", "fieldtype": "Link", "options": "Brand", "width": 100},
	]

	if not show_item_name:
		columns = [c for c in columns if c.get('fieldname') != 'item_name']

	return columns

def get_bin_list(filters):
	conditions = []

	if filters.item_code:
		conditions.append("item_code = '%s' "%filters.item_code)

	if filters.warehouse:
		warehouse_details = frappe.db.get_value("Warehouse", filters.warehouse, ["lft", "rgt"], as_dict=1)

		if warehouse_details:
			conditions.append(" exists (select name from `tabWarehouse` wh \
				where wh.lft >= %s and wh.rgt <= %s and tabBin.warehouse = wh.name)"%(warehouse_details.lft,
				warehouse_details.rgt))

	match_conditions = build_match_conditions("Bin")
	if match_conditions:
		conditions.append(match_conditions)

	bin_list = frappe.db.sql("""select item_code, warehouse, actual_qty, planned_qty, indented_qty,
		ordered_qty, reserved_qty, reserved_qty_for_production, reserved_qty_for_sub_contract, projected_qty
		from tabBin {conditions} order by item_code, warehouse
		""".format(conditions=" where " + " and ".join(conditions) if conditions else ""), as_dict=1)

	return bin_list

def get_item_map(item_code, include_uom):
	"""Optimization: get only the item doc and re_order_levels table"""

	condition = ""
	if item_code:
		condition = 'and item_code = {0}'.format(frappe.db.escape(item_code, percent=False))

	cf_field = cf_join = ""
	if include_uom:
		cf_field = ", ucd.conversion_factor"
		cf_join = "left join `tabUOM Conversion Detail` ucd on ucd.parent=item.name and ucd.uom=%(include_uom)s"

	items = frappe.db.sql("""
		select item.name, item.item_name, item.description, item.item_group, item.brand, item.item_source,
		item.stock_uom, item.alt_uom, item.alt_uom_size {cf_field}
		from `tabItem` item
		{cf_join}
		where item.is_stock_item = 1
		and item.disabled=0
		{condition}
		and (item.end_of_life > %(today)s or item.end_of_life is null or item.end_of_life='0000-00-00')
		and exists (select name from `tabBin` bin where bin.item_code=item.name)"""\
		.format(cf_field=cf_field, cf_join=cf_join, condition=condition),
		{"today": today(), "include_uom": include_uom}, as_dict=True)

	condition = ""
	if item_code:
		condition = 'where parent={0}'.format(frappe.db.escape(item_code, percent=False))

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
