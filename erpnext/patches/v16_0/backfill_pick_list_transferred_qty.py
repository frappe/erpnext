import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import flt


def execute():
	StockEntry = frappe.qb.DocType("Stock Entry")
	StockEntryDetail = frappe.qb.DocType("Stock Entry Detail")

	pick_lists = (
		frappe.qb.from_(StockEntry)
		.select(StockEntry.pick_list)
		.distinct()
		.where((StockEntry.pick_list.isnotnull()) & (StockEntry.docstatus == 1))
	).run(pluck=True)

	if not pick_lists:
		return

	rows = (
		frappe.qb.from_(StockEntryDetail)
		.join(StockEntry)
		.on(StockEntryDetail.parent == StockEntry.name)
		.select(
			StockEntry.pick_list,
			StockEntryDetail.item_code,
			StockEntryDetail.s_warehouse,
			Sum(StockEntryDetail.transfer_qty).as_("qty"),
		)
		.where((StockEntry.pick_list.isin(pick_lists)) & (StockEntry.docstatus == 1))
		.groupby(StockEntry.pick_list, StockEntryDetail.item_code, StockEntryDetail.s_warehouse)
	).run(as_dict=True)

	transferred = {(r.pick_list, r.item_code, r.s_warehouse): flt(r.qty) for r in rows}

	items = frappe.get_all(
		"Pick List Item",
		filters={"parent": ("in", pick_lists), "picked_qty": (">", 0)},
		fields=["name", "parent", "item_code", "warehouse", "picked_qty"],
		order_by="idx",
	)

	updates = {}
	for row in items:
		key = (row.parent, row.item_code, row.warehouse)
		available = transferred.get(key, 0)
		if available <= 0:
			continue
		qty = min(flt(row.picked_qty), available)
		transferred[key] = available - qty
		updates[row.name] = {"transferred_qty": qty}

	if not updates:
		return

	frappe.db.auto_commit_on_many_writes = True
	frappe.db.bulk_update("Pick List Item", updates)
	frappe.db.auto_commit_on_many_writes = False
