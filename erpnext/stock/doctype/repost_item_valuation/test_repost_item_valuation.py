# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


from unittest.mock import MagicMock, call

import frappe
from frappe.utils import add_days, add_to_date, now, nowdate, today

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.utils import repost_gle_for_stock_vouchers
from erpnext.controllers.stock_controller import create_item_wise_repost_entries
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import (
	in_configured_timeslot,
	mark_covered_transaction_reposts,
)
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.tests.test_utils import StockTestMixin
from erpnext.stock.utils import PendingRepostingError, get_combine_datetime
from erpnext.tests.utils import ERPNextTestSuite


class TestRepostItemValuation(ERPNextTestSuite, StockTestMixin):
	def test_repost_time_slot(self):
		repost_settings = frappe.get_doc("Stock Reposting Settings")

		positive_cases = [
			{"limit_reposting_timeslot": 0},
			{
				"limit_reposting_timeslot": 1,
				"start_time": "18:00:00",
				"end_time": "09:00:00",
				"current_time": "20:00:00",
			},
			{
				"limit_reposting_timeslot": 1,
				"start_time": "09:00:00",
				"end_time": "18:00:00",
				"current_time": "12:00:00",
			},
			{
				"limit_reposting_timeslot": 1,
				"start_time": "23:00:00",
				"end_time": "09:00:00",
				"current_time": "2:00:00",
			},
		]

		for case in positive_cases:
			repost_settings.update(case)
			self.assertTrue(
				in_configured_timeslot(repost_settings, case.get("current_time")),
				msg=f"Exepcted true from : {case}",
			)

		negative_cases = [
			{
				"limit_reposting_timeslot": 1,
				"start_time": "18:00:00",
				"end_time": "09:00:00",
				"current_time": "09:01:00",
			},
			{
				"limit_reposting_timeslot": 1,
				"start_time": "09:00:00",
				"end_time": "18:00:00",
				"current_time": "19:00:00",
			},
			{
				"limit_reposting_timeslot": 1,
				"start_time": "23:00:00",
				"end_time": "09:00:00",
				"current_time": "22:00:00",
			},
		]

		for case in negative_cases:
			repost_settings.update(case)
			self.assertFalse(
				in_configured_timeslot(repost_settings, case.get("current_time")),
				msg=f"Exepcted false from : {case}",
			)

	def test_clear_old_logs(self):
		# create 10 logs
		for i in range(1, 20):
			repost_doc = frappe.get_doc(
				doctype="Repost Item Valuation",
				item_code="_Test Item",
				warehouse="_Test Warehouse - _TC",
				based_on="Item and Warehouse",
				posting_date=nowdate(),
				status="Skipped",
				posting_time="00:01:00",
			).insert(ignore_permissions=True)

			repost_doc.load_from_db()
			repost_doc.creation = add_days(now(), days=-i * 10)
			repost_doc.db_update_all()

		logs = frappe.get_all("Repost Item Valuation", filters={"status": "Skipped"})
		self.assertGreater(len(logs), 10)

		from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import RepostItemValuation

		RepostItemValuation.clear_old_logs(days=1)

		logs = frappe.get_all("Repost Item Valuation", filters={"status": "Skipped"})
		self.assertEqual(len(logs), 0)

	def test_create_item_wise_repost_item_valuation_entries(self):
		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			get_multiple_items=True,
		)

		rivs = create_item_wise_repost_entries(pr.doctype, pr.name)
		self.assertGreaterEqual(len(rivs), 2)
		self.assertIn("_Test Item", [d.item_code for d in rivs])

		for riv in rivs:
			self.assertEqual(riv.company, "_Test Company with perpetual inventory")
			self.assertEqual(riv.warehouse, "Stores - TCP1")

	def test_deduplication(self):
		def _assert_status(doc, status):
			doc.load_from_db()
			self.assertEqual(doc.status, status)

		riv_args = frappe._dict(
			doctype="Repost Item Valuation",
			item_code="_Test Item",
			warehouse="_Test Warehouse - _TC",
			based_on="Item and Warehouse",
			posting_date="2021-01-02",
			posting_time="00:01:00",
		)

		# new repost without any duplicates
		riv1 = frappe.get_doc(riv_args)
		riv1.flags.dont_run_in_test = True
		riv1.submit()
		_assert_status(riv1, "Queued")

		# newer than existing duplicate - riv1
		riv2 = frappe.get_doc(riv_args.update({"posting_date": "2021-01-03"}))
		riv2.flags.dont_run_in_test = True
		riv2.submit()
		riv1.deduplicate_similar_repost()
		_assert_status(riv2, "Skipped")

		# older than exisitng duplicate - riv1
		riv3 = frappe.get_doc(riv_args.update({"posting_date": "2021-01-01"}))
		riv3.flags.dont_run_in_test = True
		riv3.submit()
		riv3.deduplicate_similar_repost()
		_assert_status(riv3, "Queued")
		_assert_status(riv1, "Skipped")

		# unrelated reposts, shouldn't do anything to others.
		riv4 = frappe.get_doc(riv_args.update({"warehouse": "Stores - _TC"}))
		riv4.flags.dont_run_in_test = True
		riv4.submit()
		riv4.deduplicate_similar_repost()
		_assert_status(riv4, "Queued")
		_assert_status(riv3, "Queued")

		# to avoid breaking other tests accidentaly
		riv4.set_status("Skipped")
		riv3.set_status("Skipped")

	def _make_queued_transaction_riv(self, voucher):
		riv = frappe.get_doc(
			doctype="Repost Item Valuation",
			based_on="Transaction",
			voucher_type=voucher.doctype,
			voucher_no=voucher.name,
			posting_date=voucher.posting_date,
			posting_time="00:00:00",
		)
		riv.flags.dont_run_in_test = True
		riv.submit()
		return riv

	def test_skip_transaction_repost_covered_by_dependent(self):
		company = "_Test Company with perpetual inventory"
		warehouse = "Stores - TCP1"

		covered_pr = make_purchase_receipt(
			company=company, warehouse=warehouse, item_code="_Test Item", qty=5
		)
		other_pr = make_purchase_receipt(
			company=company, warehouse=warehouse, item_code="_Test Item 2", qty=5
		)

		covered_riv = self._make_queued_transaction_riv(covered_pr)
		other_riv = self._make_queued_transaction_riv(other_pr)

		earlier_date = add_days(covered_pr.posting_date, -1)
		source = frappe._dict(name="__test_source_riv__", posting_date=earlier_date, posting_time="00:00:00")
		coverage = {("_Test Item", warehouse): get_combine_datetime(earlier_date, "00:00:00")}
		affected = {("Purchase Receipt", covered_pr.name), ("Purchase Receipt", other_pr.name)}

		mark_covered_transaction_reposts(source, coverage, affected)

		covered_riv.reload()
		other_riv.reload()
		self.assertEqual(covered_riv.status, "Skipped")
		self.assertEqual(other_riv.status, "Queued")

		other_riv.db_set("status", "Skipped")

	def _make_dependent_repack(self, company, consumed_items, source_wh, fg_item, fg_wh, qty, posting_date):
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Repack"
		se.company = company
		se.set_posting_time = 1
		se.posting_date = posting_date
		for item_code in consumed_items:
			se.append("items", {"item_code": item_code, "s_warehouse": source_wh, "qty": qty})
		se.append("items", {"item_code": fg_item, "t_warehouse": fg_wh, "qty": qty, "is_finished_item": 1})
		se.insert()
		se.submit()
		return se

	def test_backdated_manufacture_repost_skips_redundant_dependent(self):
		from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import (
			execute_reposting_entry,
		)

		frappe.flags.dont_execute_stock_reposts = True
		self.addCleanup(frappe.flags.pop, "dont_execute_stock_reposts", None)

		original_setting = frappe.db.get_single_value("Stock Reposting Settings", "item_based_reposting")
		frappe.db.set_single_value("Stock Reposting Settings", "item_based_reposting", 1)
		self.addCleanup(
			frappe.db.set_single_value, "Stock Reposting Settings", "item_based_reposting", original_setting
		)

		company = "_Test Company with perpetual inventory"
		source_wh = "Stores - TCP1"
		fg_wh = "Finished Goods - TCP1"

		item_a = make_item(properties={"valuation_method": "FIFO"}).name
		item_b = make_item(properties={"valuation_method": "FIFO"}).name
		item_c = make_item(properties={"valuation_method": "FIFO"}).name

		def _day(days):
			return add_days(nowdate(), days)

		make_stock_entry(
			item_code=item_a, to_warehouse=source_wh, qty=10, rate=100, posting_date=_day(2), company=company
		)
		make_stock_entry(
			item_code=item_b, to_warehouse=source_wh, qty=10, rate=100, posting_date=_day(3), company=company
		)
		self._make_dependent_repack(company, [item_a, item_b], source_wh, item_c, fg_wh, 5, _day(10))

		make_stock_entry(
			item_code=item_a, to_warehouse=source_wh, qty=10, rate=200, posting_date=_day(1), company=company
		)
		make_stock_entry(
			item_code=item_b, to_warehouse=source_wh, qty=10, rate=200, posting_date=_day(1), company=company
		)
		self._make_dependent_repack(company, [item_a, item_b], source_wh, item_c, fg_wh, 5, _day(5))

		rivs = frappe.get_all(
			"Repost Item Valuation",
			filters={
				"docstatus": 1,
				"based_on": "Item and Warehouse",
				"status": "Queued",
				"item_code": ("in", [item_a, item_b, item_c]),
			},
			fields=["name", "item_code", "warehouse"],
			order_by="posting_date asc, posting_time asc, creation asc",
		)
		self.assertTrue(
			any(r.item_code == item_c and r.warehouse == fg_wh for r in rivs),
			msg="Expected a queued repost for the finished good",
		)

		for r in rivs:
			execute_reposting_entry(r.name)

		fg_repost_status = frappe.db.get_value(
			"Repost Item Valuation",
			{"based_on": "Item and Warehouse", "item_code": item_c, "warehouse": fg_wh, "docstatus": 1},
			"status",
		)
		self.assertEqual(fg_repost_status, "Skipped")

	def test_stock_freeze_validation(self):
		today = nowdate()

		riv = frappe.get_doc(
			doctype="Repost Item Valuation",
			item_code="_Test Item",
			warehouse="_Test Warehouse - _TC",
			based_on="Item and Warehouse",
			posting_date=today,
			posting_time="00:01:00",
		)
		riv.flags.dont_run_in_test = True  # keep it queued
		riv.submit()

		stock_settings = frappe.get_doc("Stock Settings")
		stock_settings.stock_frozen_upto = today

		self.assertRaises(PendingRepostingError, stock_settings.save)

		riv.set_status("Skipped")

	@ERPNextTestSuite.change_settings("Stock Reposting Settings", {"item_based_reposting": 0})
	def test_prevention_of_cancelled_transaction_riv(self):
		frappe.flags.dont_execute_stock_reposts = True
		self.addCleanup(frappe.flags.pop, "dont_execute_stock_reposts")

		item = make_item()
		warehouse = "_Test Warehouse - _TC"
		old = make_stock_entry(item_code=item.name, to_warehouse=warehouse, qty=2, rate=5)
		_new = make_stock_entry(item_code=item.name, to_warehouse=warehouse, qty=5, rate=10)

		old.cancel()

		riv = frappe.get_last_doc(
			"Repost Item Valuation", {"voucher_type": old.doctype, "voucher_no": old.name}
		)
		self.assertRaises(frappe.ValidationError, riv.cancel)

		riv.db_set("status", "Skipped")
		riv.reload()
		riv.cancel()  # it should cancel now

	def test_queue_progress_serialization(self):
		# Make sure set/tuple -> list behaviour is retained.
		self.assertEqual(
			[["a", "b"], ["c", "d"]],
			sorted(frappe.parse_json(frappe.as_json(set([("a", "b"), ("c", "d")])))),
		)

	def test_recoverable_error_requeues_instead_of_failing(self):
		# A recoverable DB error (e.g. Postgres deadlock -> QueryDeadlockError) must re-queue the
		# repost as "In Progress"; a non-recoverable error still fails. Regression: the old check
		# string-matched MariaDB's "Deadlock found" and missed Postgres deadlocks ("deadlock detected").
		from unittest.mock import patch

		from frappe.exceptions import QueryDeadlockError

		from erpnext.stock.doctype.repost_item_valuation import repost_item_valuation as riv

		orig_max_writes = frappe.db.MAX_WRITES_PER_TRANSACTION
		self.addCleanup(setattr, frappe.db, "MAX_WRITES_PER_TRANSACTION", orig_max_writes)

		def status_after(error):
			doc = frappe.new_doc("Repost Item Valuation")
			doc.name = "test-recoverable-riv"
			doc.set_status = doc.log_error = doc.db_set = MagicMock()
			captured = {}
			with (
				patch.object(frappe, "in_test", False),
				patch.object(frappe.db, "exists", return_value=True),
				patch.object(frappe.db, "commit"),
				patch.object(frappe.db, "rollback"),
				patch.object(frappe.db, "set_value", side_effect=lambda *a, **k: captured.update(a[2])),
				patch.object(riv, "repost_sl_entries", side_effect=error),
				patch.object(frappe, "get_cached_value", return_value=None),
			):
				riv.repost(doc)
			return captured.get("status")

		self.assertEqual(status_after(QueryDeadlockError("deadlock detected")), "In Progress")
		self.assertEqual(status_after(ValueError("boom")), "Failed")

	def test_gl_repost_progress(self):
		from erpnext.accounts import utils

		# lower numbers to simplify test
		orig_chunk_size = utils.GL_REPOSTING_CHUNK
		utils.GL_REPOSTING_CHUNK = 1
		self.addCleanup(setattr, utils, "GL_REPOSTING_CHUNK", orig_chunk_size)

		doc = frappe.new_doc("Repost Item Valuation")
		doc.db_set = MagicMock()

		vouchers = []
		company = "_Test Company with perpetual inventory"
		posting_date = today()

		for _ in range(3):
			se = make_stock_entry(company=company, qty=1, rate=2, target="Stores - TCP1")
			vouchers.append((se.doctype, se.name))

		repost_gle_for_stock_vouchers(stock_vouchers=vouchers, posting_date=posting_date, repost_doc=doc)
		self.assertIn(call("gl_reposting_index", 1), doc.db_set.mock_calls)
		doc.db_set.reset_mock()

		doc.gl_reposting_index = 1
		repost_gle_for_stock_vouchers(stock_vouchers=vouchers, posting_date=posting_date, repost_doc=doc)

		self.assertNotIn(call("gl_reposting_index", 1), doc.db_set.mock_calls)

	def test_gl_complete_gl_reposting(self):
		from erpnext.accounts import utils

		# lower numbers to simplify test
		orig_chunk_size = utils.GL_REPOSTING_CHUNK
		utils.GL_REPOSTING_CHUNK = 2
		self.addCleanup(setattr, utils, "GL_REPOSTING_CHUNK", orig_chunk_size)

		item = self.make_item().name

		company = "_Test Company with perpetual inventory"

		for _ in range(10):
			make_stock_entry(item=item, company=company, qty=1, rate=10, target="Stores - TCP1")

		# consume
		consumption = make_stock_entry(item=item, company=company, qty=1, source="Stores - TCP1")

		self.assertGLEs(
			consumption,
			[{"credit": 10, "debit": 0}],
			gle_filters={"account": "Stock In Hand - TCP1"},
		)

		# backdated receipt
		backdated_receipt = make_stock_entry(
			item=item,
			company=company,
			qty=1,
			rate=50,
			target="Stores - TCP1",
			posting_date=add_to_date(today(), days=-1),
		)
		self.assertGLEs(
			backdated_receipt,
			[{"credit": 0, "debit": 50}],
			gle_filters={"account": "Stock In Hand - TCP1"},
		)

		# check that original consumption GLe is updated
		self.assertGLEs(
			consumption,
			[{"credit": 50, "debit": 0}],
			gle_filters={"account": "Stock In Hand - TCP1"},
		)

	def test_duplicate_ple_on_repost(self):
		from erpnext.accounts import utils

		# lower numbers to simplify test
		orig_chunk_size = utils.GL_REPOSTING_CHUNK
		utils.GL_REPOSTING_CHUNK = 2
		self.addCleanup(setattr, utils, "GL_REPOSTING_CHUNK", orig_chunk_size)

		rate = 100
		item = self.make_item()
		item.valuation_rate = 90
		item.allow_negative_stock = 1
		item.save()

		company = "_Test Company with perpetual inventory"

		# consume non-existing stock
		sinv = create_sales_invoice(
			company=company,
			posting_date=today(),
			debit_to="Debtors - TCP1",
			income_account="Sales - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			warehouse="Stores - TCP1",
			update_stock=1,
			currency="INR",
			item_code=item.name,
			cost_center="Main - TCP1",
			qty=1,
			rate=rate,
		)

		# backdated receipt triggers repost
		make_stock_entry(
			item=item.name,
			company=company,
			qty=5,
			rate=rate,
			target="Stores - TCP1",
			posting_date=add_to_date(today(), days=-1),
		)

		ple_entries = frappe.db.get_list(
			"Payment Ledger Entry",
			filters={"voucher_type": sinv.doctype, "voucher_no": sinv.name, "delinked": 0},
		)

		# assert successful deduplication on PLE
		self.assertEqual(len(ple_entries), 1)

		# outstanding should not be affected
		sinv.reload()
		self.assertEqual(sinv.outstanding_amount, 100)

	def test_account_freeze_validation(self):
		today = nowdate()

		riv = frappe.get_doc(
			doctype="Repost Item Valuation",
			item_code="_Test Item",
			company="_Test Company",
			warehouse="_Test Warehouse - _TC",
			based_on="Item and Warehouse",
			posting_date=today,
			posting_time="00:01:00",
		)
		riv.flags.dont_run_in_test = True  # keep it queued

		company = frappe.get_doc("Company", "_Test Company")
		company.accounts_frozen_till_date = today
		company.role_allowed_for_frozen_entries = ""
		company.save()

		self.assertRaises(frappe.ValidationError, riv.save)

		company.accounts_frozen_till_date = ""
		company.save()

	@ERPNextTestSuite.change_settings("Stock Reposting Settings", {"item_based_reposting": 0})
	def test_create_repost_entry_for_cancelled_document(self):
		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			get_multiple_items=True,
		)

		self.assertEqual(pr.docstatus, 1)
		self.assertFalse(frappe.db.exists("Repost Item Valuation", {"voucher_no": pr.name}))

		pr.load_from_db()

		pr.cancel()
		self.assertEqual(pr.docstatus, 2)
		self.assertTrue(frappe.db.exists("Repost Item Valuation", {"voucher_no": pr.name}))

	def test_repost_item_valuation_for_closing_stock_balance(self):
		from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import (
			prepare_closing_stock_balance,
		)

		doc = frappe.new_doc("Stock Closing Entry")
		doc.company = "_Test Company"
		doc.from_date = today()
		doc.to_date = today()
		doc.submit()

		prepare_closing_stock_balance(doc.name)

		doc.load_from_db()
		self.assertEqual(doc.docstatus, 1)
		self.assertEqual(doc.status, "Completed")

		riv = frappe.new_doc("Repost Item Valuation")
		riv.update(
			{
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC",
				"based_on": "Item and Warehouse",
				"posting_date": today(),
				"posting_time": "00:01:00",
			}
		)

		self.assertRaises(frappe.ValidationError, riv.save)
		doc.cancel()

	def test_recalculate_valuation_rate_for_purchase_receipt(self):
		item = self.make_item().name

		# receive item at rate 100
		pr = make_purchase_receipt(item_code=item, qty=1, rate=100)
		self.assertSLEs(pr, [{"incoming_rate": 100}])

		# change the rate from 100 to 150
		pr.load_from_db()
		pr.items[0].db_set(
			{
				"base_net_amount": 150,
				"net_rate": 150,
			}
		)

		# repost with recalculate valuation rate
		riv = frappe.get_doc(
			doctype="Repost Item Valuation",
			based_on="Transaction",
			voucher_type=pr.doctype,
			voucher_no=pr.name,
			recalculate_valuation_rate=1,
			posting_date=pr.posting_date,
			posting_time=pr.posting_time,
		)
		riv.submit()

		# incoming rate after reposting should be 150
		self.assertSLEs(pr, [{"incoming_rate": 150}])

	def test_recalculate_valuation_rate_for_stock_entry(self):
		item = self.make_item().name

		# receive item at rate 100
		se = make_stock_entry(item_code=item, target="_Test Warehouse - _TC", qty=1, rate=100)
		self.assertSLEs(se, [{"incoming_rate": 100}])

		# change the rate from 100 to 150
		se.items[0].db_set("basic_rate", 150)

		# repost with recalculate valuation rate
		riv = frappe.get_doc(
			doctype="Repost Item Valuation",
			based_on="Transaction",
			voucher_type=se.doctype,
			voucher_no=se.name,
			recalculate_valuation_rate=1,
			posting_date=se.posting_date,
			posting_time=se.posting_time,
		)
		riv.submit()

		# incoming rate after reposting should be 150
		self.assertSLEs(se, [{"incoming_rate": 150}])

	def test_remove_attached_file(self):
		item_code = make_item("_Test Remove Attached File Item", properties={"is_stock_item": 1})

		make_purchase_receipt(
			item_code=item_code.name,
			qty=1,
			rate=100,
		)

		pr1 = make_purchase_receipt(
			item_code=item_code.name,
			qty=1,
			rate=100,
			posting_date=add_days(today(), days=-1),
		)

		if docname := frappe.db.exists("Repost Item Valuation", {"voucher_no": pr1.name}):
			self.assertFalse(
				frappe.db.get_value(
					"File",
					{"attached_to_doctype": "Repost Item Valuation", "attached_to_name": docname},
					"name",
				)
			)
		else:
			repost_entries = create_item_wise_repost_entries(pr1.doctype, pr1.name)
			for entry in repost_entries:
				self.assertFalse(
					frappe.db.get_value(
						"File",
						{"attached_to_doctype": "Repost Item Valuation", "attached_to_name": entry.name},
						"name",
					)
				)
