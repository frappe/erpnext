# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos, get_serial_nos_from_sle_list
from erpnext.stock.report.stock_ledger.stock_ledger import (
	get_item_details,
	get_opening_balance,
	get_stock_ledger_entries,
)
from erpnext.stock.utils import is_reposting_item_valuation_in_progress


def execute(filters=None):
	is_reposting_item_valuation_in_progress()
	columns = get_columns(filters)
	items = get_items(filters)
	sl_entries = get_stock_ledger_entries(filters, items)

	if not sl_entries:
		return columns, []

	item_details = get_item_details(items, sl_entries, False)
	opening_row = get_opening_balance(filters, columns, sl_entries)
	precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))
	data = process_stock_ledger_entries(sl_entries, item_details, opening_row, precision)
	return columns, data


def process_stock_ledger_entries(sl_entries, item_details, opening_row, precision):
	data = []

	if opening_row:
		data.append(opening_row)

	available_serial_nos = {}
	if sabb_list := [sle.serial_and_batch_bundle for sle in sl_entries if sle.serial_and_batch_bundle]:
		available_serial_nos = get_serial_nos_from_sle_list(sabb_list)

	if not available_serial_nos:
		return [], []

	for sle in sl_entries:
		update_stock_ledger_entry(sle, item_details, precision)
		update_available_serial_nos(available_serial_nos, sle)
		data.append(sle)

	return data


def update_stock_ledger_entry(sle, item_details, precision):
	item_detail = item_details[sle.item_code]
	sle.update(item_detail)

	sle.update({"in_qty": max(sle.actual_qty, 0), "out_qty": min(sle.actual_qty, 0)})

	if sle.actual_qty:
		sle["in_out_rate"] = flt(sle.stock_value_difference / sle.actual_qty, precision)
	elif sle.voucher_type == "Stock Reconciliation":
		sle["in_out_rate"] = sle.valuation_rate


def update_available_serial_nos(available_serial_nos, sle):
	serial_nos = (
		get_serial_nos(sle.serial_no)
		if sle.serial_no
		else available_serial_nos.get(sle.serial_and_batch_bundle)
	)
	key = (sle.item_code, sle.warehouse)
	sle.serial_no = "\n".join(serial_nos) if serial_nos else ""
	if key not in available_serial_nos:
		available_serial_nos.setdefault(key, serial_nos)
		sle.balance_serial_no = "\n".join(serial_nos)
		return

	existing_serial_no = available_serial_nos[key]
	for sn in serial_nos:
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
			"label": _("UOM"),
			"fieldname": "stock_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 60,
		},
	]

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
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 150,
			},
			{
				"label": _("Serial No (In/Out)"),
				"fieldname": "serial_no",
				"width": 150,
			},
			{"label": _("Balance Serial No"), "fieldname": "balance_serial_no", "width": 150},
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
				"fieldtype": filters.valuation_field_type,
				"width": 180,
				"options": "Company:company:default_currency"
				if filters.valuation_field_type == "Currency"
				else None,
				"convertible": "rate",
			},
			{
				"label": _("Valuation Rate"),
				"fieldname": "in_out_rate",
				"fieldtype": filters.valuation_field_type,
				"width": 140,
				"options": "Company:company:default_currency"
				if filters.valuation_field_type == "Currency"
				else None,
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
			{
				"label": _("Serial and Batch Bundle"),
				"fieldname": "serial_and_batch_bundle",
				"fieldtype": "Link",
				"options": "Serial and Batch Bundle",
				"width": 100,
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
				"label": _("Company"),
				"fieldname": "company",
				"fieldtype": "Link",
				"options": "Company",
				"width": 110,
			},
		]
	)

	return columns


def get_items(filters):
	item = frappe.qb.DocType("Item")
	query = frappe.qb.from_(item).select(item.name).where(item.has_serial_no == 1)

	if item_code := filters.get("item_code"):
		query = query.where(item.name == item_code)

	return query.run(pluck=True)
