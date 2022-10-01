# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import cint, cstr, flt

from erpnext.controllers.stock_controller import create_repost_item_valuation_entry
from erpnext.stock.stock_ledger import make_sl_entries


def execute():
	if not frappe.db.has_column("Work Order", "has_batch_no"):
		return

	frappe.reload_doc("manufacturing", "doctype", "manufacturing_settings")
	if cint(
		frappe.db.get_single_value("Manufacturing Settings", "make_serial_no_batch_from_work_order")
	):
		return

	frappe.reload_doc("manufacturing", "doctype", "work_order")
	filters = {
		"docstatus": 1,
		"produced_qty": (">", 0),
		"creation": (">=", "2021-06-29 00:00:00"),
		"has_batch_no": 1,
	}

	fields = ["name", "production_item"]

	work_orders = [d.name for d in frappe.get_all("Work Order", filters=filters, fields=fields)]

	if not work_orders:
		return

	repost_stock_entries = []

	stock_entries = frappe.db.sql_list(
		"""
		SELECT
			se.name
		FROM
			`tabStock Entry` se
		WHERE
			se.purpose = 'Manufacture' and se.docstatus < 2 and se.work_order in %s
			and not exists(
				select name from `tabStock Entry Detail` sed where sed.parent = se.name and sed.is_finished_item = 1
			)
		ORDER BY
			se.posting_date, se.posting_time
	""",
		(work_orders,),
	)

	if stock_entries:
		print("Length of stock entries", len(stock_entries))

	for stock_entry in stock_entries:
		doc = frappe.get_doc("Stock Entry", stock_entry)
		doc.set_work_order_details()
		doc.load_items_from_bom()
		doc.calculate_rate_and_amount()
		set_expense_account(doc)
		doc.make_batches("t_warehouse")

		if doc.docstatus == 0:
			doc.save()
		else:
			repost_stock_entry(doc)
			repost_stock_entries.append(doc)

	for repost_doc in repost_stock_entries:
		repost_future_sle_and_gle(repost_doc)


def set_expense_account(doc):
	for row in doc.items:
		if row.is_finished_item and not row.expense_account:
			row.expense_account = frappe.get_cached_value(
				"Company", doc.company, "stock_adjustment_account"
			)


def repost_stock_entry(doc):
	doc.db_update()
	for child_row in doc.items:
		if child_row.is_finished_item:
			child_row.db_update()

	sl_entries = []
	finished_item_row = doc.get_finished_item_row()
	get_sle_for_target_warehouse(doc, sl_entries, finished_item_row)

	if sl_entries:
		try:
			make_sl_entries(sl_entries, True)
		except Exception:
			print(f"SLE entries not posted for the stock entry {doc.name}")
			traceback = frappe.get_traceback()
			frappe.log_error(traceback)


def get_sle_for_target_warehouse(doc, sl_entries, finished_item_row):
	for d in doc.get("items"):
		if cstr(d.t_warehouse) and finished_item_row and d.name == finished_item_row.name:
			sle = doc.get_sl_entries(
				d,
				{
					"warehouse": cstr(d.t_warehouse),
					"actual_qty": flt(d.transfer_qty),
					"incoming_rate": flt(d.valuation_rate),
				},
			)

			sle.recalculate_rate = 1
			sl_entries.append(sle)


def repost_future_sle_and_gle(doc):
	args = frappe._dict(
		{
			"posting_date": doc.posting_date,
			"posting_time": doc.posting_time,
			"voucher_type": doc.doctype,
			"voucher_no": doc.name,
			"company": doc.company,
		}
	)

	create_repost_item_valuation_entry(args)
