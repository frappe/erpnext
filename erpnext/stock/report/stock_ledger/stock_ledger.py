# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import CombineDatetime
from frappe.utils import cint, flt

from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_stock_balance_for
from erpnext.stock.doctype.warehouse.warehouse import apply_warehouse_filter
from erpnext.stock.utils import (
	is_reposting_item_valuation_in_progress,
	update_included_uom_in_report,
)


def execute(filters=None):
	is_reposting_item_valuation_in_progress()
	include_uom = filters.get("include_uom")
	columns = get_columns(filters)
	items = get_items(filters)
	sl_entries = get_stock_ledger_entries(filters, items)
	item_details = get_item_details(items, sl_entries, include_uom)
	opening_row = get_opening_balance(filters, columns, sl_entries)
	precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))

	data = []
	conversion_factors = []
	if opening_row:
		data.append(opening_row)
		conversion_factors.append(0)

	actual_qty = stock_value = 0

	available_serial_nos = {}
	inventory_dimension_filters_applied = check_inventory_dimension_filters_applied(filters)

	for sle in sl_entries:
		item_detail = item_details[sle.item_code]

		sle.update(item_detail)

		if filters.get("batch_no") or inventory_dimension_filters_applied:
			actual_qty += flt(sle.actual_qty, precision)
			stock_value += sle.stock_value_difference

			if sle.voucher_type == "Stock Reconciliation" and not sle.actual_qty:
				actual_qty = sle.qty_after_transaction
				stock_value = sle.stock_value

			sle.update({"qty_after_transaction": actual_qty, "stock_value": stock_value})

		sle.update({"in_qty": max(sle.actual_qty, 0), "out_qty": min(sle.actual_qty, 0)})

		if sle.serial_no:
			update_available_serial_nos(available_serial_nos, sle)

		if sle.actual_qty:
			sle["in_out_rate"] = flt(sle.stock_value_difference / sle.actual_qty, precision)

		elif sle.voucher_type == "Stock Reconciliation":
			sle["in_out_rate"] = sle.valuation_rate

		data.append(sle)

		if include_uom:
			conversion_factors.append(item_detail.conversion_factor)

	update_included_uom_in_report(columns, data, include_uom, conversion_factors)
	return columns, data


def update_available_serial_nos(available_serial_nos, sle):
	serial_nos = get_serial_nos(sle.serial_no)
	key = (sle.item_code, sle.warehouse)
	if key not in available_serial_nos:
		stock_balance = get_stock_balance_for(
			sle.item_code, sle.warehouse, sle.posting_date, sle.posting_time
		)
		serials = get_serial_nos(stock_balance["serial_nos"]) if stock_balance["serial_nos"] else []
		available_serial_nos.setdefault(key, serials)

	existing_serial_no = available_serial_nos[key]
	for sn in serial_nos:
		if sle.actual_qty > 0:
			if sn in existing_serial_no:
				existing_serial_no.remove(sn)
			else:
				existing_serial_no.append(sn)
		else:
			if sn in existing_serial_no:
				existing_serial_no.remove(sn)
			else:
				existing_serial_no.append(sn)

	sle.balance_serial_no = "\n".join(existing_serial_no)


def get_columns(filters):
	columns = [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Datetime", "width": 150},
		{
			"label": _("Item"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 100,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "width": 100},
		{
			"label": _("Stock UOM"),
			"fieldname": "stock_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 90,
		},
	]

	for dimension in get_inventory_dimensions():
		columns.append(
			{
				"label": _(dimension.doctype),
				"fieldname": dimension.fieldname,
				"fieldtype": "Link",
				"options": dimension.doctype,
				"width": 110,
			}
		)

	columns.extend(
		[
			{
				"label": _("In Qty"),
				"fieldname": "in_qty",
				"fieldtype": "Float",
				"width": 80,
				"convertible": "qty",
			},
			{
				"label": _("Out Qty"),
				"fieldname": "out_qty",
				"fieldtype": "Float",
				"width": 80,
				"convertible": "qty",
			},
			{
				"label": _("Balance Qty"),
				"fieldname": "qty_after_transaction",
				"fieldtype": "Float",
				"width": 100,
				"convertible": "qty",
			},
			{
				"label": _("Voucher #"),
				"fieldname": "voucher_no",
				"fieldtype": "Dynamic Link",
				"options": "voucher_type",
				"width": 150,
			},
			{
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 150,
			},
			{
				"label": _("Item Group"),
				"fieldname": "item_group",
				"fieldtype": "Link",
				"options": "Item Group",
				"width": 100,
			},
			{
				"label": _("Brand"),
				"fieldname": "brand",
				"fieldtype": "Link",
				"options": "Brand",
				"width": 100,
			},
			{"label": _("Description"), "fieldname": "description", "width": 200},
			{
				"label": _("Incoming Rate"),
				"fieldname": "incoming_rate",
				"fieldtype": "Currency",
				"width": 110,
				"options": "Company:company:default_currency",
				"convertible": "rate",
			},
			{
				"label": _("Avg Rate (Balance Stock)"),
				"fieldname": "valuation_rate",
				"fieldtype": "Currency",
				"width": 180,
				"options": "Company:company:default_currency",
				"convertible": "rate",
			},
			{
				"label": _("Valuation Rate"),
				"fieldname": "in_out_rate",
				"fieldtype": "Currency",
				"width": 140,
				"options": "Company:company:default_currency",
				"convertible": "rate",
			},
			{
				"label": _("Balance Value"),
				"fieldname": "stock_value",
				"fieldtype": "Currency",
				"width": 110,
				"options": "Company:company:default_currency",
			},
			{
				"label": _("Value Change"),
				"fieldname": "stock_value_difference",
				"fieldtype": "Currency",
				"width": 110,
				"options": "Company:company:default_currency",
			},
			{"label": _("Voucher Type"), "fieldname": "voucher_type", "width": 110},
			{
				"label": _("Voucher #"),
				"fieldname": "voucher_no",
				"fieldtype": "Dynamic Link",
				"options": "voucher_type",
				"width": 100,
			},
			{
				"label": _("Batch"),
				"fieldname": "batch_no",
				"fieldtype": "Link",
				"options": "Batch",
				"width": 100,
			},
			{
				"label": _("Serial No"),
				"fieldname": "serial_no",
				"fieldtype": "Link",
				"options": "Serial No",
				"width": 100,
			},
			{"label": _("Balance Serial No"), "fieldname": "balance_serial_no", "width": 100},
			{
				"label": _("Project"),
				"fieldname": "project",
				"fieldtype": "Link",
				"options": "Project",
				"width": 100,
			},
			{
				"label": _("Company"),
				"fieldname": "company",
				"fieldtype": "Link",
				"options": "Company",
				"width": 110,
			},
		]
	)

	return columns


def get_stock_ledger_entries(filters, items):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	query = (
		frappe.qb.from_(sle)
		.select(
			sle.item_code,
			CombineDatetime(sle.posting_date, sle.posting_time).as_("date"),
			sle.warehouse,
			sle.posting_date,
			sle.posting_time,
			sle.actual_qty,
			sle.incoming_rate,
			sle.valuation_rate,
			sle.company,
			sle.voucher_type,
			sle.qty_after_transaction,
			sle.stock_value_difference,
			sle.voucher_no,
			sle.stock_value,
			sle.batch_no,
			sle.serial_no,
			sle.project,
		)
		.where(
			(sle.docstatus < 2)
			& (sle.is_cancelled == 0)
			& (sle.posting_date[filters.from_date : filters.to_date])
		)
		.orderby(CombineDatetime(sle.posting_date, sle.posting_time))
		.orderby(sle.creation)
	)

	inventory_dimension_fields = get_inventory_dimension_fields()
	if inventory_dimension_fields:
		for fieldname in inventory_dimension_fields:
			query = query.select(fieldname)
			if fieldname in filters and filters.get(fieldname):
				query = query.where(sle[fieldname].isin(filters.get(fieldname)))

	if items:
		query = query.where(sle.item_code.isin(items))

	for field in ["voucher_no", "batch_no", "project", "company"]:
		if filters.get(field):
			query = query.where(sle[field] == filters.get(field))

	query = apply_warehouse_filter(query, sle, filters)

	return query.run(as_dict=True)


def get_inventory_dimension_fields():
	return [dimension.fieldname for dimension in get_inventory_dimensions()]


def get_items(filters):
	item = frappe.qb.DocType("Item")
	query = frappe.qb.from_(item).select(item.name)
	conditions = []

	if item_code := filters.get("item_code"):
		conditions.append(item.name == item_code)
	else:
		if brand := filters.get("brand"):
			conditions.append(item.brand == brand)
		if item_group := filters.get("item_group"):
			if condition := get_item_group_condition(item_group, item):
				conditions.append(condition)

	items = []
	if conditions:
		for condition in conditions:
			query = query.where(condition)
		items = [r[0] for r in query.run()]

	return items


def get_item_details(items, sl_entries, include_uom):
	item_details = {}
	if not items:
		items = list(set(d.item_code for d in sl_entries))

	if not items:
		return item_details

	item = frappe.qb.DocType("Item")
	query = (
		frappe.qb.from_(item)
		.select(item.name, item.item_name, item.description, item.item_group, item.brand, item.stock_uom)
		.where(item.name.isin(items))
	)

	if include_uom:
		ucd = frappe.qb.DocType("UOM Conversion Detail")
		query = (
			query.left_join(ucd)
			.on((ucd.parent == item.name) & (ucd.uom == include_uom))
			.select(ucd.conversion_factor)
		)

	res = query.run(as_dict=True)

	for item in res:
		item_details.setdefault(item.name, item)

	return item_details


def get_sle_conditions(filters):
	conditions = []
	if filters.get("warehouse"):
		warehouse_condition = get_warehouse_condition(filters.get("warehouse"))
		if warehouse_condition:
			conditions.append(warehouse_condition)
	if filters.get("voucher_no"):
		conditions.append("voucher_no=%(voucher_no)s")
	if filters.get("batch_no"):
		conditions.append("batch_no=%(batch_no)s")
	if filters.get("project"):
		conditions.append("project=%(project)s")

	for dimension in get_inventory_dimensions():
		if filters.get(dimension.fieldname):
			conditions.append(f"{dimension.fieldname} in %({dimension.fieldname})s")

	return "and {}".format(" and ".join(conditions)) if conditions else ""


def get_opening_balance(filters, columns, sl_entries):
	if not (filters.item_code and filters.warehouse and filters.from_date):
		return

	from erpnext.stock.stock_ledger import get_previous_sle

	last_entry = get_previous_sle(
		{
			"item_code": filters.item_code,
			"warehouse_condition": get_warehouse_condition(filters.warehouse),
			"posting_date": filters.from_date,
			"posting_time": "00:00:00",
		}
	)

	# check if any SLEs are actually Opening Stock Reconciliation
	for sle in list(sl_entries):
		if (
			sle.get("voucher_type") == "Stock Reconciliation"
			and sle.posting_date == filters.from_date
			and frappe.db.get_value("Stock Reconciliation", sle.voucher_no, "purpose") == "Opening Stock"
		):
			last_entry = sle
			sl_entries.remove(sle)

	row = {
		"item_code": _("'Opening'"),
		"qty_after_transaction": last_entry.get("qty_after_transaction", 0),
		"valuation_rate": last_entry.get("valuation_rate", 0),
		"stock_value": last_entry.get("stock_value", 0),
	}

	return row


def get_warehouse_condition(warehouse):
	warehouse_details = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"], as_dict=1)
	if warehouse_details:
		return (
			" exists (select name from `tabWarehouse` wh \
			where wh.lft >= %s and wh.rgt <= %s and warehouse = wh.name)"
			% (warehouse_details.lft, warehouse_details.rgt)
		)

	return ""


def get_item_group_condition(item_group, item_table=None):
	item_group_details = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=1)
	if item_group_details:
		if item_table:
			ig = frappe.qb.DocType("Item Group")
			return item_table.item_group.isin(
				(
					frappe.qb.from_(ig)
					.select(ig.name)
					.where(
						(ig.lft >= item_group_details.lft)
						& (ig.rgt <= item_group_details.rgt)
						& (item_table.item_group == ig.name)
					)
				)
			)
		else:
			return (
				"item.item_group in (select ig.name from `tabItem Group` ig \
				where ig.lft >= %s and ig.rgt <= %s and item.item_group = ig.name)"
				% (item_group_details.lft, item_group_details.rgt)
			)


def check_inventory_dimension_filters_applied(filters) -> bool:
	for dimension in get_inventory_dimensions():
		if dimension.fieldname in filters and filters.get(dimension.fieldname):
			return True

	return False
