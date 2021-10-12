# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt
from six import iteritems

from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition


def execute(filters=None):
	if not filters:
		filters = frappe._dict()

	columns = get_columns()
	item_details, pb_details, parent_items, child_items = get_items(filters)
	stock_balance = get_stock_balance(filters, child_items)

	data = []
	for parent_item in parent_items:
		parent_item_detail = item_details[parent_item]

		required_items = pb_details[parent_item]
		warehouse_company_map = {}
		for child_item in required_items:
			child_item_balance = stock_balance.get(child_item.item_code, frappe._dict())
			for warehouse, sle in iteritems(child_item_balance):
				if flt(sle.qty_after_transaction) > 0:
					warehouse_company_map[warehouse] = sle.company

		for warehouse, company in iteritems(warehouse_company_map):
			parent_row = {
				"indent": 0,
				"item_code": parent_item,
				"item_name": parent_item_detail.item_name,
				"item_group": parent_item_detail.item_group,
				"brand": parent_item_detail.brand,
				"description": parent_item_detail.description,
				"warehouse": warehouse,
				"uom": parent_item_detail.stock_uom,
				"company": company,
			}

			child_rows = []
			for child_item_detail in required_items:
				child_item_balance = stock_balance.get(child_item_detail.item_code, frappe._dict()).get(warehouse, frappe._dict())
				child_row = {
					"indent": 1,
					"parent_item": parent_item,
					"item_code": child_item_detail.item_code,
					"item_name": child_item_detail.item_name,
					"item_group": child_item_detail.item_group,
					"brand": child_item_detail.brand,
					"description": child_item_detail.description,
					"warehouse": warehouse,
					"uom": child_item_detail.uom,
					"actual_qty": flt(child_item_balance.qty_after_transaction),
					"minimum_qty": flt(child_item_detail.qty),
					"company": company,
				}
				child_row["bundle_qty"] = child_row["actual_qty"] // child_row["minimum_qty"]
				child_rows.append(child_row)

			min_bundle_qty = min(map(lambda d: d["bundle_qty"], child_rows))
			parent_row["bundle_qty"] = min_bundle_qty

			data.append(parent_row)
			data += child_rows

	return columns, data


def get_columns():
	columns = [
		{"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 300},
		{"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 100},
		{"fieldname": "uom", "label": _("UOM"), "fieldtype": "Link", "options": "UOM", "width": 70},
		{"fieldname": "bundle_qty", "label": _("Bundle Qty"), "fieldtype": "Float", "width": 100},
		{"fieldname": "actual_qty", "label": _("Actual Qty"), "fieldtype": "Float", "width": 100},
		{"fieldname": "minimum_qty", "label": _("Minimum Qty"), "fieldtype": "Float", "width": 100},
		{"fieldname": "item_group", "label": _("Item Group"), "fieldtype": "Link", "options": "Item Group", "width": 100},
		{"fieldname": "brand", "label": _("Brand"), "fieldtype": "Link", "options": "Brand", "width": 100},
		{"fieldname": "description", "label": _("Description"), "width": 140},
		{"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company", "width": 100}
	]
	return columns


def get_items(filters):
	pb_details = frappe._dict()
	item_details = frappe._dict()

	conditions = get_parent_item_conditions(filters)
	parent_item_details = frappe.db.sql("""
		select item.name as item_code, item.item_name, pb.description, item.item_group, item.brand, item.stock_uom
		from `tabItem` item
		inner join `tabProduct Bundle` pb on pb.new_item_code = item.name
		where ifnull(item.disabled, 0) = 0 {0}
	""".format(conditions), filters, as_dict=1)  # nosec

	parent_items = []
	for d in parent_item_details:
		parent_items.append(d.item_code)
		item_details[d.item_code] = d

	if parent_items:
		child_item_details = frappe.db.sql("""
			select
				pb.new_item_code as parent_item, pbi.item_code, item.item_name, pbi.description, item.item_group, item.brand,
				item.stock_uom, pbi.uom, pbi.qty
			from `tabProduct Bundle Item` pbi
			inner join `tabProduct Bundle` pb on pb.name = pbi.parent
			inner join `tabItem` item on item.name = pbi.item_code
			where pb.new_item_code in ({0})
		""".format(", ".join(["%s"] * len(parent_items))), parent_items, as_dict=1)  # nosec
	else:
		child_item_details = []

	child_items = set()
	for d in child_item_details:
		if d.item_code != d.parent_item:
			pb_details.setdefault(d.parent_item, []).append(d)
			child_items.add(d.item_code)
			item_details[d.item_code] = d

	child_items = list(child_items)
	return item_details, pb_details, parent_items, child_items


def get_stock_balance(filters, items):
	sle = get_stock_ledger_entries(filters, items)
	stock_balance = frappe._dict()
	for d in sle:
		stock_balance.setdefault(d.item_code, frappe._dict())[d.warehouse] = d
	return stock_balance


def get_stock_ledger_entries(filters, items):
	if not items:
		return []

	item_conditions_sql = ' and sle.item_code in ({})' \
		.format(', '.join(frappe.db.escape(i) for i in items))

	conditions = get_sle_conditions(filters)

	return frappe.db.sql("""
		select
			sle.item_code, sle.warehouse, sle.qty_after_transaction, sle.company
		from
			`tabStock Ledger Entry` sle force index (posting_sort_index)
		left join `tabStock Ledger Entry` sle2 on
			sle.item_code = sle2.item_code and sle.warehouse = sle2.warehouse
			and (sle.posting_date, sle.posting_time, sle.name) < (sle2.posting_date, sle2.posting_time, sle2.name)
		where sle2.name is null and sle.docstatus < 2 %s %s""" % (item_conditions_sql, conditions), as_dict=1)  # nosec


def get_parent_item_conditions(filters):
	conditions = []

	if filters.get("item_code"):
		conditions.append("item.item_code = %(item_code)s")
	else:
		if filters.get("brand"):
			conditions.append("item.brand=%(brand)s")
		if filters.get("item_group"):
			conditions.append(get_item_group_condition(filters.get("item_group")))

	conditions = " and ".join(conditions)
	return "and {0}".format(conditions) if conditions else ""


def get_sle_conditions(filters):
	conditions = ""
	if not filters.get("date"):
		frappe.throw(_("'Date' is required"))

	conditions += " and sle.posting_date <= %s" % frappe.db.escape(filters.get("date"))

	if filters.get("warehouse"):
		warehouse_details = frappe.db.get_value("Warehouse", filters.get("warehouse"), ["lft", "rgt"], as_dict=1)
		if warehouse_details:
			conditions += " and exists (select name from `tabWarehouse` wh \
				where wh.lft >= %s and wh.rgt <= %s and sle.warehouse = wh.name)" % (warehouse_details.lft, warehouse_details.rgt)  # nosec

	return conditions
