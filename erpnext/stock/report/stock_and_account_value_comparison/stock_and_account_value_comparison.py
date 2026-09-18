# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from datetime import date

import frappe
from frappe import _
from frappe.utils import create_batch, get_datetime, get_link_to_form, getdate, parse_json

import erpnext
from erpnext.accounts.utils import get_currency_precision, get_stock_accounts
from erpnext.stock.doctype.stock_reposting_settings.stock_reposting_settings import get_stock_ledgers
from erpnext.stock.doctype.warehouse.warehouse import get_warehouses_based_on_account


def execute(filters=None):
	if not erpnext.is_perpetual_inventory_enabled(filters.company):
		frappe.throw(
			_("Perpetual inventory required for the company {0} to view this report.").format(filters.company)
		)

	data = get_data(filters)
	columns = get_columns(filters)

	return columns, data


def get_data(report_filters):
	data = []

	filters = {
		"is_cancelled": 0,
		"company": report_filters.company,
		"posting_date": ("<=", report_filters.as_on_date),
	}

	get_currency_precision() or 2
	stock_ledger_entries = get_stock_ledger_data(report_filters, filters)
	voucher_wise_gl_data = get_gl_data(report_filters, filters)

	for d in stock_ledger_entries:
		key = (d.voucher_type, d.voucher_no)
		gl_data = voucher_wise_gl_data.get(key) or {}
		d.account_value = gl_data.get("account_value", 0)
		d.difference_value = d.stock_value - d.account_value
		d.ledger_type = "Stock Ledger Entry"
		if abs(d.difference_value) > 0.1:
			data.append(d)

		if key in voucher_wise_gl_data:
			del voucher_wise_gl_data[key]

	if voucher_wise_gl_data:
		data += get_gl_ledgers_with_no_stock_ledger_entries(voucher_wise_gl_data)

	return data


def get_gl_ledgers_with_no_stock_ledger_entries(voucher_wise_gl_data):
	data = []

	for key in voucher_wise_gl_data:
		gl_data = voucher_wise_gl_data.get(key) or {}
		data.append(
			{
				"name": gl_data.get("name"),
				"ledger_type": "GL Entry",
				"voucher_type": gl_data.get("voucher_type"),
				"voucher_no": gl_data.get("voucher_no"),
				"posting_date": gl_data.get("posting_date"),
				"stock_value": 0,
				"account_value": gl_data.get("account_value", 0),
				"difference_value": gl_data.get("account_value", 0) * -1,
			}
		)

	return data


def get_stock_ledger_data(report_filters, filters):
	if report_filters.account:
		warehouses = get_warehouses_based_on_account(report_filters.account, report_filters.company)

		filters["warehouse"] = ("in", warehouses)

	return frappe.get_all(
		"Stock Ledger Entry",
		filters=filters,
		fields=[
			"name",
			"voucher_type",
			"voucher_no",
			"sum(stock_value_difference) as stock_value",
			"posting_date",
			"posting_time",
		],
		group_by="voucher_type, voucher_no",
		order_by="posting_date ASC, posting_time ASC",
	)


def get_gl_data(report_filters, filters):
	if report_filters.account:
		stock_accounts = [report_filters.account]
	else:
		stock_accounts = get_stock_accounts(report_filters.company)

	filters.update({"account": ("in", stock_accounts)})

	if filters.get("warehouse"):
		del filters["warehouse"]

	gl_entries = frappe.get_all(
		"GL Entry",
		filters=filters,
		fields=[
			"name",
			"voucher_type",
			"voucher_no",
			"sum(debit_in_account_currency) - sum(credit_in_account_currency) as account_value",
			"posting_date",
		],
		group_by="voucher_type, voucher_no",
	)

	voucher_wise_gl_data = {}
	for d in gl_entries:
		key = (d.voucher_type, d.voucher_no)
		voucher_wise_gl_data[key] = d

	return voucher_wise_gl_data


def get_columns(filters):
	return [
		{
			"label": _("Stock Ledger ID"),
			"fieldname": "name",
			"fieldtype": "Dynamic Link",
			"options": "ledger_type",
			"width": "80",
		},
		{
			"label": _("Ledger Type"),
			"fieldname": "ledger_type",
			"fieldtype": "Data",
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date"},
		{"label": _("Posting Time"), "fieldname": "posting_time", "fieldtype": "Time"},
		{"label": _("Voucher Type"), "fieldname": "voucher_type", "width": "110"},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": "110",
		},
		{"label": _("Stock Value"), "fieldname": "stock_value", "fieldtype": "Currency", "width": "120"},
		{
			"label": _("Account Value"),
			"fieldname": "account_value",
			"fieldtype": "Currency",
			"width": "120",
		},
		{
			"label": _("Difference Value"),
			"fieldname": "difference_value",
			"fieldtype": "Currency",
			"width": "120",
		},
	]


@frappe.whitelist()
def create_reposting_entries(rows: str | list, company: str):
	if isinstance(rows, str):
		rows = parse_json(rows)

	entries = []

	item_wh = frappe._dict()
	vouchers = [
		row.get("voucher_no")
		for row in rows
		if row.get("voucher_type") not in ["Purchase Receipt", "Purchase Invoice"]
	]
	repost_based_on_transaction(rows, company, entries)

	sles = get_stock_ledgers(vouchers)
	for sle in sles:
		key = (sle.item_code, sle.warehouse)
		if key not in item_wh:
			item_wh[key] = sle
		elif get_datetime(item_wh.get(key).posting_datetime) > get_datetime(sle.posting_datetime):
			item_wh[key] = sle

	for key, sle in item_wh.items():
		item_code, warehouse = key
		try:
			doc = frappe.get_doc(
				{
					"doctype": "Repost Item Valuation",
					"based_on": "Item and Warehouse",
					"status": "Queued",
					"item_code": item_code,
					"warehouse": warehouse,
					"posting_date": sle.posting_date,
					"posting_time": sle.posting_time,
					"company": company,
					"allow_negative_stock": 1,
				}
			).submit()

			entries.append(get_link_to_form("Repost Item Valuation", doc.name))
		except frappe.DuplicateEntryError:
			pass

	if entries:
		entries = ", ".join(entries)
		frappe.msgprint(_("Reposting entries created: {0}").format(entries))


def repost_based_on_transaction(rows, company=None, entries=None):
	if entries is None:
		entries = []

	duplicate_vouchers = set()
	for row in rows:
		if (
			row.get("voucher_type") == "Purchase Invoice"
			and frappe.get_cached_value("Purchase Invoice", row.get("voucher_no"), "update_stock") == 0
		):
			continue

		if row.get("voucher_type") in ["Purchase Receipt", "Purchase Invoice"]:
			voucher_key = (row.get("voucher_type"), row.get("voucher_no"))
			if voucher_key in duplicate_vouchers:
				continue

			duplicate_vouchers.add(voucher_key)
			doc = frappe.get_doc(
				{
					"doctype": "Repost Item Valuation",
					"based_on": "Transaction",
					"status": "Queued",
					"voucher_type": row.get("voucher_type"),
					"voucher_no": row.get("voucher_no"),
					"posting_date": row.get("posting_date"),
					"posting_time": row.get("posting_time"),
					"company": company,
					"allow_negative_stock": 1,
					"recalculate_valuation_rate": 1,
				}
			).submit()

<<<<<<< HEAD
			entries.append(get_link_to_form("Repost Item Valuation", doc.name))
=======
				entries.append(get_link_to_form("Repost Item Valuation", doc.name))
			except frappe.DuplicateEntryError:
				frappe.db.rollback(save_point="repost_based_on_transaction")


@frappe.whitelist()
def create_gl_reposting_entries(rows: str | list, company: str, from_date: str | date | None = None):
	"""Repost only the accounting ledgers for the selected vouchers posted on or after `from_date`.

	Unlike `create_reposting_entries`, the stock ledgers and the valuation rates are left untouched.
	This is meant for the case where the stock valuation itself is correct but the General Ledger has
	drifted away from it, so there is no need to pay for a full (and much slower) revaluation.

	`from_date` bounds how far back the accounting ledgers are rewritten: selected rows posted before
	it are ignored, so a stale selection cannot reach into an already reconciled period.
	"""

	frappe.has_permission("Repost Item Valuation", "create", throw=True)

	if isinstance(rows, str):
		rows = parse_json(rows)

	if not rows:
		frappe.throw(_("Please select rows to create GL Reposting Entries"))

	if not from_date:
		frappe.throw(_("Please select the date to repost the accounting ledgers from"))

	from_date = getdate(from_date)

	entries = []
	processed_vouchers = set()

	# One batched lookup for the whole selection. Checking each row on its own meant a query per
	# row, which does not hold up when the report is used on the large selections it is meant for.
	pending_vouchers = get_pending_gl_reposting_vouchers(
		[(row.get("voucher_type"), row.get("voucher_no")) for row in rows]
	)

	for row in rows:
		# Rows posted before the From Date are skipped, so a stale selection cannot rewrite the
		# accounting ledgers of an already reconciled period.
		if getdate(row.get("posting_date")) < from_date:
			continue

		voucher_type, voucher_no = row.get("voucher_type"), row.get("voucher_no")

		# journal entry has not stock stock value, so no need to create a reposting entry for it
		if voucher_type == "Journal Entry":
			continue

		# Skip duplicate vouchers in the selection: a single reposting entry is enough to rewrite the accounting ledgers for a given voucher.
		if (voucher_type, voucher_no) in processed_vouchers:
			continue

		processed_vouchers.add((voucher_type, voucher_no))

		# A repost queued by an earlier run still has to rewrite this voucher, so queuing another one
		# now would just rebuild the same ledgers twice.
		if (voucher_type, voucher_no) in pending_vouchers:
			continue

		doc = frappe.get_doc(
			{
				"doctype": "Repost Item Valuation",
				"based_on": "Transaction",
				"status": "Queued",
				"voucher_type": voucher_type,
				"voucher_no": voucher_no,
				"posting_date": row.get("posting_date"),
				"posting_time": row.get("posting_time"),
				"company": company,
				"repost_only_accounting_ledgers": 1,
			}
		).submit()

		entries.append(get_link_to_form("Repost Item Valuation", doc.name))

	if entries:
		if len(entries) > 20:
			entries = entries[:20] + ["..."]

		frappe.msgprint(_("GL reposting entries created: {0}").format(", ".join(entries)))
	else:
		frappe.msgprint(_("No new GL reposting entries were created for the selected rows."))


def get_pending_gl_reposting_vouchers(transactions) -> set[tuple[str, str]]:
	"""Vouchers that already have a GL-only repost queued or running."""

	pending_vouchers = set()

	for chunk in create_batch(transactions, 1000):
		entries = frappe.get_all(
			"Repost Item Valuation",
			filters={
				"based_on": "Transaction",
				"repost_only_accounting_ledgers": 1,
				"docstatus": 1,
				"status": ("in", ["Queued", "In Progress"]),
				"voucher_no": ("in", [voucher_no for _, voucher_no in chunk]),
			},
			fields=["voucher_type", "voucher_no"],
		)

		pending_vouchers.update((d.voucher_type, d.voucher_no) for d in entries)

	return pending_vouchers
>>>>>>> c055faa (feat(stock): GL-only reposting from Stock and Account Value Comparison report (#59127))
