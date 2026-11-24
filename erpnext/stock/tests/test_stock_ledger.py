# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestRepostQueue(ERPNextTestSuite):
	def test_entries_pop_in_posting_order_with_ties_in_insertion_order(self):
		from erpnext.stock.stock_ledger import RepostQueue

		def entry(name, posting_datetime, creation="2026-01-01 10:00:00"):
			return frappe._dict(name=name, posting_datetime=posting_datetime, creation=creation)

		queue = RepostQueue([entry("a", "2026-01-02 00:00:01"), entry("b", "2026-01-04 00:00:01")])
		queue.extend(
			[
				entry("c", "2026-01-01 00:00:01"),
				entry("d", "2026-01-02 00:00:01"),
				entry("e", "2026-01-02 00:00:01", creation="2026-01-01 09:00:00"),
			]
		)

		self.assertEqual([row.name for row in queue.peek(2)], ["c", "e"])
		self.assertEqual(len(queue), 5)
		self.assertEqual([queue.popleft().name for _ in range(len(queue))], ["c", "e", "a", "d", "b"])

	def test_repost_fetches_each_entry_once_when_dependants_join_the_queue(self):
		from unittest.mock import patch

		from frappe.utils import add_days, nowdate

		import erpnext.stock.stock_ledger as stock_ledger
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item("_Test Repost Batch Fetch Item", {"is_stock_item": 1}).name
		source, target = "_Test Warehouse - _TC", "_Test Warehouse 1 - _TC"
		make_stock_entry(
			item_code=item, target=source, qty=10, basic_rate=100, posting_date=add_days(nowdate(), -3)
		)
		for days in (-2, -1):
			make_stock_entry(
				item_code=item, source=source, target=target, qty=2, posting_date=add_days(nowdate(), days)
			)

		fetched = []

		def record(names):
			fetched.extend(names)
			return get_sle_entries_by_names(names)

		get_sle_entries_by_names = stock_ledger.get_sle_entries_by_names
		with patch.object(stock_ledger, "get_sle_entries_by_names", side_effect=record):
			stock_ledger.update_entries_after(
				{
					"item_code": item,
					"warehouse": source,
					"posting_date": add_days(nowdate(), -3),
					"posting_time": "00:00:00",
				}
			)

		target_sles = frappe.get_all(
			"Stock Ledger Entry", {"item_code": item, "warehouse": target}, pluck="name"
		)
		self.assertTrue(set(target_sles) <= set(fetched))
		self.assertEqual(len(fetched), len(set(fetched)))
