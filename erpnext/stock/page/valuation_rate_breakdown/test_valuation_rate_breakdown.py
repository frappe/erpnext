from unittest.mock import patch

import frappe
from frappe.permissions import add_user_permission
from frappe.utils import add_days, today

from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.controllers.stock_controller import create_repost_item_valuation_entry
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_batch_from_bundle,
)
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.page.valuation_rate_breakdown.valuation_rate_breakdown import (
	get_stock_breakdown,
	get_valuation_steps,
	repost_from_entry,
)
from erpnext.stock.serial_batch_bundle import get_serial_nos_from_bundle
from erpnext.tests.utils import ERPNextTestSuite

WAREHOUSE = "Stores - _TC"
PAGE_MODULE = "erpnext.stock.page.valuation_rate_breakdown.valuation_rate_breakdown"


class TestValuationRateBreakdown(ERPNextTestSuite):
	def make_item(self, valuation_method, **properties):
		properties.update({"is_stock_item": 1, "valuation_method": valuation_method})
		return make_item(properties=properties).name

	def receive(self, item_code, rate, days_ago, qty=1):
		return make_purchase_receipt(
			item_code=item_code,
			qty=qty,
			rate=rate,
			warehouse=WAREHOUSE,
			posting_date=add_days(today(), -days_ago),
		)

	def get_entry_name(self, voucher_no):
		return frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": voucher_no, "is_cancelled": 0}, "name"
		)

	def make_purchase_return(self, item_code):
		first = self.receive(item_code, 50, 2)
		self.receive(item_code, 60, 1)
		purchase_return = make_return_doc("Purchase Receipt", first.name)
		purchase_return.submit()
		return first, self.get_entry_name(purchase_return.name)

	def test_purchase_return_shows_the_rate_used_and_the_original_rate(self):
		item_code = self.make_item("Moving Average")
		first, entry = self.make_purchase_return(item_code)

		steps = get_valuation_steps(item_code, WAREHOUSE, upto=entry)

		self.assertEqual(len(steps.entries), 3)
		self.assertEqual(steps.entries[0].qty_before, 0)
		self.assertEqual(steps.entries[1].rate_after, 55)
		returned = steps.entries[-1]
		self.assertEqual(returned.kind, "out")
		self.assertEqual(returned.return_against, first.name)
		self.assertEqual((returned.rate, returned.original_rate), (50, 50))
		self.assertEqual((returned.qty_after, returned.value_after, returned.rate_after), (1, 60, 60))

	def test_moving_average_purchase_return_after_repost_goes_out_at_average(self):
		item_code = self.make_item("Moving Average")
		_first, entry = self.make_purchase_return(item_code)
		create_repost_item_valuation_entry(
			{
				"based_on": "Item and Warehouse",
				"item_code": item_code,
				"warehouse": WAREHOUSE,
				"posting_date": add_days(today(), -2),
				"posting_time": "00:00:00",
				"company": "_Test Company",
			}
		)

		returned = get_valuation_steps(item_code, WAREHOUSE, upto=entry).entries[-1]

		self.assertEqual((returned.rate, returned.original_rate), (55, 50))
		self.assertEqual((returned.qty_after, returned.value_after, returned.rate_after), (1, 55, 55))

	def test_purchase_return_keeps_its_original_rate_when_entered(self):
		item_code = self.make_item("Moving Average")
		_first, entry = self.make_purchase_return(item_code)
		self.receive(item_code, 80, 1)

		returned = get_valuation_steps(item_code, WAREHOUSE, upto=entry).entries[-1]

		self.assertTrue(returned.changed_by)
		self.assertEqual((returned.rate_when_entered, returned.rate_after_when_entered), (50, 60))

	def test_fifo_purchase_return_replays_from_its_own_lot(self):
		item_code = self.make_item("FIFO")
		self.receive(item_code, 50, 2)
		second = self.receive(item_code, 60, 1)
		purchase_return = make_return_doc("Purchase Receipt", second.name)
		purchase_return.submit()
		entry = self.get_entry_name(purchase_return.name)
		self.receive(item_code, 80, 1)

		returned = get_valuation_steps(item_code, WAREHOUSE, upto=entry).entries[-1]

		self.assertTrue(returned.changed_by)
		self.assertEqual(returned.rate_when_entered, 60)

	def test_fifo_issue_lists_the_lot_used(self):
		item_code = self.make_item("FIFO")
		self.receive(item_code, 50, 2)
		self.receive(item_code, 60, 1)
		issue = make_stock_entry(item_code=item_code, source=WAREHOUSE, qty=1)

		steps = get_valuation_steps(item_code, WAREHOUSE, upto=self.get_entry_name(issue.name))
		issued = steps.entries[-1]

		self.assertEqual(issued.rate, 50)
		self.assertEqual(issued.used_lots, [[1, 50]])
		self.assertEqual(issued.lots_after, [[1, 60]])
		self.assertEqual(steps.entries[1].added_lots, [[1, 60]])

	def test_window_starts_where_stock_was_last_zero(self):
		item_code = self.make_item("Moving Average")
		self.receive(item_code, 50, 3)
		make_stock_entry(item_code=item_code, source=WAREHOUSE, qty=1, posting_date=add_days(today(), -2))
		last = self.receive(item_code, 70, 1)

		steps = get_valuation_steps(item_code, WAREHOUSE)

		self.assertEqual([entry.voucher_no for entry in steps.entries], [last.name])
		self.assertTrue(steps.has_earlier)
		self.assertEqual(steps.opening.qty, 0)

		earlier = get_valuation_steps(item_code, WAREHOUSE, before=steps.entries[0].name)
		self.assertEqual(len(earlier.entries), 2)
		self.assertFalse(earlier.has_earlier)

	def issue(self, item_code, days_ago, **kwargs):
		posting_date = add_days(today(), -days_ago)
		entry = make_stock_entry(
			item_code=item_code, source=WAREHOUSE, qty=1, posting_date=posting_date, **kwargs
		)
		return self.get_entry_name(entry.name)

	def test_backdated_receipt_shows_the_rate_when_the_issue_was_entered(self):
		item_code = self.make_item("Moving Average")
		self.receive(item_code, 100, 5, qty=2)
		issue = self.issue(item_code, 2)
		backdated = self.receive(item_code, 200, 4, qty=2)

		steps = get_valuation_steps(item_code, WAREHOUSE, upto=issue)
		issued = steps.entries[-1]

		self.assertEqual(issued.rate, 150)
		self.assertEqual((issued.rate_when_entered, issued.rate_after_when_entered), (100, 100))
		self.assertEqual([(d.voucher_no, d.kind) for d in issued.changed_by], [(backdated.name, "added")])
		backdated_entry = next(d for d in steps.entries if d.voucher_no == backdated.name)
		self.assertEqual(backdated_entry.later_dated_count, 1)
		self.assertEqual(steps.entries[0].changed_by, [])

	def test_backdated_receipt_changes_the_fifo_lot_used(self):
		item_code = self.make_item("FIFO")
		self.receive(item_code, 100, 5)
		issue = self.issue(item_code, 2)
		self.receive(item_code, 50, 6)

		issued = get_valuation_steps(item_code, WAREHOUSE, upto=issue).entries[-1]

		self.assertEqual(issued.rate, 50)
		self.assertEqual(issued.rate_when_entered, 100)

	def test_cancelled_earlier_receipt_is_listed_as_a_change(self):
		item_code = self.make_item("Moving Average")
		self.receive(item_code, 100, 5)
		second = self.receive(item_code, 200, 4)
		issue = self.issue(item_code, 2)
		second.cancel()

		issued = get_valuation_steps(item_code, WAREHOUSE, upto=issue).entries[-1]

		self.assertEqual(issued.rate, 100)
		self.assertEqual(issued.rate_when_entered, 150)
		self.assertEqual([(d.voucher_no, d.kind) for d in issued.changed_by], [(second.name, "cancelled")])

	def test_batch_issue_goes_out_at_the_batch_rate(self):
		item_code = self.make_item(
			"FIFO", has_batch_no=1, create_new_batch=1, batch_number_series="VRB-BATCH-.###"
		)
		self.receive(item_code, 100, 3, qty=10)
		second = self.receive(item_code, 200, 2, qty=10)
		batch_no = get_batch_from_bundle(second.items[0].serial_and_batch_bundle)
		issue = self.issue(item_code, 1, batch_no=batch_no)

		steps = get_valuation_steps(item_code, WAREHOUSE, upto=issue)
		[part] = steps.entries[-1].parts

		self.assertEqual(steps.item.valued_by, "batch")
		self.assertEqual((part.batch_no, part.qty, part.rate, part.own_rate), (batch_no, -1, 200, True))
		self.assertEqual((part.qty_before, part.value_before), (10, 2000))

	def test_serial_issue_goes_out_at_the_rate_the_serial_came_in_at(self):
		item_code = self.make_item("Moving Average", has_serial_no=1, serial_no_series="VRB-SN-.###")
		self.receive(item_code, 100, 3)
		second = self.receive(item_code, 300, 2)
		serial_no = get_serial_nos_from_bundle(second.items[0].serial_and_batch_bundle)[0]
		issue = self.issue(item_code, 1, serial_no=[serial_no])

		steps = get_valuation_steps(item_code, WAREHOUSE, upto=issue)
		[part] = steps.entries[-1].parts

		self.assertEqual(steps.item.valued_by, "serial")
		self.assertEqual(
			(part.serial_nos, part.rate, part.source_voucher_no), ([serial_no], 300, second.name)
		)
		self.assertEqual(steps.entries[-1].rate, 300)

	def test_entry_of_another_item_is_rejected(self):
		item_code = self.make_item("Moving Average")
		other = self.receive(self.make_item("Moving Average"), 50, 1)

		with self.assertRaises(frappe.ValidationError):
			get_valuation_steps(item_code, WAREHOUSE, upto=self.get_entry_name(other.name))

	def make_user(self, email, role):
		user = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Valuation", "send_welcome_email": 0}
		).insert(ignore_permissions=True)
		user.add_roles(role)
		return email

	def test_user_without_access_is_refused(self):
		item_code = self.make_item("Moving Average")
		entry = self.get_entry_name(self.receive(item_code, 50, 1).name)
		accounts_user = self.make_user("vrb-accounts-user@example.com", "Accounts User")
		stock_user = self.make_user("vrb-stock-user@example.com", "Stock User")
		other_warehouse = frappe.db.get_value(
			"Warehouse", {"company": "_Test Company", "is_group": 0, "name": ("!=", WAREHOUSE)}, "name"
		)
		add_user_permission("Warehouse", other_warehouse, stock_user, ignore_permissions=True)

		for user in (accounts_user, stock_user):
			frappe.set_user(user)
			with self.assertRaises(frappe.PermissionError):
				get_valuation_steps(item_code, WAREHOUSE)
			with self.assertRaises(frappe.PermissionError):
				get_stock_breakdown(item_code, WAREHOUSE, entry)
			with self.assertRaises(frappe.PermissionError):
				repost_from_entry(entry)
			frappe.set_user("Administrator")

	def test_repost_needs_permission_to_create_reposts(self):
		item_code = self.make_item("Moving Average")
		entry = self.get_entry_name(self.receive(item_code, 50, 1).name)
		frappe.set_user(self.make_user("vrb-stock-reader@example.com", "Stock User"))
		try:
			get_valuation_steps(item_code, WAREHOUSE)
			with self.assertRaises(frappe.PermissionError):
				repost_from_entry(entry)
		finally:
			frappe.set_user("Administrator")

	def tamper(self, entry, **values):
		frappe.db.set_value("Stock Ledger Entry", entry, values, update_modified=False)

	def problems_by_entry(self, item_code):
		entries = get_valuation_steps(item_code, WAREHOUSE).entries
		return {entry.name: [problem.check for problem in entry.ledger_problems or []] for entry in entries}

	def test_entry_that_does_not_add_up_is_flagged_and_repost_fixes_it(self):
		item_code = self.make_item("Moving Average")
		first, second, third = (
			self.get_entry_name(self.receive(item_code, rate, days_ago).name)
			for rate, days_ago in ((100, 3), (200, 2), (300, 1))
		)
		self.tamper(second, stock_value=800)

		entries = get_valuation_steps(item_code, WAREHOUSE).entries
		self.assertEqual(
			self.problems_by_entry(item_code), {first: [], second: ["value", "rate"], third: ["value"]}
		)
		self.assertEqual(entries[1].repost_from.name, second)

		repost = repost_from_entry(second)

		self.assertEqual(
			frappe.db.get_value("Repost Item Valuation", repost, ["based_on", "item_code", "status"]),
			("Item and Warehouse", item_code, "Completed"),
		)
		self.assertEqual(self.problems_by_entry(item_code), {first: [], second: [], third: []})

	def test_moving_average_issue_at_the_wrong_rate_is_flagged(self):
		item_code = self.make_item("Moving Average")
		self.receive(item_code, 100, 3, qty=2)
		issue = self.issue(item_code, 1)
		self.tamper(issue, stock_value_difference=-150, stock_value=50, valuation_rate=50)

		[problem] = get_valuation_steps(item_code, WAREHOUSE).entries[-1].ledger_problems

		self.assertEqual((problem.check, problem.expected, problem.actual), ("outgoing_rate", 100, 150))

	@patch(f"{PAGE_MODULE}.PAGE_SIZE", 1)
	def test_lots_problem_reposts_from_where_it_started(self):
		item_code = self.make_item("FIFO")
		first, second, third = (
			self.get_entry_name(self.receive(item_code, 100, days_ago).name) for days_ago in (3, 2, 1)
		)
		for entry in (second, third):
			self.tamper(entry, stock_queue="[]")

		[entry] = get_valuation_steps(item_code, WAREHOUSE).entries

		self.assertEqual(entry.name, third)
		self.assertEqual([problem.check for problem in entry.ledger_problems], ["lots"])
		self.assertEqual(entry.repost_from.name, second)

	def queue_repost(self, **fields):
		repost = frappe.get_doc(
			{
				"doctype": "Repost Item Valuation",
				"company": "_Test Company",
				"posting_date": add_days(today(), -3),
				"posting_time": "00:00:00",
				**fields,
			}
		)
		repost.flags.dont_run_in_test = True
		repost.submit()
		return repost

	def test_transaction_repost_is_shown_only_for_its_items(self):
		item_code = self.make_item("Moving Average")
		other_item = self.make_item("Moving Average")
		receipt = self.receive(item_code, 50, 3)
		self.receive(other_item, 50, 3)
		self.queue_repost(based_on="Transaction", voucher_type="Purchase Receipt", voucher_no=receipt.name)
		other_warehouse = frappe.db.get_value(
			"Warehouse", {"company": "_Test Company", "is_group": 0, "name": ("!=", WAREHOUSE)}, "name"
		)
		self.queue_repost(based_on="Item and Warehouse", item_code=other_item, warehouse=other_warehouse)

		self.assertEqual(get_valuation_steps(item_code, WAREHOUSE).repost_status, "pending")
		self.assertIsNone(get_valuation_steps(other_item, WAREHOUSE).repost_status)

	def test_failed_repost_is_reported(self):
		item_code = self.make_item("Moving Average")
		self.receive(item_code, 50, 3)
		repost = self.queue_repost(based_on="Item and Warehouse", item_code=item_code, warehouse=WAREHOUSE)
		frappe.db.set_value("Repost Item Valuation", repost.name, "status", "Failed")

		self.assertEqual(get_valuation_steps(item_code, WAREHOUSE).repost_status, "failed")

	def test_issue_waits_for_recalculation_until_repost_runs(self):
		item_code = self.make_item("Moving Average")
		self.receive(item_code, 100, 5, qty=2)
		issue = self.issue(item_code, 2)
		frappe.flags.dont_execute_stock_reposts = True
		try:
			self.receive(item_code, 200, 4, qty=2)
		finally:
			frappe.flags.dont_execute_stock_reposts = False

		steps = get_valuation_steps(item_code, WAREHOUSE, upto=issue)
		issued = steps.entries[-1]

		self.assertEqual(steps.repost_status, "pending")
		self.assertTrue(issued.awaiting_recalculation)
		self.assertEqual(issued.rate, 100)
		self.assertIsNone(issued.ledger_problems)

	def make_batch_item(self):
		item_code = self.make_item(
			"FIFO", has_batch_no=1, create_new_batch=1, batch_number_series="VRB-FOCUS-.###"
		)
		first = self.receive(item_code, 100, 4, qty=10)
		second = self.receive(item_code, 200, 3, qty=10)
		batches = [get_batch_from_bundle(doc.items[0].serial_and_batch_bundle) for doc in (first, second)]
		return item_code, batches, second

	def test_batch_stock_is_shown_batch_by_batch(self):
		item_code, (first_batch, second_batch), _second = self.make_batch_item()
		self.issue(item_code, 2, batch_no=second_batch)

		newest = get_valuation_steps(item_code, WAREHOUSE).entries[-1]
		breakdown = get_stock_breakdown(item_code, WAREHOUSE, newest.name)
		parts = {part.batch_no: (part.qty, part.value, part.rate) for part in breakdown.stock_parts}

		self.assertEqual(parts, {first_batch: (10, 1000, 100), second_batch: (9, 1800, 200)})
		self.assertIsNone(breakdown.stock_gap)

	def test_batch_filter_shows_only_that_batch(self):
		item_code, (first_batch, second_batch), second = self.make_batch_item()
		self.issue(item_code, 2, batch_no=first_batch)
		issue = self.issue(item_code, 1, batch_no=second_batch)

		steps = get_valuation_steps(item_code, WAREHOUSE, batch_no=second_batch)
		last = steps.entries[-1]

		self.assertEqual([entry.name for entry in steps.entries], [self.get_entry_name(second.name), issue])
		self.assertEqual((last.qty_before, last.value_before, last.qty, last.rate), (10, 2000, -1, 200))
		self.assertEqual((last.qty_after, last.value_after), (9, 1800))
		self.assertEqual((steps.focus.qty, steps.focus.value, steps.opening.qty), (9, 1800, 0))

	def test_serial_filter_follows_one_serial_number(self):
		item_code = self.make_item("Moving Average", has_serial_no=1, serial_no_series="VRB-FSN-.###")
		receipt = self.receive(item_code, 100, 3, qty=2)
		serial_no = get_serial_nos_from_bundle(receipt.items[0].serial_and_batch_bundle)[0]
		self.issue(item_code, 1, serial_no=[serial_no])

		steps = get_valuation_steps(item_code, WAREHOUSE, serial_no=serial_no)
		received, issued = steps.entries

		self.assertEqual((received.qty, received.qty_after, received.value_after), (1, 1, 100))
		self.assertEqual((issued.qty_before, issued.value_before, issued.qty_after), (1, 100, 0))
		self.assertEqual(issued.parts[0].source_voucher_no, receipt.name)
		self.assertEqual(steps.focus.qty, 0)
		self.assertEqual(
			[
				(part.qty, part.rate)
				for part in get_stock_breakdown(item_code, WAREHOUSE, issued.name).stock_parts
			],
			[(1, 100)],
		)

	@patch(f"{PAGE_MODULE}.PAGE_SIZE", 1)
	def test_older_entries_load_one_page_at_a_time(self):
		item_code = self.make_item(
			"FIFO", has_batch_no=1, create_new_batch=1, batch_number_series="VRB-PAGE-.###"
		)
		self.receive(item_code, 100, 3, qty=10)
		second = self.receive(item_code, 200, 2, qty=10)
		batch_no = get_batch_from_bundle(second.items[0].serial_and_batch_bundle)
		issue = self.issue(item_code, 1, batch_no=batch_no)

		newest = get_valuation_steps(item_code, WAREHOUSE)
		[part] = newest.entries[0].parts
		older = get_valuation_steps(item_code, WAREHOUSE, before=issue)

		self.assertEqual(([entry.name for entry in newest.entries], newest.has_earlier), ([issue], True))
		self.assertEqual((part.qty_before, part.value_before, part.rate), (10, 2000, 200))
		self.assertEqual(
			([entry.voucher_no for entry in older.entries], older.has_earlier), ([second.name], True)
		)

	def test_serial_that_left_at_a_different_value_explains_the_gap(self):
		item_code = self.make_item("Moving Average", has_serial_no=1, serial_no_series="VRB-GAP-.###")
		receipt = self.receive(item_code, 100, 3, qty=2)
		serial_no = get_serial_nos_from_bundle(receipt.items[0].serial_and_batch_bundle)[0]
		issue = self.issue(item_code, 1, serial_no=[serial_no])
		bundle = frappe.db.get_value("Stock Ledger Entry", issue, "serial_and_batch_bundle")
		frappe.db.set_value("Serial and Batch Entry", {"parent": bundle}, "stock_value_difference", 0)
		frappe.db.set_value("Stock Ledger Entry", issue, {"stock_value_difference": 0, "stock_value": 200})

		breakdown = get_stock_breakdown(item_code, WAREHOUSE, issue)
		[cause] = breakdown.stock_gap.causes

		self.assertEqual([(part.qty, part.value) for part in breakdown.stock_parts], [(1, 100)])
		self.assertEqual(breakdown.stock_gap.gap, 100)
		self.assertEqual((cause.serial_nos, cause.actual, cause.expected), ([serial_no], 0, 100))

	def test_rounding_sized_gap_is_not_flagged(self):
		item_code = self.make_item("Moving Average", has_serial_no=1, serial_no_series="VRB-ROUND-.###")
		receipt = self.receive(item_code, 100, 3, qty=2)
		sle = self.get_entry_name(receipt.name)
		frappe.db.set_value("Stock Ledger Entry", sle, "stock_value", 200.4)

		breakdown = get_stock_breakdown(item_code, WAREHOUSE, sle)

		self.assertEqual(sum(part.value for part in breakdown.stock_parts), 200)
		self.assertIsNone(breakdown.stock_gap)

	def test_batch_valuation_says_whether_batches_share_a_value(self):
		item_code, (first_batch, second_batch), _second = self.make_batch_item()
		valuation = lambda: get_valuation_steps(item_code, WAREHOUSE).item.batch_valuation  # noqa: E731

		self.assertEqual(valuation(), "own")
		frappe.db.set_value("Batch", first_batch, "use_batchwise_valuation", 0)
		self.assertEqual(valuation(), "mixed")
		frappe.db.set_value("Batch", second_batch, "use_batchwise_valuation", 0)
		self.assertEqual(valuation(), "shared")

	def make_legacy(self, entry, **fields):
		bundle = frappe.db.get_value("Stock Ledger Entry", entry, "serial_and_batch_bundle")
		frappe.db.set_value("Serial and Batch Entry", {"parent": bundle}, "is_cancelled", 1)
		values = {"serial_and_batch_bundle": None, **fields}
		frappe.db.set_value("Stock Ledger Entry", entry, values, update_modified=False)

	def test_legacy_batch_entries_are_part_of_the_history(self):
		item_code, (first_batch, second_batch), _second = self.make_batch_item()
		[receipt] = frappe.get_all(
			"Stock Ledger Entry",
			filters={"item_code": item_code, "is_cancelled": 0},
			order_by="posting_datetime, creation",
			limit=1,
			pluck="name",
		)
		self.make_legacy(receipt, batch_no=first_batch)
		issue = self.issue(item_code, 1, batch_no=first_batch)

		breakdown = get_stock_breakdown(item_code, WAREHOUSE, issue)
		[issued] = get_valuation_steps(item_code, WAREHOUSE, upto=issue).entries[-1].parts
		focus = get_valuation_steps(item_code, WAREHOUSE, batch_no=first_batch)

		parts = {part.batch_no: (part.qty, part.value) for part in breakdown.stock_parts}
		self.assertEqual(parts, {first_batch: (9, 900), second_batch: (10, 2000)})
		self.assertIsNone(breakdown.stock_gap)
		self.assertEqual((issued.batch_no, issued.qty_before, issued.rate), (first_batch, 10, 100))
		self.assertEqual([entry.name for entry in focus.entries], [receipt, issue])

	def test_legacy_serial_entries_are_part_of_the_history(self):
		item_code = self.make_item("Moving Average", has_serial_no=1, serial_no_series="VRB-OLD-.###")
		receipt = self.receive(item_code, 100, 3, qty=2)
		entry = self.get_entry_name(receipt.name)
		first, second = get_serial_nos_from_bundle(receipt.items[0].serial_and_batch_bundle)
		self.make_legacy(entry, serial_no=f"{first}\n{second}")
		issue = self.issue(item_code, 1, serial_no=[first])

		breakdown = get_stock_breakdown(item_code, WAREHOUSE, issue)
		[issued] = get_valuation_steps(item_code, WAREHOUSE, upto=issue).entries[-1].parts
		focus = get_valuation_steps(item_code, WAREHOUSE, serial_no=first)

		self.assertEqual([(part.qty, part.value) for part in breakdown.stock_parts], [(1, 100)])
		self.assertIsNone(breakdown.stock_gap)
		self.assertEqual(
			(issued.serial_nos, issued.source_voucher_no, issued.source_rate), ([first], receipt.name, 100)
		)
		self.assertEqual([step.name for step in focus.entries], [entry, issue])

	def test_batch_of_another_item_is_rejected(self):
		item_code, (first_batch, _), _second = self.make_batch_item()
		other_item = self.make_item(
			"FIFO", has_batch_no=1, create_new_batch=1, batch_number_series="VRB-OTHER-.###"
		)

		with self.assertRaises(frappe.ValidationError):
			get_valuation_steps(other_item, WAREHOUSE, batch_no=first_batch)
