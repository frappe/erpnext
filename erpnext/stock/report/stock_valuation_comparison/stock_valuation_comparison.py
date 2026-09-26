# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The stock ledger's values, entry by entry, against what they are expected to be.

The actual side is what each Stock Ledger Entry carries. The expected side comes from
erpnext.stock.expected_valuation, which replays the ledger with its own rules.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from erpnext.stock.expected_valuation import get_expected_valuation

SHOW_FIRST_DIFFERENCE = "First Difference per Item-Warehouse"
SHOW_ALL_DIFFERENCES = "All Differences"
SHOW_ALL_ENTRIES = "All Entries"

# (actual field, expected field, difference field) compared on every entry
COMPARED_VALUES = (
	("qty_after_transaction", "expected_qty_after_transaction", "qty_difference"),
	("stock_value_difference", "expected_stock_value_difference", "stock_value_difference_difference"),
	("valuation_rate", "expected_valuation_rate", "valuation_rate_difference"),
	("stock_value", "expected_stock_value", "stock_value_difference_in_balance"),
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.company:
		frappe.throw(_("Please select a Company"))

	return get_columns(), get_data(filters)


def get_data(filters) -> list[dict]:
	tolerance = flt(filters.tolerance) or get_default_tolerance()

	data = []
	for item_warehouse in get_item_warehouses(filters):
		rows = compare_ledger_with_expected(item_warehouse.item_code, item_warehouse.warehouse, tolerance)
		data.extend(pick_rows_to_show(rows, filters))

	return data


def compare_ledger_with_expected(item_code: str, warehouse: str, tolerance: float) -> list[dict]:
	rows = []
	for entry, expected in get_expected_valuation(item_code, warehouse):
		row = frappe._dict(
			{
				"stock_ledger_entry": entry.name,
				"posting_date": entry.posting_date,
				"posting_time": entry.posting_time,
				"item_code": item_code,
				"warehouse": warehouse,
				"voucher_type": entry.voucher_type,
				"voucher_no": entry.voucher_no,
				"serial_and_batch_bundle": entry.serial_and_batch_bundle,
				"batch_no": entry.batch_no,
				"actual_qty": entry.actual_qty,
				"qty_after_transaction": entry.qty_after_transaction,
				"stock_value_difference": entry.stock_value_difference,
				"valuation_rate": entry.valuation_rate,
				"stock_value": entry.stock_value,
				"expected_qty_after_transaction": expected.qty_after_transaction,
				"expected_stock_value_difference": expected.stock_value_difference,
				"expected_valuation_rate": expected.valuation_rate,
				"expected_stock_value": expected.stock_value,
				"expected_basis": expected.basis,
			}
		)

		set_differences(row, tolerance)
		rows.append(row)

	return rows


def set_differences(row, tolerance: float) -> None:
	"""Fill in actual minus expected for every compared value, and flag the row if
	any of them is beyond the tolerance."""
	row.has_difference = 0

	for actual_field, expected_field, difference_field in COMPARED_VALUES:
		difference = flt(row[actual_field]) - flt(row[expected_field])

		# with nothing on hand there is no rate to compare
		if difference_field == "valuation_rate_difference" and not flt(row.expected_qty_after_transaction):
			difference = 0.0

		if abs(difference) < tolerance:
			difference = 0.0

		row[difference_field] = difference
		if difference:
			row.has_difference = 1


def pick_rows_to_show(rows: list[dict], filters) -> list[dict]:
	from_date = getdate(filters.from_date) if filters.from_date else None
	to_date = getdate(filters.to_date) if filters.to_date else None

	rows = [
		row
		for row in rows
		if (not from_date or getdate(row.posting_date) >= from_date)
		and (not to_date or getdate(row.posting_date) <= to_date)
	]

	show = filters.show or SHOW_FIRST_DIFFERENCE
	if show == SHOW_ALL_ENTRIES:
		return rows

	rows_with_difference = [row for row in rows if row.has_difference]
	if show == SHOW_ALL_DIFFERENCES:
		return rows_with_difference

	return rows_with_difference[:1]


def get_item_warehouses(filters) -> list[dict]:
	bin = frappe.qb.DocType("Bin")
	item = frappe.qb.DocType("Item")
	warehouse = frappe.qb.DocType("Warehouse")

	query = (
		frappe.qb.from_(bin)
		.inner_join(item)
		.on(bin.item_code == item.name)
		.inner_join(warehouse)
		.on(bin.warehouse == warehouse.name)
		.select(bin.item_code, bin.warehouse)
		.where((item.is_stock_item == 1) & (warehouse.company == filters.company))
		.orderby(bin.item_code)
		.orderby(bin.warehouse)
	)

	if filters.item_code:
		query = query.where(item.name == filters.item_code)

	if filters.item_group:
		item_group = frappe.db.get_value("Item Group", filters.item_group, ["lft", "rgt"], as_dict=True)
		item_groups = frappe.get_all(
			"Item Group",
			filters={"lft": (">=", item_group.lft), "rgt": ("<=", item_group.rgt)},
			pluck="name",
		)
		query = query.where(item.item_group.isin(item_groups))

	if filters.warehouse:
		parent = frappe.db.get_value("Warehouse", filters.warehouse, ["lft", "rgt"], as_dict=True)
		query = query.where((warehouse.lft >= parent.lft) & (warehouse.rgt <= parent.rgt))

	return query.run(as_dict=True)


def get_default_tolerance() -> float:
	currency_precision = cint(frappe.db.get_single_value("System Settings", "currency_precision")) or 2
	return 1.0 / 10**currency_precision


def get_columns() -> list[dict]:
	return [
		{
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"label": _("Posting Date"),
			"width": 100,
		},
		{
			"fieldname": "posting_time",
			"fieldtype": "Time",
			"label": _("Posting Time"),
			"width": 90,
		},
		{
			"fieldname": "item_code",
			"fieldtype": "Link",
			"label": _("Item"),
			"options": "Item",
			"width": 140,
		},
		{
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"label": _("Warehouse"),
			"options": "Warehouse",
			"width": 140,
		},
		{
			"fieldname": "voucher_type",
			"fieldtype": "Link",
			"label": _("Voucher Type"),
			"options": "DocType",
			"width": 130,
		},
		{
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"label": _("Voucher No"),
			"options": "voucher_type",
			"width": 150,
		},
		{
			"fieldname": "serial_and_batch_bundle",
			"fieldtype": "Link",
			"label": _("Serial and Batch Bundle"),
			"options": "Serial and Batch Bundle",
			"width": 150,
		},
		{
			"fieldname": "actual_qty",
			"fieldtype": "Float",
			"label": _("Qty Change"),
			"width": 100,
		},
		{
			"fieldname": "qty_after_transaction",
			"fieldtype": "Float",
			"label": _("(A) Balance Qty"),
			"width": 120,
		},
		{
			"fieldname": "expected_qty_after_transaction",
			"fieldtype": "Float",
			"label": _("(B) Expected Balance Qty"),
			"width": 120,
		},
		{
			"fieldname": "qty_difference",
			"fieldtype": "Float",
			"label": _("A - B"),
			"width": 90,
		},
		{
			"fieldname": "stock_value_difference",
			"fieldtype": "Currency",
			"label": _("(C) Change in Stock Value"),
			"width": 140,
		},
		{
			"fieldname": "expected_stock_value_difference",
			"fieldtype": "Currency",
			"label": _("(D) Expected Change in Stock Value"),
			"width": 140,
		},
		{
			"fieldname": "stock_value_difference_difference",
			"fieldtype": "Currency",
			"label": _("C - D"),
			"width": 110,
		},
		{
			"fieldname": "valuation_rate",
			"fieldtype": "Currency",
			"label": _("(E) Valuation Rate"),
			"width": 120,
		},
		{
			"fieldname": "expected_valuation_rate",
			"fieldtype": "Currency",
			"label": _("(F) Expected Valuation Rate"),
			"width": 120,
		},
		{
			"fieldname": "valuation_rate_difference",
			"fieldtype": "Currency",
			"label": _("E - F"),
			"width": 110,
		},
		{
			"fieldname": "stock_value",
			"fieldtype": "Currency",
			"label": _("(G) Balance Stock Value"),
			"width": 140,
		},
		{
			"fieldname": "expected_stock_value",
			"fieldtype": "Currency",
			"label": _("(H) Expected Balance Stock Value"),
			"width": 140,
		},
		{
			"fieldname": "stock_value_difference_in_balance",
			"fieldtype": "Currency",
			"label": _("G - H"),
			"width": 110,
		},
		{
			"fieldname": "expected_basis",
			"fieldtype": "Data",
			"label": _("Expected Value Based On"),
			"width": 200,
		},
		{
			"fieldname": "stock_ledger_entry",
			"fieldtype": "Link",
			"label": _("Stock Ledger Entry"),
			"options": "Stock Ledger Entry",
			"width": 150,
		},
	]
