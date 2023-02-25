# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import IfNull
from frappe.utils import flt
from pypika.terms import ExistsCriterion

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
			for warehouse, sle in child_item_balance.items():
				if flt(sle.qty_after_transaction) > 0:
					warehouse_company_map[warehouse] = sle.company

		for warehouse, company in warehouse_company_map.items():
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
				child_item_balance = stock_balance.get(child_item_detail.item_code, frappe._dict()).get(
					warehouse, frappe._dict()
				)
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
		{
			"fieldname": "item_code",
			"label": _("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 300,
		},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 100,
		},
		{"fieldname": "uom", "label": _("UOM"), "fieldtype": "Link", "options": "UOM", "width": 70},
		{"fieldname": "bundle_qty", "label": _("Bundle Qty"), "fieldtype": "Float", "width": 100},
		{"fieldname": "actual_qty", "label": _("Actual Qty"), "fieldtype": "Float", "width": 100},
		{"fieldname": "minimum_qty", "label": _("Minimum Qty"), "fieldtype": "Float", "width": 100},
		{
			"fieldname": "item_group",
			"label": _("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 100,
		},
		{
			"fieldname": "brand",
			"label": _("Brand"),
			"fieldtype": "Link",
			"options": "Brand",
			"width": 100,
		},
		{"fieldname": "description", "label": _("Description"), "width": 140},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 100,
		},
	]
	return columns


def get_items(filters):
	pb_details = frappe._dict()
	item_details = frappe._dict()

	item = frappe.qb.DocType("Item")
	pb = frappe.qb.DocType("Product Bundle")

	query = (
		frappe.qb.from_(item)
		.inner_join(pb)
		.on(pb.new_item_code == item.name)
		.select(
			item.name.as_("item_code"),
			item.item_name,
			pb.description,
			item.item_group,
			item.brand,
			item.stock_uom,
		)
		.where(IfNull(item.disabled, 0) == 0)
	)

	if item_code := filters.get("item_code"):
		query = query.where(item.item_code == item_code)
	else:
		if brand := filters.get("brand"):
			query = query.where(item.brand == brand)
		if item_group := filters.get("item_group"):
			if conditions := get_item_group_condition(item_group, item):
				query = query.where(conditions)

	parent_item_details = query.run(as_dict=True)

	parent_items = []
	for d in parent_item_details:
		parent_items.append(d.item_code)
		item_details[d.item_code] = d

	child_item_details = []
	if parent_items:
		item = frappe.qb.DocType("Item")
		pb = frappe.qb.DocType("Product Bundle")
		pbi = frappe.qb.DocType("Product Bundle Item")

		child_item_details = (
			frappe.qb.from_(pbi)
			.inner_join(pb)
			.on(pb.name == pbi.parent)
			.inner_join(item)
			.on(item.name == pbi.item_code)
			.select(
				pb.new_item_code.as_("parent_item"),
				pbi.item_code,
				item.item_name,
				pbi.description,
				item.item_group,
				item.brand,
				item.stock_uom,
				pbi.uom,
				pbi.qty,
			)
			.where(pb.new_item_code.isin(parent_items))
		).run(as_dict=1)

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

	sle = frappe.qb.DocType("Stock Ledger Entry")
	sle2 = frappe.qb.DocType("Stock Ledger Entry")

	query = (
		frappe.qb.from_(sle)
		.force_index("posting_sort_index")
		.left_join(sle2)
		.on(
			(sle.item_code == sle2.item_code)
			& (sle.warehouse == sle2.warehouse)
			& (sle.posting_date < sle2.posting_date)
			& (sle.posting_time < sle2.posting_time)
			& (sle.name < sle2.name)
		)
		.select(sle.item_code, sle.warehouse, sle.qty_after_transaction, sle.company)
		.where((sle2.name.isnull()) & (sle.docstatus < 2) & (sle.item_code.isin(items)))
	)

	if date := filters.get("date"):
		query = query.where(sle.posting_date <= date)
	else:
		frappe.throw(_("'Date' is required"))

	if filters.get("warehouse"):
		warehouse_details = frappe.db.get_value(
			"Warehouse", filters.get("warehouse"), ["lft", "rgt"], as_dict=1
		)

		if warehouse_details:
			wh = frappe.qb.DocType("Warehouse")
			query = query.where(
				ExistsCriterion(
					frappe.qb.from_(wh)
					.select(wh.name)
					.where((wh.lft >= warehouse_details.lft) & (wh.rgt <= warehouse_details.rgt))
				)
			)

	return query.run(as_dict=True)
