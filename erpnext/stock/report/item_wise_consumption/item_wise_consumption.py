# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import IfNull
from frappe.utils import flt

SALES_VOUCHER_TYPES = ("Delivery Note", "Sales Invoice")
PURCHASE_VOUCHER_TYPES = ("Purchase Receipt", "Purchase Invoice")


def execute(filters=None):
	columns = get_columns(filters)
	consumed_details = get_consumed_details(filters)
	supplier_details = get_suppliers_details(filters)
	data = []

	for item_code, entries in consumed_details.items():
		if filters.get("supplier") and item_code not in supplier_details:
			continue

		if row := get_item_row(entries, supplier_details.get(item_code, [])):
			data.append(row)

	return columns, data


def get_item_row(entries, suppliers):
	consumed_qty = consumed_amount = delivered_qty = delivered_amount = 0.0
	for cd in entries:
		if cd.voucher_type in SALES_VOUCHER_TYPES:
			delivered_qty -= flt(cd.actual_qty)
			delivered_amount -= flt(cd.stock_value_difference)
		elif cd.voucher_type not in PURCHASE_VOUCHER_TYPES:
			consumed_qty -= flt(cd.actual_qty)
			consumed_amount -= flt(cd.stock_value_difference)

	if not (consumed_qty or consumed_amount or delivered_qty or delivered_amount):
		return

	cd = entries[0]
	return [
		cd.item_code,
		cd.item_name,
		cd.description,
		cd.stock_uom,
		consumed_qty,
		consumed_amount,
		delivered_qty,
		delivered_amount,
		delivered_qty + consumed_qty,
		delivered_amount + consumed_amount,
		",".join(set(suppliers)),
	]


def get_columns(filters):
	"""return columns based on filters"""

	columns = [
		_("Item") + ":Link/Item:100",
		_("Item Name") + "::100",
		_("Description") + "::150",
		_("UOM") + ":Link/UOM:90",
		_("Consumed Qty") + ":Float:110",
		_("Consumed Amount") + ":Currency:130",
		_("Delivered Qty") + ":Float:110",
		_("Delivered Amount") + ":Currency:130",
		_("Total Qty") + ":Float:110",
		_("Total Amount") + ":Currency:130",
		_("Supplier(s)") + "::250",
	]

	return columns


def get_consumed_details(filters):
	item = frappe.qb.DocType("Item")
	sle = frappe.qb.DocType("Stock Ledger Entry")

	query = (
		frappe.qb.from_(sle)
		.from_(item)
		.select(
			sle.item_code,
			item.item_name,
			item.description,
			item.stock_uom,
			sle.actual_qty,
			sle.stock_value_difference,
			sle.voucher_no,
			sle.voucher_type,
			sle.voucher_detail_no,
		)
		# the stock an Adjustment Entry counts out comes back in, it is not consumed
		.where(
			(sle.is_cancelled == 0)
			& (sle.item_code == item.name)
			& ((sle.actual_qty < 0) | (sle.voucher_type.isin(SALES_VOUCHER_TYPES)))
			& (sle.is_adjustment_entry == 0)
		)
	)

	if filters.get("from_date") and filters.get("to_date"):
		query = query.where(
			(sle.posting_date >= filters.get("from_date")) & (sle.posting_date <= filters.get("to_date"))
		)

	entries = query.run(as_dict=True)
	transfer_rows = get_stock_entry_transfer_rows(entries)

	consumed_details = {}
	for d in entries:
		if d.voucher_detail_no not in transfer_rows:
			consumed_details.setdefault(d.item_code, []).append(d)

	return consumed_details


def get_stock_entry_transfer_rows(entries):
	names = [d.voucher_detail_no for d in entries if d.voucher_type == "Stock Entry" and d.voucher_detail_no]
	if not names:
		return set()

	detail = frappe.qb.DocType("Stock Entry Detail")
	return set(
		frappe.qb.from_(detail)
		.select(detail.name)
		.where(
			(detail.name.isin(names))
			& (IfNull(detail.s_warehouse, "") != "")
			& (IfNull(detail.t_warehouse, "") != "")
		)
		.run(pluck=True)
	)


def get_suppliers_details(filters):
	item_supplier_map = {}
	supplier = filters.get("supplier")

	item = frappe.qb.DocType("Item")
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")

	query = (
		frappe.qb.from_(pr)
		.from_(pr_item)
		.select(pr.supplier, pr_item.item_code)
		.where(
			(pr.name == pr_item.parent)
			& (pr.docstatus == 1)
			& (
				pr_item.item_code
				== (
					frappe.qb.from_(item)
					.select(item.name)
					.where((item.is_stock_item == 1) & (item.name == pr_item.item_code))
				)
			)
		)
	)

	for d in query.run(as_dict=True):
		item_supplier_map.setdefault(d.item_code, []).append(d.supplier)

	pi = frappe.qb.DocType("Purchase Invoice")
	pi_item = frappe.qb.DocType("Purchase Invoice Item")

	query = (
		frappe.qb.from_(pi)
		.from_(pi_item)
		.select(pi.supplier, pi_item.item_code)
		.where(
			(pi.name == pi_item.parent)
			& (pi.docstatus == 1)
			& (IfNull(pi.update_stock, 0) == 1)
			& (
				pi_item.item_code
				== (
					frappe.qb.from_(item)
					.select(item.name)
					.where((item.is_stock_item == 1) & (item.name == pi_item.item_code))
				)
			)
		)
	)

	for d in query.run(as_dict=True):
		if d.item_code not in item_supplier_map:
			item_supplier_map.setdefault(d.item_code, []).append(d.supplier)

	if supplier:
		invalid_items = []
		for item_code, suppliers in item_supplier_map.items():
			if supplier not in suppliers:
				invalid_items.append(item_code)

		for item_code in invalid_items:
			del item_supplier_map[item_code]

	return item_supplier_map
