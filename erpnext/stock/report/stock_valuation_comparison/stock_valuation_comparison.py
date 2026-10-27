# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The stock ledger's values, entry by entry, against what they are expected to be.

The actual side is what each Stock Ledger Entry carries. The expected side comes from
erpnext.stock.expected_valuation, which replays the ledger with its own rules.

A difference can be settled from here in two ways: by reposting the item-warehouse from it, or
by an Adjustment Entry (erpnext.stock.valuation_adjustment) on a later date. A difference before
an Adjustment Entry is left in the ledger, so it is hidden unless asked for.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, nowdate

from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.expected_valuation import iterate_expected_valuations
from erpnext.stock.report.stock_ledger_entries_of_cancelled_vouchers.stock_ledger_entries_of_cancelled_vouchers import (
	get_allowed_values,
	validate_company_permission,
)
from erpnext.stock.utils import get_combine_datetime
from erpnext.stock.valuation_adjustment import get_adjusted_until
from erpnext.stock.valuation_adjustment import make_adjustment_entry as make_draft_adjustment_entry

SHOW_FIRST_DIFFERENCE = "First Difference per Item-Warehouse"
SHOW_ALL_DIFFERENCES = "All Differences"
SHOW_ALL_ENTRIES = "All Entries"

FLOAT_NOISE = 1e-9

PENDING_REPOST_STATUSES = ("Queued", "In Progress")

# (actual field, expected field, difference field) compared on every entry
COMPARED_VALUES = (
	("qty_after_transaction", "expected_qty_after_transaction", "qty_difference"),
	("stock_value_difference", "expected_stock_value_difference", "stock_value_difference_difference"),
	("valuation_rate", "expected_valuation_rate", "valuation_rate_difference"),
	("stock_value", "expected_stock_value", "stock_value_difference_in_balance"),
)
DIFFERENCE_FIELDS = [difference_field for _actual, _expected, difference_field in COMPARED_VALUES]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.company:
		frappe.throw(_("Please select a Company"))

	validate_company_permission(filters.company)

	return get_columns(), get_data(filters)


def get_data(filters) -> list[dict]:
	tolerance = get_default_tolerance() if filters.get("tolerance") in (None, "") else flt(filters.tolerance)

	item_warehouses = [(row.item_code, row.warehouse) for row in get_item_warehouses(filters)]
	adjusted_until = get_adjusted_until(item_warehouses, filters.to_date)
	pending_reposts = get_pending_reposts(item_warehouses)

	data = []
	for item_code, warehouse, expected_valuation in iterate_expected_valuations(
		item_warehouses, to_date=filters.to_date
	):
		rows = get_rows_to_show(
			item_code,
			warehouse,
			expected_valuation,
			filters,
			tolerance,
			adjusted_until.get((item_code, warehouse)),
		)
		for row in rows:
			row.pending_repost = pending_reposts.get((item_code, warehouse))

		data.extend(rows)

	return data


def get_rows_to_show(
	item_code: str, warehouse: str, expected_valuation, filters, tolerance: float, adjustment=None
) -> list[dict]:
	"""Compare the item-warehouse's ledger with its expected values.

	The replay has to start at the first entry, but it stops at To Date, and at the
	first difference when only that is to be shown. A difference before the item-warehouse's
	latest Adjustment Entry was settled by it, and counts only when settled ones are asked for.
	"""
	from_date = getdate(filters.from_date) if filters.from_date else None
	show = filters.show or SHOW_FIRST_DIFFERENCE

	rows = []
	for entry, expected in expected_valuation:
		if from_date and getdate(entry.posting_date) < from_date:
			continue

		row = make_comparison_row(item_code, warehouse, entry, expected, tolerance)
		if (
			row.has_difference
			and adjustment
			and get_datetime(entry.posting_datetime) < adjustment.posting_datetime
		):
			row.adjusted_by = adjustment.voucher_no
			if not filters.show_adjusted_differences:
				row.has_difference = 0
				if show == SHOW_ALL_ENTRIES:
					row.update(dict.fromkeys(DIFFERENCE_FIELDS, 0.0))

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

	allowed_values = get_allowed_values()
	for field in ("item_code", "warehouse"):
		if allowed_values.get(field):
			query = query.where(bin[field].isin(allowed_values[field]))

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
			"fieldname": "adjusted_by",
			"fieldtype": "Link",
			"label": _("Adjusted By"),
			"options": "Stock Reconciliation",
			"width": 150,
		},
		{
			"fieldname": "pending_repost",
			"fieldtype": "Link",
			"label": _("Pending Repost"),
			"options": "Repost Item Valuation",
			"width": 150,
		},
		{
			"fieldname": "stock_ledger_entry",
			"fieldtype": "Link",
			"label": _("Stock Ledger Entry"),
			"options": "Stock Ledger Entry",
			"width": 150,
		},
	]


def get_pending_reposts(item_warehouses: list[tuple[str, str]]) -> dict[tuple[str, str], str]:
	"""The queued or running Repost Item Valuation of each item-warehouse, if it has one."""
	if not item_warehouses:
		return {}

	pending = {}
	for repost in frappe.get_all(
		"Repost Item Valuation",
		filters={
			"docstatus": 1,
			"status": ("in", PENDING_REPOST_STATUSES),
			"based_on": "Item and Warehouse",
			"item_code": ("in", list({item_code for item_code, _warehouse in item_warehouses})),
		},
		fields=["name", "item_code", "warehouse", "posting_date", "posting_time"],
		order_by="posting_date asc, posting_time asc",
	):
		pending.setdefault((repost.item_code, repost.warehouse), repost)

	return {key: repost.name for key, repost in pending.items()}


def get_differences_to_fix(company: str, stock_ledger_entries) -> dict[tuple[str, str], frappe._dict]:
	"""The earliest of the given entries of each item-warehouse, which is where fixing it starts."""
	stock_ledger_entries = frappe.parse_json(stock_ledger_entries) or []
	if not stock_ledger_entries:
		frappe.throw(_("Select the differences to fix."))

	validate_company_permission(company)

	# only the entries of the items and warehouses the user is permitted
	filters = {"name": ("in", stock_ledger_entries), "company": company, "is_cancelled": 0}
	for field, values in get_allowed_values().items():
		if field in ("item_code", "warehouse"):
			filters[field] = ("in", values)

	first_differences = {}
	for entry in frappe.get_all(
		"Stock Ledger Entry",
		filters=filters,
		fields=["name", "item_code", "warehouse", "posting_date", "posting_time", "posting_datetime"],
		order_by="posting_datetime asc, creation asc",
	):
		first_differences.setdefault((entry.item_code, entry.warehouse), entry)

	return first_differences


@frappe.whitelist()
def get_repost_preview(company: str, stock_ledger_entries: str | list) -> list[dict]:
	"""What reposting the differences would do: one repost per item-warehouse from its first
	difference, unless one is already pending, and which of them reach into a past fiscal year."""
	frappe.has_permission("Repost Item Valuation", "create", throw=True)

	first_differences = get_differences_to_fix(company, stock_ledger_entries)
	pending_reposts = get_pending_reposts(list(first_differences))
	current_fiscal_year_start = get_fiscal_year(nowdate(), company=company, boolean=True)

	preview = []
	for (item_code, warehouse), entry in first_differences.items():
		fiscal_year = get_fiscal_year(entry.posting_date, company=company, boolean=True)
		preview.append(
			{
				"item_code": item_code,
				"warehouse": warehouse,
				"posting_date": entry.posting_date,
				"posting_time": entry.posting_time,
				"fiscal_year": fiscal_year[0] if fiscal_year else None,
				"is_past_fiscal_year": bool(
					current_fiscal_year_start and getdate(entry.posting_date) < current_fiscal_year_start[1]
				),
				"pending_repost": pending_reposts.get((item_code, warehouse)),
			}
		)

	return preview


@frappe.whitelist(methods=["POST"])
def make_repost_entries(company: str, stock_ledger_entries: str | list) -> dict:
	"""A Repost Item Valuation per item-warehouse from its first difference, unless one is
	already pending. One that cannot be made, say for a closed period, does not stop the rest."""
	frappe.has_permission("Repost Item Valuation", "create", throw=True)
	frappe.has_permission("Repost Item Valuation", "submit", throw=True)

	created, not_created = [], []
	for row in get_repost_preview(company, stock_ledger_entries):
		if row["pending_repost"]:
			not_created.append(
				{**row, "reason": _("Repost {0} is already pending.").format(row["pending_repost"])}
			)
			continue

		frappe.db.savepoint("repost_item_valuation")
		try:
			repost = frappe.get_doc(
				{
					"doctype": "Repost Item Valuation",
					"based_on": "Item and Warehouse",
					"company": company,
					"item_code": row["item_code"],
					"warehouse": row["warehouse"],
					"posting_date": row["posting_date"],
					"posting_time": row["posting_time"],
				}
			)
			repost.insert()
			repost.submit()
			created.append({**row, "repost": repost.name})
		except frappe.ValidationError as e:
			frappe.db.rollback(save_point="repost_item_valuation")
			frappe.clear_messages()
			not_created.append({**row, "reason": str(e)})

	return {"created": created, "not_created": not_created}


@frappe.whitelist(methods=["POST"])
def make_adjustment_entry(
	company: str,
	stock_ledger_entries: str | list,
	posting_date: str,
	posting_time: str,
	expense_account: str | None = None,
) -> dict:
	"""A draft Adjustment Entry that settles the differences of the item-warehouses on the given
	date, and why the others cannot be settled by it."""
	frappe.has_permission("Stock Reconciliation", "create", throw=True)

	adjustment_datetime = get_combine_datetime(posting_date, posting_time)
	first_differences = get_differences_to_fix(company, stock_ledger_entries)

	not_adjusted = []
	item_warehouses = []
	for (item_code, warehouse), entry in first_differences.items():
		if get_datetime(entry.posting_datetime) >= get_datetime(adjustment_datetime):
			not_adjusted.append(
				{
					"item_code": item_code,
					"warehouse": warehouse,
					"reason": _("Its difference on {0} is not before the adjustment date.").format(
						frappe.format(entry.posting_date, "Date")
					),
				}
			)
		else:
			item_warehouses.append((item_code, warehouse))

	doc, plans = make_draft_adjustment_entry(
		company, item_warehouses, posting_date, posting_time, expense_account=expense_account
	)

	for item_code, warehouse in item_warehouses:
		plan = plans.get((item_code, warehouse))
		if not plan or plan.reason:
			not_adjusted.append(
				{
					"item_code": item_code,
					"warehouse": warehouse,
					"reason": plan.reason if plan else _("It has no stock transactions by then."),
				}
			)

	return {"adjustment_entry": doc.name if doc.items else None, "not_adjusted": not_adjusted}
