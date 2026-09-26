# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The stock ledger's values, entry by entry, against what they are expected to be.

The actual side is what each Stock Ledger Entry carries. The expected side comes from
erpnext.stock.expected_valuation, which replays the ledger with its own rules.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from erpnext.stock.expected_valuation import iterate_expected_valuations

SHOW_FIRST_DIFFERENCE = "First Difference per Item-Warehouse"
SHOW_ALL_DIFFERENCES = "All Differences"
SHOW_ALL_ENTRIES = "All Entries"

FLOAT_NOISE = 1e-9

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
	tolerance = get_default_tolerance() if filters.get("tolerance") in (None, "") else flt(filters.tolerance)

	item_warehouses = [(row.item_code, row.warehouse) for row in get_item_warehouses(filters)]

	data = []
	for item_code, warehouse, expected_valuation in iterate_expected_valuations(
		item_warehouses, to_date=filters.to_date
	):
		data.extend(get_rows_to_show(item_code, warehouse, expected_valuation, filters, tolerance))

	return data


def get_rows_to_show(
	item_code: str, warehouse: str, expected_valuation, filters, tolerance: float
) -> list[dict]:
	"""Compare the item-warehouse's ledger with its expected values.

	The replay has to start at the first entry, but it stops at To Date, and at the
	first difference when only that is to be shown.
	"""
	from_date = getdate(filters.from_date) if filters.from_date else None
	show = filters.show or SHOW_FIRST_DIFFERENCE

	rows = []
	for entry, expected in expected_valuation:
		if from_date and getdate(entry.posting_date) < from_date:
			continue

		row = make_comparison_row(item_code, warehouse, entry, expected, tolerance)
		if show == SHOW_ALL_ENTRIES or row.has_difference:
			rows.append(row)

		if show == SHOW_FIRST_DIFFERENCE and row.has_difference:
			break

	return rows


def make_comparison_row(item_code: str, warehouse: str, entry, expected, tolerance: float) -> dict:
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
	return row


def set_differences(row, tolerance: float) -> None:
	"""Fill in actual minus expected for every compared value, and flag the row if
	any of them is beyond the tolerance."""
	row.has_difference = 0

	for actual_field, expected_field, difference_field in COMPARED_VALUES:
		difference = flt(row[actual_field]) - flt(row[expected_field])

		# with nothing on hand there is no rate to compare
		if difference_field == "valuation_rate_difference" and not flt(row.expected_qty_after_transaction):
			difference = 0.0

		# even with no tolerance, float noise is not a difference
		if abs(difference) < max(tolerance, FLOAT_NOISE):
			difference = 0.0

		row[difference_field] = difference
		if difference:
			row.has_difference = 1


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
