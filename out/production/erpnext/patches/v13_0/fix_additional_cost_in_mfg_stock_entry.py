from typing import List, NewType

import frappe

StockEntryCode = NewType("StockEntryCode", str)


def execute():
	stock_entry_codes = find_broken_stock_entries()

	for stock_entry_code in stock_entry_codes:
		patched_stock_entry = patch_additional_cost(stock_entry_code)
		create_repost_item_valuation(patched_stock_entry)


def find_broken_stock_entries() -> List[StockEntryCode]:
	period_closing_date = frappe.db.get_value(
		"Period Closing Voucher", {"docstatus": 1}, "posting_date", order_by="posting_date desc"
	)

	stock_entries_to_patch = frappe.db.sql(
		"""
		select se.name, sum(sed.additional_cost) as item_additional_cost, se.total_additional_costs
		from `tabStock Entry` se
		join `tabStock Entry Detail` sed
			on sed.parent = se.name
		where
			se.docstatus = 1 and
			se.posting_date > %s
		group by
			sed.parent
		having
			item_additional_cost != se.total_additional_costs
	""",
		period_closing_date,
		as_dict=True,
	)

	return [d.name for d in stock_entries_to_patch]


def patch_additional_cost(code: StockEntryCode):
	stock_entry = frappe.get_doc("Stock Entry", code)
	stock_entry.distribute_additional_costs()
	stock_entry.update_valuation_rate()
	stock_entry.set_total_incoming_outgoing_value()
	stock_entry.set_total_amount()
	stock_entry.db_update()
	for item in stock_entry.items:
		item.db_update()
	return stock_entry


def create_repost_item_valuation(stock_entry):
	from erpnext.controllers.stock_controller import create_repost_item_valuation_entry

	# turn on recalculate flag so reposting corrects the incoming/outgoing rates.
	frappe.db.set_value(
		"Stock Ledger Entry",
		{"voucher_no": stock_entry.name, "actual_qty": (">", 0)},
		"recalculate_rate",
		1,
		update_modified=False,
	)

	create_repost_item_valuation_entry(
		args=frappe._dict(
			{
				"posting_date": stock_entry.posting_date,
				"posting_time": stock_entry.posting_time,
				"voucher_type": stock_entry.doctype,
				"voucher_no": stock_entry.name,
				"company": stock_entry.company,
			}
		)
	)
