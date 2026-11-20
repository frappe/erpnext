from unittest.mock import patch

import frappe
from frappe.utils import add_days, flt, today

from erpnext.projects.doctype.project.test_project import make_project
from erpnext.stock import get_warehouse_account_map
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.repost_item_valuation import repost_item_valuation
from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import execute_reposting_entry
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
	create_stock_reconciliation,
)
from erpnext.stock.stock_ledger import update_entries_after
from erpnext.stock.tests.test_utils import StockTestMixin
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company with perpetual inventory"
WAREHOUSE = "Stores - TCP1"
TARGET_WAREHOUSE = "Finished Goods - TCP1"
WAREHOUSE_WITHOUT_PERPETUAL_INVENTORY = "_Test Warehouse - _TC"


class TestRepostSkipUnchangedEntries(ERPNextTestSuite, StockTestMixin):
	def test_repost_stops_at_stock_reconciliation(self):
		item = self.make_item(properties={"valuation_method": "FIFO"}).name
		self.receive(item, 10, 100, days_ago=10)
		issue = self.issue(item, 5, days_ago=8)
		reco = self.reconcile(item, 20, 150, days_ago=6)
		later_issue = self.issue(item, 5, days_ago=4)
		later_receipt = self.receive(item, 5, 200, days_ago=2)

		backdated, reposted, gl_vouchers = self.record_repost(lambda: self.receive(item, 10, 120, days_ago=9))

		self.assertEqual(reposted, [backdated.name, issue.name, reco.name])
		self.assertSLEValues(issue, stock_value_difference=-500, stock_value=1700)
		self.assertSLEValues(reco, stock_value_difference=1300, stock_value=3000)
		self.assertSLEValues(later_issue, stock_value_difference=-750, stock_value=2250)
		self.assertEqual(self.get_stock_account_balance(reco), 1300)
		self.assertIn(reco.name, gl_vouchers)
		self.assertNotIn(later_issue.name, gl_vouchers)
		self.assertNotIn(later_receipt.name, gl_vouchers)

	def test_backdated_reconciliation_reposts_till_the_next_reconciliation(self):
		item = self.make_item(properties={"valuation_method": "FIFO"}).name
		self.receive(item, 10, 100, days_ago=10)
		issue = self.issue(item, 5, days_ago=8)
		reco = self.reconcile(item, 20, 150, days_ago=6)
		later_issue = self.issue(item, 5, days_ago=4)

		backdated, reposted, _gl_vouchers = self.record_repost(
			lambda: self.reconcile(item, 15, 110, days_ago=9)
		)

		self.assertEqual(reposted, [backdated.name, issue.name, reco.name])
		self.assertSLEValues(issue, stock_value_difference=-550, stock_value=1100)
		self.assertSLEValues(reco, stock_value_difference=1900, stock_value=3000)
		self.assertNotIn(later_issue.name, reposted)

	def test_return_after_reconciliation_takes_the_new_rate(self):
		item = self.make_item(properties={"valuation_method": "FIFO"}).name
		self.receive(item, 10, 100, days_ago=10)
		delivery = self.deliver(item, 5, days_ago=8)
		self.reconcile(item, 20, 150, days_ago=6)
		sales_return = self.deliver(item, -2, days_ago=4, is_return=1, return_against=delivery.name)
		later_issue = self.issue(item, 5, days_ago=2)

		self.receive(item, 10, 50, days_ago=11)

		self.assertSLEValues(delivery, stock_value_difference=-250)
		self.assertSLEValues(sales_return, incoming_rate=50, stock_value_difference=100, stock_value=3100)
		self.assertSLEValues(later_issue, stock_value_difference=-750, stock_value=2350)
		self.assertEqual(self.get_stock_account_balance(sales_return), 100)

	def test_project_cost_is_updated_after_the_return_without_perpetual_inventory(self):
		warehouse = WAREHOUSE_WITHOUT_PERPETUAL_INVENTORY
		item = self.make_item(properties={"valuation_method": "FIFO"}).name
		project = make_project({"project_name": f"_Test Repost Project {frappe.generate_hash(length=6)}"})
		self.receive(item, 10, 100, days_ago=10, warehouse=warehouse)
		delivery = create_delivery_note(
			item_code=item, qty=5, warehouse=warehouse, posting_date=add_days(today(), -8)
		)
		create_stock_reconciliation(
			item_code=item, warehouse=warehouse, qty=20, rate=150, posting_date=add_days(today(), -6)
		)
		create_delivery_note(
			item_code=item,
			qty=-2,
			warehouse=warehouse,
			is_return=1,
			return_against=delivery.name,
			posting_date=add_days(today(), -4),
		)
		project_issue = self.issue(item, 22, days_ago=2, warehouse=warehouse, project=project.name)

		self.receive(item, 10, 50, days_ago=11, warehouse=warehouse)

		self.assertSLEValues(project_issue, warehouse=warehouse, stock_value_difference=-3100)
		self.assertEqual(frappe.db.get_value("Project", project.name, "total_consumed_material_cost"), 3100)

	def test_unchanged_transfer_target_stops_after_the_transfer(self):
		item = self.make_item(properties={"valuation_method": "FIFO"}).name
		self.receive(item, 20, 100, days_ago=10)
		self.transfer(item, 5, days_ago=8)
		first_issue = self.issue(item, 2, days_ago=6, warehouse=TARGET_WAREHOUSE)
		later_issue = self.issue(item, 1, days_ago=4, warehouse=TARGET_WAREHOUSE)

		_backdated, reposted, _gl_vouchers = self.record_repost(
			lambda: self.receive(item, 10, 100, days_ago=9)
		)

		self.assertIn(first_issue.name, reposted)
		self.assertNotIn(later_issue.name, reposted)
		self.assertSLEValues(later_issue, warehouse=TARGET_WAREHOUSE, stock_value=200)

	def test_changed_transfer_target_is_reposted_until_it_settles(self):
		item = self.make_item(properties={"valuation_method": "FIFO"}).name
		self.receive(item, 10, 100, days_ago=10)
		transfer = self.transfer(item, 5, days_ago=8)
		first_issue = self.issue(item, 2, days_ago=6, warehouse=TARGET_WAREHOUSE)
		second_issue = self.issue(item, 3, days_ago=5, warehouse=TARGET_WAREHOUSE)
		refill = self.receive(item, 5, 120, days_ago=4, warehouse=TARGET_WAREHOUSE)
		later_issue = self.issue(item, 2, days_ago=2, warehouse=TARGET_WAREHOUSE)

		_backdated, reposted, _gl_vouchers = self.record_repost(
			lambda: self.receive(item, 10, 80, days_ago=12)
		)

		self.assertSLEValues(transfer, warehouse=TARGET_WAREHOUSE, stock_value_difference=400)
		self.assertSLEValues(
			first_issue, warehouse=TARGET_WAREHOUSE, stock_value_difference=-160, stock_value=240
		)
		self.assertSLEValues(
			second_issue, warehouse=TARGET_WAREHOUSE, stock_value_difference=-240, stock_value=0
		)
		self.assertSLEValues(refill, warehouse=TARGET_WAREHOUSE, stock_value=600)
		self.assertIn(refill.name, reposted)
		self.assertNotIn(later_issue.name, reposted)

	def test_matching_balance_inside_the_backdated_shift_does_not_stop_the_repost(self):
		item = self.make_item(properties={"valuation_method": "Moving Average"}).name
		self.receive(item, 10, 10, days_ago=10)
		receipt = self.receive(item, 10, 10, days_ago=8)
		issue = self.issue(item, 5, days_ago=6)

		self.receive(item, 10, 20, days_ago=9)

		self.assertSLEValues(receipt, stock_value=400)
		self.assertSLEValues(issue, stock_value=333.33)

	def test_queued_repost_after_the_stop_is_not_skipped(self):
		item = self.make_item(properties={"valuation_method": "FIFO"}).name
		self.receive(item, 10, 100, days_ago=10)
		self.issue(item, 5, days_ago=8)
		self.reconcile(item, 20, 150, days_ago=6)
		self.issue(item, 5, days_ago=4)

		running = self.make_queued_repost(item, days_ago=9)
		covered = self.make_queued_repost(item, days_ago=7)
		full_repost = self.make_queued_repost(item, days_ago=7, skip_unchanged_entries=0)
		after_stop = self.make_queued_repost(item, days_ago=4)
		execute_reposting_entry(running.name)

		self.assertEqual(
			[
				frappe.db.get_value("Repost Item Valuation", repost.name, "status")
				for repost in (running, covered, full_repost, after_stop)
			],
			["Completed", "Skipped", "Queued", "Queued"],
		)

	def test_repost_without_skip_walks_the_whole_ledger(self):
		item = self.make_item(properties={"valuation_method": "FIFO"}).name
		self.receive(item, 10, 100, days_ago=10)
		self.reconcile(item, 20, 150, days_ago=6)
		later_issue = self.issue(item, 5, days_ago=4)

		repost = self.make_queued_repost(item, days_ago=9, skip_unchanged_entries=0)
		_result, reposted, _gl_vouchers = self.record_repost(lambda: execute_reposting_entry(repost.name))

		self.assertIn(later_issue.name, reposted)

	def receive(self, item, qty, rate, days_ago, warehouse=WAREHOUSE):
		return make_stock_entry(
			item_code=item, target=warehouse, qty=qty, rate=rate, posting_date=add_days(today(), -days_ago)
		)

	def issue(self, item, qty, days_ago, warehouse=WAREHOUSE, project=None):
		issue = make_stock_entry(
			item_code=item,
			source=warehouse,
			qty=qty,
			posting_date=add_days(today(), -days_ago),
			do_not_save=True,
		)
		issue.project = project
		issue.insert()
		issue.submit()
		return issue

	def transfer(self, item, qty, days_ago):
		return make_stock_entry(
			item_code=item,
			source=WAREHOUSE,
			target=TARGET_WAREHOUSE,
			qty=qty,
			posting_date=add_days(today(), -days_ago),
		)

	def reconcile(self, item, qty, rate, days_ago):
		return create_stock_reconciliation(
			item_code=item,
			warehouse=WAREHOUSE,
			company=COMPANY,
			qty=qty,
			rate=rate,
			posting_date=add_days(today(), -days_ago),
		)

	def deliver(self, item, qty, days_ago, **args):
		return create_delivery_note(
			item_code=item,
			qty=qty,
			rate=300,
			company=COMPANY,
			warehouse=WAREHOUSE,
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			posting_date=add_days(today(), -days_ago),
			**args,
		)

	def make_queued_repost(self, item, days_ago, skip_unchanged_entries=1):
		repost = frappe.new_doc("Repost Item Valuation")
		repost.update(
			{
				"based_on": "Item and Warehouse",
				"item_code": item,
				"warehouse": WAREHOUSE,
				"company": COMPANY,
				"posting_date": add_days(today(), -days_ago),
				"posting_time": "00:00:00",
				"skip_unchanged_entries": skip_unchanged_entries,
			}
		)
		repost.flags.dont_run_in_test = True
		repost.submit()
		return repost

	def record_repost(self, action):
		reposted, gl_vouchers = [], []
		repost_entry = update_entries_after.repost_stock_ledger_entry
		repost_gl = repost_item_valuation.repost_gle_for_stock_vouchers

		def record_entry(obj, sle):
			reposted.append(sle.voucher_no)
			return repost_entry(obj, sle)

		def record_gl(stock_vouchers, *args, **kwargs):
			gl_vouchers.extend(voucher_no for _voucher_type, voucher_no in stock_vouchers)
			return repost_gl(stock_vouchers, *args, **kwargs)

		with (
			patch.object(update_entries_after, "repost_stock_ledger_entry", record_entry),
			patch.object(repost_item_valuation, "repost_gle_for_stock_vouchers", record_gl),
		):
			result = action()

		return result, reposted, gl_vouchers

	def assertSLEValues(self, doc, warehouse=WAREHOUSE, **expected):
		sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": doc.name, "warehouse": warehouse, "is_cancelled": 0},
			list(expected),
			as_dict=True,
		)
		for field, value in expected.items():
			self.assertEqual(flt(sle[field], 2), flt(value, 2), msg=f"{field} of {doc.name}")

	def get_stock_account_balance(self, doc):
		account = get_warehouse_account_map(COMPANY)[WAREHOUSE].account
		gl_entries = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": doc.name, "account": account, "is_cancelled": 0},
			fields=["debit", "credit"],
		)
		return flt(sum(flt(row.debit) - flt(row.credit) for row in gl_entries), 2)
