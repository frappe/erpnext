# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Read-side GL / Stock Ledger preview helpers.

A dry-run consumer of the posting path, shared across accounts and stock vouchers
(Sales/Purchase Invoice, Payment Entry, Delivery Note, Purchase Receipt, Stock
Entry): it submits-in-memory, reads the resulting GL/SLE entries and formats them
for the datatable preview, then rolls back. Lives separately from the posting
services it orchestrates. The whitelisted ``show_*_preview`` entry points stay on
``stock_controller`` (their dotted path is referenced from client JS).
"""

import frappe


def get_accounting_ledger_preview(doc, filters):
	from erpnext.accounts.report.general_ledger.general_ledger import get_columns as get_gl_columns

	gl_columns, gl_data = [], []
	fields = [
		"posting_date",
		"account",
		"debit",
		"credit",
		"against",
		"party_type",
		"party",
		"cost_center",
		"against_voucher_type",
		"against_voucher",
	]

	# Dry run: submit in memory to materialise GL entries, read them, then roll back
	# to the savepoint so the preview never persists anything, regardless of caller.
	frappe.db.savepoint("ledger_preview")
	try:
		doc.docstatus = 1

		if doc.get("update_stock") or doc.doctype in ("Purchase Receipt", "Delivery Note", "Stock Entry"):
			doc.update_stock_ledger()

		doc.make_gl_entries()
		columns = get_gl_columns(filters)
		gl_entries = get_gl_entries_for_preview(doc.doctype, doc.name, fields)

		gl_columns = get_columns(columns, fields)
		gl_data = get_data(fields, gl_entries)
	finally:
		frappe.db.rollback(save_point="ledger_preview")

	return gl_columns, gl_data


def get_stock_ledger_preview(doc, filters):
	from erpnext.stock.report.stock_ledger.stock_ledger import get_columns as get_sl_columns

	sl_columns, sl_data = [], []
	fields = [
		"item_code",
		"stock_uom",
		"actual_qty",
		"qty_after_transaction",
		"warehouse",
		"incoming_rate",
		"valuation_rate",
		"stock_value",
		"stock_value_difference",
	]
	columns_fields = [
		"item_code",
		"stock_uom",
		"in_qty",
		"out_qty",
		"qty_after_transaction",
		"warehouse",
		"incoming_rate",
		"in_out_rate",
		"stock_value",
		"stock_value_difference",
	]

	if doc.get("update_stock") or doc.doctype in ("Purchase Receipt", "Delivery Note", "Stock Entry"):
		# Dry run: submit in memory to materialise SLEs, read them, then roll back to
		# the savepoint so the preview never persists anything, regardless of caller.
		frappe.db.savepoint("ledger_preview")
		try:
			doc.docstatus = 1
			doc.make_bundle_using_old_serial_batch_fields()
			doc.update_stock_ledger()

			columns = get_sl_columns(filters)
			sl_entries = get_sl_entries_for_preview(doc.doctype, doc.name, fields)

			sl_columns = get_columns(columns, columns_fields)
			sl_data = get_data(columns_fields, sl_entries)
		finally:
			frappe.db.rollback(save_point="ledger_preview")

	return sl_columns, sl_data


def get_sl_entries_for_preview(doctype, docname, fields):
	sl_entries = frappe.get_all(
		"Stock Ledger Entry", filters={"voucher_type": doctype, "voucher_no": docname}, fields=fields
	)

	for entry in sl_entries:
		if entry.actual_qty > 0:
			entry["in_qty"] = entry.actual_qty
			entry["out_qty"] = 0
		else:
			entry["out_qty"] = abs(entry.actual_qty)
			entry["in_qty"] = 0

		entry["in_out_rate"] = entry["valuation_rate"]

	return sl_entries


def get_gl_entries_for_preview(doctype, docname, fields):
	return frappe.get_all("GL Entry", filters={"voucher_type": doctype, "voucher_no": docname}, fields=fields)


def get_columns(raw_columns, fields):
	return [
		{"name": d.get("label"), "editable": False, "width": 110, "fieldtype": d.get("fieldtype")}
		for d in raw_columns
		if not d.get("hidden") and d.get("fieldname") in fields
	]


def get_data(raw_columns, raw_data):
	datatable_data = []
	for row in raw_data:
		data_row = []
		for column in raw_columns:
			data_row.append(row.get(column) or "")

		datatable_data.append(data_row)

	return datatable_data
