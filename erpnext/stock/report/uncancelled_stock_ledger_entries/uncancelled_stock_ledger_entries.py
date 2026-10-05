# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from erpnext.stock.stock_ledger import set_as_cancel


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns() -> list[dict]:
	return [
		{
			"label": _("Stock Ledger Entry"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Stock Ledger Entry",
			"width": 180,
		},
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Link",
			"options": "DocType",
			"width": 150,
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 180,
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
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
			"label": _("Qty"),
			"fieldname": "actual_qty",
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"label": _("Stock Value Difference"),
			"fieldname": "stock_value_difference",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Uncancelled Serial and Batch Bundle"),
			"fieldname": "serial_and_batch_bundle",
			"fieldtype": "Link",
			"options": "Serial and Batch Bundle",
			"width": 180,
		},
	]


def get_data(filters) -> list[dict]:
	# SLEs that are still active (is_cancelled = 0) although their voucher is cancelled
	data = []
	for voucher_type in get_voucher_types(filters):
		data.extend(get_uncancelled_entries(voucher_type, filters))

	return sorted(data, key=lambda d: (d.posting_date, d.voucher_no))


def get_voucher_types(filters) -> list[str]:
	if filters.voucher_type:
		voucher_types = [filters.voucher_type]
	else:
		sle = frappe.qb.DocType("Stock Ledger Entry")
		query = frappe.qb.from_(sle).select(sle.voucher_type).distinct()
		voucher_types = [d[0] for d in apply_filters(query, sle, filters).run()]

	return [d for d in voucher_types if frappe.db.table_exists(d)]


def get_uncancelled_entries(voucher_type, filters) -> list[dict]:
	sle = frappe.qb.DocType("Stock Ledger Entry")
	voucher = frappe.qb.DocType(voucher_type)
	sabb = frappe.qb.DocType("Serial and Batch Bundle")

	query = (
		frappe.qb.from_(sle)
		.inner_join(voucher)
		.on(voucher.name == sle.voucher_no)
		.left_join(sabb)
		.on(
			(sabb.voucher_type == sle.voucher_type)
			& (sabb.voucher_no == sle.voucher_no)
			& (sabb.voucher_detail_no == sle.voucher_detail_no)
			& (sabb.item_code == sle.item_code)
			& (sabb.warehouse == sle.warehouse)
			& (sabb.docstatus == 1)
		)
		.select(
			sle.name,
			sle.voucher_type,
			sle.voucher_no,
			sle.posting_date,
			sle.item_code,
			sle.warehouse,
			sle.actual_qty,
			sle.stock_value_difference,
			sabb.name.as_("serial_and_batch_bundle"),
		)
		.where((sle.voucher_type == voucher_type) & (voucher.docstatus == 2))
	)

	return apply_filters(query, sle, filters).run(as_dict=True)


def apply_filters(query, sle, filters):
	query = query.where(sle.is_cancelled == 0)

	for field in ("company", "item_code", "warehouse"):
		if filters.get(field):
			query = query.where(sle[field] == filters.get(field))

	if filters.from_date:
		query = query.where(sle.posting_date >= filters.from_date)

	if filters.to_date:
		query = query.where(sle.posting_date <= filters.to_date)

	return query


@frappe.whitelist()
def fix_uncancelled_entries(selected_rows: str | list):
	frappe.has_permission("Stock Ledger Entry", "write", throw=True)

	if isinstance(selected_rows, str):
		selected_rows = frappe.parse_json(selected_rows)

	vouchers = {(row.get("voucher_type"), row.get("voucher_no")) for row in selected_rows}
	for voucher_type, voucher_no in vouchers:
		# re-check on the server, the client data could be stale
		if frappe.db.get_value(voucher_type, voucher_no, "docstatus") != 2:
			continue

		fix_voucher(voucher_type, voucher_no)

	frappe.msgprint(
		_("Stock Ledger Entries of the selected vouchers have been cancelled and reposting has been queued.")
	)


def fix_voucher(voucher_type, voucher_no):
	entries = frappe.get_all(
		"Stock Ledger Entry",
		filters={"voucher_type": voucher_type, "voucher_no": voucher_no, "is_cancelled": 0},
		fields=["item_code", "warehouse", "posting_date", "posting_time", "company"],
		order_by="posting_datetime asc, creation asc",
	)

	if not entries:
		return

	set_as_cancel(voucher_type, voucher_no)
	cancel_serial_and_batch_bundles(voucher_type, voucher_no)
	repost_future_entries(entries)


def cancel_serial_and_batch_bundles(voucher_type, voucher_no):
	# bundles of a different voucher type (POS Invoice, Asset Repair) are not cancelled with this voucher
	bundles = frappe.get_all(
		"Serial and Batch Bundle",
		filters={"voucher_type": voucher_type, "voucher_no": voucher_no, "docstatus": ["!=", 0]},
		or_filters={"is_cancelled": 0, "docstatus": 1},
		pluck="name",
	)

	if not bundles:
		return

	sabb = frappe.qb.DocType("Serial and Batch Bundle")
	frappe.qb.update(sabb).set(sabb.is_cancelled, 1).set(sabb.docstatus, 2).where(
		sabb.name.isin(bundles)
	).run()

	sabb_entry = frappe.qb.DocType("Serial and Batch Entry")
	frappe.qb.update(sabb_entry).set(sabb_entry.is_cancelled, 1).set(sabb_entry.docstatus, 2).where(
		sabb_entry.parent.isin(bundles)
	).run()

	# same as SerialandBatchBundle.before_cancel
	sle = frappe.qb.DocType("Stock Ledger Entry")
	frappe.qb.update(sle).set(sle.serial_and_batch_bundle, None).where(
		sle.serial_and_batch_bundle.isin(bundles)
	).run()


def repost_future_entries(entries):
	# the uncancelled entries were counted in the balances of the entries after them,
	# repost each item-warehouse from the earliest fixed entry to correct those
	from erpnext.controllers.stock_controller import create_repost_item_valuation_entry

	reposted = set()
	for sle in entries:
		key = (sle.item_code, sle.warehouse)
		if key in reposted:
			continue

		reposted.add(key)
		create_repost_item_valuation_entry(
			{
				"based_on": "Item and Warehouse",
				"item_code": sle.item_code,
				"warehouse": sle.warehouse,
				"posting_date": sle.posting_date,
				"posting_time": sle.posting_time,
				"company": sle.company,
			}
		)
