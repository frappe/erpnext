# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, cstr, flt, nowdate, nowtime, today

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.utils import get_stock_and_account_balance
from erpnext.stock.doctype.item.test_item import create_item, make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import (
	ensure_parent_account,
	make_purchase_receipt,
)
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_batch_from_bundle,
	get_serial_nos_from_bundle,
	make_serial_batch_bundle,
)
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import (
	EmptyStockReconciliationItemsError,
	get_items,
)
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.stock_ledger import get_previous_sle, update_entries_after
from erpnext.stock.tests.test_utils import StockTestMixin
from erpnext.stock.utils import get_incoming_rate, get_stock_value_on, get_valuation_method


class TestStockReconciliation(FrappeTestCase, StockTestMixin):
	@classmethod
	def setUpClass(cls):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		frappe.set_user("Administrator")

		if not frappe.db.exists("Company", "_Test Company"):
			create_company("_Test Company")

		create_warehouse(
			warehouse_name="_Test Warehouse",
			company="_Test Company",
		)
		setup_defaults_data()
		create_batch_or_serial_no_items()
		super().setUpClass()
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)

	def tearDown(self):
		frappe.local.future_sle = {}
		frappe.flags.pop("dont_execute_stock_reposts", None)

	def test_reco_for_fifo(self):
		self._test_reco_sle_gle("FIFO")

	def test_reco_for_moving_average(self):
		self._test_reco_sle_gle("Moving Average")

	def _test_reco_sle_gle(self, valuation_method):
		item_code = self.make_item(properties={"valuation_method": valuation_method}).name

		se1, se2, se3 = insert_existing_sle(warehouse="Stores - TCP1", item_code=item_code)
		company = frappe.db.get_value("Warehouse", "Stores - TCP1", "company")
		# [[qty, valuation_rate, posting_date,
		# 		posting_time, expected_stock_value, bin_qty, bin_valuation]]

		input_data = [
			[50, 1000, "2012-12-26", "12:00"],
			[25, 900, "2012-12-26", "12:00"],
			["", 1000, "2012-12-20", "12:05"],
			[20, "", "2012-12-26", "12:05"],
			[0, "", "2012-12-31", "12:10"],
		]

		for d in input_data:
			last_sle = get_previous_sle(
				{
					"item_code": item_code,
					"warehouse": "Stores - TCP1",
					"posting_date": d[2],
					"posting_time": d[3],
				}
			)

			# submit stock reconciliation
			stock_reco = create_stock_reconciliation(
				item_code=item_code,
				qty=d[0],
				rate=d[1],
				posting_date=d[2],
				posting_time=d[3],
				warehouse="Stores - TCP1",
				company=company,
				expense_account="Stock Adjustment - TCP1",
			)

			# check stock value
			sle = frappe.db.sql(
				"""select * from `tabStock Ledger Entry`
				where voucher_type='Stock Reconciliation' and voucher_no=%s""",
				stock_reco.name,
				as_dict=1,
			)

			qty_after_transaction = flt(d[0]) if d[0] != "" else flt(last_sle.get("qty_after_transaction"))

			valuation_rate = flt(d[1]) if d[1] != "" else flt(last_sle.get("valuation_rate"))

			if qty_after_transaction == last_sle.get(
				"qty_after_transaction"
			) and valuation_rate == last_sle.get("valuation_rate"):
				self.assertFalse(sle)
			else:
				self.assertEqual(flt(sle[0].qty_after_transaction, 1), flt(qty_after_transaction, 1))
				self.assertEqual(flt(sle[0].stock_value, 1), flt(qty_after_transaction * valuation_rate, 1))

				# no gl entries
				self.assertTrue(
					frappe.db.get_value(
						"Stock Ledger Entry",
						{"voucher_type": "Stock Reconciliation", "voucher_no": stock_reco.name},
					)
				)

				acc_bal, stock_bal, wh_list = get_stock_and_account_balance(
					"Stock In Hand - TCP1", stock_reco.posting_date, stock_reco.company
				)
				self.assertEqual(flt(acc_bal, 1), flt(stock_bal, 1))

				stock_reco.cancel()

		se3.cancel()
		se2.cancel()
		se1.cancel()

	def test_get_items(self):
		create_warehouse(
			"_Test Warehouse Group 1",
			{"is_group": 1, "company": "_Test Company", "parent_warehouse": "All Warehouses - _TC"},
		)
		create_warehouse(
			"_Test Warehouse Ledger 1",
			{
				"is_group": 0,
				"parent_warehouse": "_Test Warehouse Group 1 - _TC",
				"company": "_Test Company",
			},
		)

		create_item(
			"_Test Stock Reco Item",
			is_stock_item=1,
			valuation_rate=100,
			warehouse="_Test Warehouse Ledger 1 - _TC",
			opening_stock=100,
		)

		items = get_items("_Test Warehouse Group 1 - _TC", nowdate(), nowtime(), "_Test Company")

		self.assertEqual(
			["_Test Stock Reco Item", "_Test Warehouse Ledger 1 - _TC", 100],
			[items[0]["item_code"], items[0]["warehouse"], items[0]["qty"]],
		)

	def test_stock_reco_for_serialized_item(self):
		to_delete_records = []

		# Add new serial nos
		serial_item_code = "Stock-Reco-Serial-Item-1"
		serial_warehouse = "_Test Warehouse for Stock Reco1 - _TC"

		sr = create_stock_reconciliation(
			item_code=serial_item_code, warehouse=serial_warehouse, qty=5, rate=200
		)

		serial_nos = frappe.get_doc(
			"Serial and Batch Bundle", sr.items[0].serial_and_batch_bundle
		).get_serial_nos()
		self.assertEqual(len(serial_nos), 5)

		args = {
			"item_code": serial_item_code,
			"warehouse": serial_warehouse,
			"qty": -5,
			"posting_date": add_days(sr.posting_date, 1),
			"posting_time": nowtime(),
			"serial_and_batch_bundle": sr.items[0].serial_and_batch_bundle,
		}

		valuation_rate = get_incoming_rate(args)
		self.assertEqual(valuation_rate, 200)

		to_delete_records.append(sr.name)

		sr = create_stock_reconciliation(
			item_code=serial_item_code, warehouse=serial_warehouse, qty=5, rate=300, serial_no=serial_nos
		)

		sn_doc = frappe.get_doc("Serial and Batch Bundle", sr.items[0].serial_and_batch_bundle)

		self.assertEqual(len(sn_doc.get_serial_nos()), 5)

		args = {
			"item_code": serial_item_code,
			"warehouse": serial_warehouse,
			"qty": -5,
			"posting_date": add_days(sr.posting_date, 1),
			"posting_time": nowtime(),
			"serial_and_batch_bundle": sr.items[0].serial_and_batch_bundle,
		}

		valuation_rate = get_incoming_rate(args)
		self.assertEqual(valuation_rate, 300)

		to_delete_records.append(sr.name)
		to_delete_records.reverse()

		for d in to_delete_records:
			stock_doc = frappe.get_doc("Stock Reconciliation", d)
			stock_doc.cancel()

	def test_stock_reco_for_batch_item(self):
		to_delete_records = []

		# Add new serial nos
		item_code = "Stock-Reco-batch-Item-123"
		warehouse = "_Test Warehouse for Stock Reco2 - _TC"
		self.make_item(
			item_code,
			frappe._dict(
				{
					"is_stock_item": 1,
					"has_batch_no": 1,
					"create_new_batch": 1,
					"batch_number_series": "SRBI123-.#####",
				}
			),
		)

		sr = create_stock_reconciliation(
			item_code=item_code, warehouse=warehouse, qty=5, rate=200, do_not_save=1
		)
		sr.save()
		sr.submit()
		sr.load_from_db()

		batch_no = get_batch_from_bundle(sr.items[0].serial_and_batch_bundle)
		self.assertTrue(batch_no)
		to_delete_records.append(sr.name)

		sr1 = create_stock_reconciliation(
			item_code=item_code, warehouse=warehouse, qty=6, rate=300, batch_no=batch_no
		)

		args = {
			"item_code": item_code,
			"warehouse": warehouse,
			"posting_date": nowdate(),
			"posting_time": nowtime(),
			"serial_and_batch_bundle": sr1.items[0].serial_and_batch_bundle,
		}

		valuation_rate = get_incoming_rate(args)
		self.assertEqual(valuation_rate, 300)
		to_delete_records.append(sr1.name)

		sr2 = create_stock_reconciliation(
			item_code=item_code, warehouse=warehouse, qty=0, rate=0, batch_no=batch_no
		)

		stock_value = get_stock_value_on(warehouse, nowdate(), item_code)
		self.assertEqual(stock_value, 0)
		to_delete_records.append(sr2.name)

		to_delete_records.reverse()
		for d in to_delete_records:
			stock_doc = frappe.get_doc("Stock Reconciliation", d)
			stock_doc.cancel()

	def test_stock_reco_for_serial_and_batch_item(self):
		item = create_item("_TestBatchSerialItemReco")
		item.has_batch_no = 1
		item.create_new_batch = 1
		item.has_serial_no = 1
		item.batch_number_series = "TBS-BATCH-.##"
		item.serial_no_series = "TBS-.####"
		item.save()

		warehouse = "_Test Warehouse for Stock Reco2 - _TC"

		sr = create_stock_reconciliation(item_code=item.item_code, warehouse=warehouse, qty=1, rate=100)

		batch_no = get_batch_from_bundle(sr.items[0].serial_and_batch_bundle)

		serial_nos = get_serial_nos_from_bundle(sr.items[0].serial_and_batch_bundle)
		self.assertEqual(len(serial_nos), 1)
		self.assertEqual(frappe.db.get_value("Serial No", serial_nos[0], "batch_no"), batch_no)

		sr.cancel()

		self.assertEqual(frappe.db.get_value("Serial No", serial_nos[0], "warehouse"), None)

	def test_stock_reco_for_serial_and_batch_item_with_future_dependent_entry(self):
		"""
		Behaviour: 1) Create Stock Reconciliation, which will be the origin document
		of a new batch having a serial no
		2) Create a Stock Entry that adds a serial no to the same batch following this
		Stock Reconciliation
		3) Cancel Stock Entry
		Expected Result: 3) Serial No only in the Stock Entry is Inactive and Batch qty decreases
		"""
		from erpnext.stock.doctype.batch.batch import get_batch_qty
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = create_item("_TestBatchSerialItemDependentReco")
		item.has_batch_no = 1
		item.create_new_batch = 1
		item.has_serial_no = 1
		item.batch_number_series = "TBSD-BATCH-.##"
		item.serial_no_series = "TBSD-.####"
		item.save()

		warehouse = "_Test Warehouse for Stock Reco2 - _TC"

		stock_reco = create_stock_reconciliation(
			item_code=item.item_code, warehouse=warehouse, qty=1, rate=100
		)
		batch_no = get_batch_from_bundle(stock_reco.items[0].serial_and_batch_bundle)
		reco_serial_no = get_serial_nos_from_bundle(stock_reco.items[0].serial_and_batch_bundle)[0]

		stock_entry = make_stock_entry(
			item_code=item.item_code, target=warehouse, qty=1, basic_rate=100, batch_no=batch_no
		)
		serial_no_2 = get_serial_nos_from_bundle(stock_entry.items[0].serial_and_batch_bundle)[0]

		# Check Batch qty after 2 transactions
		batch_qty = get_batch_qty(batch_no, warehouse, item.item_code)
		self.assertEqual(batch_qty, 2)

		# Cancel latest stock document
		stock_entry.cancel()

		# Check Batch qty after cancellation
		batch_qty = get_batch_qty(batch_no, warehouse, item.item_code)
		self.assertEqual(batch_qty, 1)

		# Check if Serial No from Stock Reconcilation is intact
		self.assertEqual(frappe.db.get_value("Serial No", reco_serial_no, "batch_no"), batch_no)
		self.assertTrue(frappe.db.get_value("Serial No", reco_serial_no, "warehouse"))

		# Check if Serial No from Stock Entry is Unlinked and Inactive
		self.assertFalse(frappe.db.get_value("Serial No", serial_no_2, "warehouse"))

		stock_reco.cancel()

	def test_customer_provided_items(self):
		item_code = "Stock-Reco-customer-Item-100"
		create_item(item_code, is_customer_provided_item=1, customer="_Test Customer", is_purchase_item=0)

		sr = create_stock_reconciliation(item_code=item_code, qty=10, rate=420)

		self.assertEqual(sr.get("items")[0].allow_zero_valuation_rate, 1)
		self.assertEqual(sr.get("items")[0].valuation_rate, 0)
		self.assertEqual(sr.get("items")[0].amount, 0)

	def test_backdated_stock_reco_qty_reposting(self):
		"""
		Test if a backdated stock reco recalculates future qty until next reco.
		-------------------------------------------
		Var		| Doc	|	Qty	| Balance
		-------------------------------------------
		PR5     | PR    |   10  |  10   (posting date: today-4) [backdated]
		SR5		| Reco	|	0	|	8	(posting date: today-4) [backdated]
		PR1		| PR	|	10	|	18	(posting date: today-3)
		PR2		| PR	|	1	|	19	(posting date: today-2)
		SR4		| Reco	|	0	|	6	(posting date: today-1) [backdated]
		PR3		| PR	|	1	|	7	(posting date: today) # can't post future PR
		"""
		item_code = self.make_item().name
		warehouse = "_Test Warehouse - _TC"

		frappe.flags.dont_execute_stock_reposts = True

		def assertBalance(doc, qty_after_transaction):
			sle_balance = frappe.db.get_value(
				"Stock Ledger Entry", {"voucher_no": doc.name, "is_cancelled": 0}, "qty_after_transaction"
			)
			self.assertEqual(sle_balance, qty_after_transaction)

		pr1 = make_purchase_receipt(
			item_code=item_code, warehouse=warehouse, qty=10, rate=100, posting_date=add_days(nowdate(), -3)
		)
		pr2 = make_purchase_receipt(
			item_code=item_code, warehouse=warehouse, qty=1, rate=100, posting_date=add_days(nowdate(), -2)
		)
		pr3 = make_purchase_receipt(
			item_code=item_code, warehouse=warehouse, qty=1, rate=100, posting_date=nowdate()
		)
		assertBalance(pr1, 10)
		assertBalance(pr3, 12)

		# post backdated stock reco in between
		sr4 = create_stock_reconciliation(
			item_code=item_code, warehouse=warehouse, qty=6, rate=100, posting_date=add_days(nowdate(), -1)
		)
		assertBalance(pr3, 7)

		# post backdated stock reco at the start
		sr5 = create_stock_reconciliation(
			item_code=item_code, warehouse=warehouse, qty=8, rate=100, posting_date=add_days(nowdate(), -4)
		)
		assertBalance(pr1, 18)
		assertBalance(pr2, 19)
		assertBalance(sr4, 6)  # check if future stock reco is unaffected

		# Make a backdated receipt and check only entries till first SR are affected
		pr5 = make_purchase_receipt(
			item_code=item_code, warehouse=warehouse, qty=10, rate=100, posting_date=add_days(nowdate(), -5)
		)
		assertBalance(pr5, 10)
		# check if future stock reco is unaffected
		assertBalance(sr4, 6)
		assertBalance(sr5, 8)

		# cancel backdated stock reco and check future impact
		sr5.cancel()
		assertBalance(pr1, 10)
		assertBalance(pr2, 11)
		assertBalance(sr4, 6)  # check if future stock reco is unaffected

	@change_settings("Stock Settings", {"allow_negative_stock": 0})
	def test_backdated_stock_reco_future_negative_stock(self):
		"""
		Test if a backdated stock reco causes future negative stock and is blocked.
		-------------------------------------------
		Var		| Doc	|	Qty	| Balance
		-------------------------------------------
		PR1		| PR	|	10	|	10		(posting date: today-2)
		SR3		| Reco	|	0	|	1		(posting date: today-1) [backdated & blocked]
		DN2		| DN	|	-2	|	8(-1)	(posting date: today)
		"""
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.stock_ledger import NegativeStockError

		item_code = self.make_item().name
		warehouse = "_Test Warehouse - _TC"

		pr1 = make_purchase_receipt(
			item_code=item_code, warehouse=warehouse, qty=10, rate=100, posting_date=add_days(nowdate(), -2)
		)
		dn2 = create_delivery_note(
			item_code=item_code, warehouse=warehouse, qty=2, rate=120, posting_date=nowdate()
		)

		pr1_balance = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": pr1.name, "is_cancelled": 0}, "qty_after_transaction"
		)
		dn2_balance = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": dn2.name, "is_cancelled": 0}, "qty_after_transaction"
		)
		self.assertEqual(pr1_balance, 10)
		self.assertEqual(dn2_balance, 8)

		# check if stock reco is blocked
		sr3 = create_stock_reconciliation(
			item_code=item_code,
			warehouse=warehouse,
			qty=1,
			rate=100,
			posting_date=add_days(nowdate(), -1),
			do_not_submit=True,
		)
		self.assertRaises(NegativeStockError, sr3.submit)

		# teardown
		sr3.cancel()
		dn2.cancel()
		pr1.cancel()

	@change_settings("Stock Settings", {"allow_negative_stock": 0})
	def test_backdated_stock_reco_cancellation_future_negative_stock(self):
		"""
		Test if a backdated stock reco cancellation that causes future negative stock is blocked.
		-------------------------------------------
		Var | Doc  | Qty | Balance
		-------------------------------------------
		SR  | Reco | 100 | 100     (posting date: today-1) (shouldn't be cancelled after DN)
		DN  | DN   | 100 |   0     (posting date: today)
		"""
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.stock_ledger import NegativeStockError

		item_code = self.make_item().name
		warehouse = "_Test Warehouse - _TC"

		sr = create_stock_reconciliation(
			item_code=item_code,
			warehouse=warehouse,
			qty=100,
			rate=100,
			posting_date=add_days(nowdate(), -1),
		)

		dn = create_delivery_note(
			item_code=item_code, warehouse=warehouse, qty=100, rate=120, posting_date=nowdate()
		)

		dn_balance = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": dn.name, "is_cancelled": 0}, "qty_after_transaction"
		)
		self.assertEqual(dn_balance, 0)

		# check if cancellation of stock reco is blocked
		self.assertRaises(NegativeStockError, sr.cancel)

		repost_exists = bool(
			frappe.db.exists("Repost Item Valuation", {"voucher_no": sr.name, "status": "Queued"})
		)
		self.assertFalse(repost_exists, msg="Negative stock validation not working on reco cancellation")

	def test_intermediate_sr_bin_update(self):
		"""Bin should show correct qty even for backdated entries.

		-------------------------------------------
		| creation | Var | Doc  | Qty | balance qty
		-------------------------------------------
		|  1       | SR  | Reco | 10  | 10     (posting date: today+10)
		|  3       | SR2 | Reco | 11  | 11     (posting date: today+11)
		|  2       | DN  | DN   | 5   | 6 <-- assert in BIN  (posting date: today+12)
		"""
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		frappe.db.rollback()

		# repost will make this test useless, qty should update in realtime without reposts
		frappe.flags.dont_execute_stock_reposts = True
		frappe.db.set_single_value("Stock Reposting Settings", "do_reposting_for_each_stock_transaction", 0)

		item_code = self.make_item().name
		warehouse = "_Test Warehouse - _TC"

		create_stock_reconciliation(
			item_code=item_code, warehouse=warehouse, qty=10, rate=100, posting_date=add_days(nowdate(), 10)
		)

		create_delivery_note(
			item_code=item_code, warehouse=warehouse, qty=5, rate=120, posting_date=add_days(nowdate(), 12)
		)
		old_bin_qty = frappe.db.get_value(
			"Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty"
		)

		create_stock_reconciliation(
			item_code=item_code, warehouse=warehouse, qty=11, rate=100, posting_date=add_days(nowdate(), 11)
		)
		new_bin_qty = frappe.db.get_value(
			"Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty"
		)

		self.assertEqual(old_bin_qty + 1, new_bin_qty)
		frappe.db.rollback()

	def test_valid_batch(self):
		create_batch_item_with_batch("Testing Batch Item 1", "001")
		create_batch_item_with_batch("Testing Batch Item 2", "002")

		doc = frappe.get_doc(
			{
				"doctype": "Serial and Batch Bundle",
				"item_code": "Testing Batch Item 1",
				"warehouse": "_Test Warehouse - _TC",
				"voucher_type": "Stock Reconciliation",
				"entries": [
					{
						"batch_no": "002",
						"qty": 1,
						"incoming_rate": 100,
					}
				],
			}
		)

		self.assertRaises(frappe.ValidationError, doc.save)

	def test_serial_no_cancellation(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		item = create_item("Stock-Reco-Serial-Item-9", is_stock_item=1)
		if not item.has_serial_no:
			item.has_serial_no = 1
			item.serial_no_series = "PSRS9.####"
			item.save()

		item_code = item.name
		warehouse = "_Test Warehouse - _TC"

		se1 = make_stock_entry(item_code=item_code, target=warehouse, qty=10, basic_rate=700)
		serial_nos = get_serial_nos_from_bundle(se1.items[0].serial_and_batch_bundle)
		# reduce 1 item
		serial_nos.pop()
		new_serial_nos = serial_nos

		sr = create_stock_reconciliation(
			item_code=item.name, warehouse=warehouse, serial_no=new_serial_nos, qty=9
		)
		sr.cancel()

		active_sr_no = frappe.get_all(
			"Serial No", filters={"item_code": item_code, "warehouse": warehouse, "status": "Active"}
		)

		self.assertEqual(len(active_sr_no), 10)

	def test_serial_no_creation_and_inactivation(self):
		item = create_item("_TestItemCreatedWithStockReco", is_stock_item=1)
		if not item.has_serial_no:
			item.has_serial_no = 1
			item.save()

		item_code = item.name
		warehouse = "_Test Warehouse - _TC"

		if not frappe.db.exists("Serial No", "SR-CREATED-SR-NO"):
			frappe.get_doc(
				{
					"doctype": "Serial No",
					"item_code": item_code,
					"serial_no": "SR-CREATED-SR-NO",
				}
			).insert()

		sr = create_stock_reconciliation(
			item_code=item.name,
			warehouse=warehouse,
			serial_no=["SR-CREATED-SR-NO"],
			qty=1,
			do_not_submit=True,
			rate=100,
		)
		sr.save()
		self.assertEqual(cstr(sr.items[0].current_serial_no), "")
		sr.submit()

		active_sr_no = frappe.get_all(
			"Serial No", filters={"item_code": item_code, "warehouse": warehouse, "status": "Active"}
		)
		self.assertEqual(len(active_sr_no), 1)

		sr.cancel()
		active_sr_no = frappe.get_all(
			"Serial No", filters={"item_code": item_code, "warehouse": warehouse, "status": "Active"}
		)
		self.assertEqual(len(active_sr_no), 0)

	def test_serial_no_batch_no_item(self):
		item = self.make_item(
			"Test Serial No Batch No Item",
			{
				"is_stock_item": 1,
				"has_serial_no": 1,
				"has_batch_no": 1,
				"serial_no_series": "SRS9.####",
				"batch_number_series": "BNS90.####",
				"create_new_batch": 1,
			},
		)

		warehouse = "_Test Warehouse - _TC"

		sr = create_stock_reconciliation(
			item_code=item.name,
			warehouse=warehouse,
			qty=1,
			rate=100,
		)

		sl_entry = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Stock Reconciliation", "voucher_no": sr.name},
			["actual_qty", "qty_after_transaction"],
			as_dict=1,
		)

		self.assertEqual(flt(sl_entry.actual_qty), 1.0)
		self.assertEqual(flt(sl_entry.qty_after_transaction), 1.0)

	@change_settings("Stock Reposting Settings", {"item_based_reposting": 0})
	def test_backdated_stock_reco_entry(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		item_code = self.make_item(
			"Test New Batch Item ABCV",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"batch_number_series": "BNS91.####",
				"create_new_batch": 1,
			},
		).name

		warehouse = "_Test Warehouse - _TC"

		# Added 100 Qty, Balace Qty 100
		se1 = make_stock_entry(
			item_code=item_code, posting_time="09:00:00", target=warehouse, qty=100, basic_rate=700
		)

		batch_no = get_batch_from_bundle(se1.items[0].serial_and_batch_bundle)

		# Removed 50 Qty, Balace Qty 50
		se2 = make_stock_entry(
			item_code=item_code,
			batch_no=batch_no,
			posting_time="10:00:00",
			source=warehouse,
			qty=50,
			basic_rate=700,
		)

		# Stock Reco for 100, Balace Qty 100
		stock_reco = create_stock_reconciliation(
			item_code=item_code,
			posting_time="11:00:00",
			warehouse=warehouse,
			batch_no=batch_no,
			qty=100,
			rate=100,
		)

		sle = frappe.get_all(
			"Stock Ledger Entry",
			filters={"is_cancelled": 0, "voucher_no": stock_reco.name, "actual_qty": ("<", 0)},
			fields=["actual_qty"],
		)

		self.assertEqual(flt(sle[0].actual_qty), flt(-50.0))

		# Removed 50 Qty, Balace Qty 50
		make_stock_entry(
			item_code=item_code,
			batch_no=batch_no,
			posting_time="12:00:00",
			source=warehouse,
			qty=50,
			basic_rate=700,
		)

		self.assertFalse(frappe.db.exists("Repost Item Valuation", {"voucher_no": stock_reco.name}))

		# Cancel the backdated Stock Entry se2,
		# Since Stock Reco entry in the future the Balace Qty should remain as it's (50)

		se2.cancel()

		sle = frappe.get_all(
			"Stock Ledger Entry",
			filters={"item_code": item_code, "warehouse": warehouse, "is_cancelled": 0},
			fields=["qty_after_transaction", "actual_qty", "voucher_type", "voucher_no"],
			order_by="posting_time desc, creation desc",
		)

		self.assertEqual(flt(sle[0].qty_after_transaction), flt(50.0))

		sle = frappe.get_all(
			"Stock Ledger Entry",
			filters={"is_cancelled": 0, "voucher_no": stock_reco.name, "actual_qty": ("<", 0)},
			fields=["actual_qty"],
		)

		self.assertEqual(flt(sle[0].actual_qty), flt(-100.0))

	def test_update_stock_reconciliation_while_reposting(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		item_code = self.make_item().name
		warehouse = "_Test Warehouse - _TC"

		# Stock Value => 100 * 100 = 10000
		make_stock_entry(
			item_code=item_code,
			target=warehouse,
			qty=100,
			basic_rate=100,
			posting_time="10:00:00",
		)

		# Stock Value => 100 * 200 = 20000
		# Value Change => 20000 - 10000 = 10000
		sr1 = create_stock_reconciliation(
			item_code=item_code,
			warehouse=warehouse,
			qty=100,
			rate=200,
			posting_time="12:00:00",
		)
		self.assertEqual(sr1.difference_amount, 10000)

		# Stock Value => 50 * 50 = 2500
		# Value Change => 2500 - 10000 = -7500
		sr2 = create_stock_reconciliation(
			item_code=item_code,
			warehouse=warehouse,
			qty=50,
			rate=50,
			posting_time="11:00:00",
		)
		self.assertEqual(sr2.difference_amount, -7500)

		sr1.load_from_db()
		self.assertEqual(sr1.difference_amount, 17500)

		sr2.cancel()
		sr1.load_from_db()
		self.assertEqual(sr1.difference_amount, 10000)

	def test_make_stock_zero_for_serial_batch_item(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		serial_item = self.make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "DJJ.####"}
		).name
		batch_item = self.make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"batch_number_series": "BDJJ.####",
				"create_new_batch": 1,
			}
		).name

		serial_batch_item = self.make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"batch_number_series": "ADJJ.####",
				"create_new_batch": 1,
				"has_serial_no": 1,
				"serial_no_series": "SN-ADJJ.####",
			}
		).name

		warehouse = "_Test Warehouse - _TC"

		for item_code in [serial_item, batch_item, serial_batch_item]:
			make_stock_entry(
				item_code=item_code,
				target=warehouse,
				qty=10,
				basic_rate=100,
			)

			_reco = create_stock_reconciliation(
				item_code=item_code,
				warehouse=warehouse,
				qty=0.0,
			)

			serial_batch_bundle = frappe.get_all(
				"Stock Ledger Entry",
				{"item_code": item_code, "warehouse": warehouse, "is_cancelled": 0, "voucher_no": _reco.name},
				"serial_and_batch_bundle",
			)

			self.assertEqual(len(serial_batch_bundle), 1)

			_reco.cancel()

			serial_batch_bundle = frappe.get_all(
				"Stock Ledger Entry",
				{"item_code": item_code, "warehouse": warehouse, "is_cancelled": 0, "voucher_no": _reco.name},
				"serial_and_batch_bundle",
			)

			self.assertEqual(len(serial_batch_bundle), 0)

	def test_backdated_purchase_receipt_with_stock_reco(self):
		item_code = self.make_item(
			properties={
				"is_stock_item": 1,
				"has_serial_no": 1,
				"serial_no_series": "TEST-SERIAL-.###",
			}
		).name

		warehouse = "_Test Warehouse - _TC"

		# Step - 1: Create a Backdated Purchase Receipt

		pr1 = make_purchase_receipt(
			item_code=item_code, warehouse=warehouse, qty=10, rate=100, posting_date=add_days(nowdate(), -3)
		)
		pr1.reload()

		serial_nos = sorted(get_serial_nos_from_bundle(pr1.items[0].serial_and_batch_bundle))[:5]

		# Step - 2: Create a Stock Reconciliation
		sr1 = create_stock_reconciliation(
			item_code=item_code,
			warehouse=warehouse,
			qty=5,
			serial_no=serial_nos,
		)

		data = frappe.get_all(
			"Stock Ledger Entry",
			fields=["serial_no", "actual_qty", "stock_value_difference"],
			filters={"voucher_no": sr1.name, "is_cancelled": 0},
			order_by="creation",
		)

		for d in data:
			if d.actual_qty < 0:
				self.assertEqual(d.actual_qty, -10.0)
				self.assertAlmostEqual(d.stock_value_difference, -1000.0)
			else:
				self.assertEqual(d.actual_qty, 5.0)
				self.assertAlmostEqual(d.stock_value_difference, 500.0)

		# Step - 3: Create a Purchase Receipt before the first Purchase Receipt
		make_purchase_receipt(
			item_code=item_code, warehouse=warehouse, qty=10, rate=200, posting_date=add_days(nowdate(), -5)
		)

		data = frappe.get_all(
			"Stock Ledger Entry",
			fields=["serial_no", "actual_qty", "stock_value_difference"],
			filters={"voucher_no": sr1.name, "is_cancelled": 0},
			order_by="creation",
		)

		for d in data:
			if d.actual_qty < 0:
				self.assertEqual(d.actual_qty, -20.0)
				self.assertAlmostEqual(d.stock_value_difference, -3000.0)
			else:
				self.assertEqual(d.actual_qty, 5.0)
				self.assertAlmostEqual(d.stock_value_difference, 500.0)

		active_serial_no = frappe.get_all("Serial No", filters={"status": "Active", "item_code": item_code})
		self.assertEqual(len(active_serial_no), 5)

	def test_balance_qty_for_batch_with_backdated_stock_reco_and_future_entries(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		item = self.make_item(
			"Test Batch Item Original Test",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TEST-BATCH-SRWFEE-.###",
			},
		)

		warehouse = "_Test Warehouse - _TC"
		se1 = make_stock_entry(
			item_code=item.name,
			target=warehouse,
			qty=50,
			basic_rate=100,
			posting_date=add_days(nowdate(), -2),
		)
		batch1 = get_batch_from_bundle(se1.items[0].serial_and_batch_bundle)

		se2 = make_stock_entry(
			item_code=item.name,
			target=warehouse,
			qty=50,
			basic_rate=100,
			posting_date=add_days(nowdate(), -2),
		)
		batch2 = get_batch_from_bundle(se2.items[0].serial_and_batch_bundle)

		se3 = make_stock_entry(
			item_code=item.name,
			target=warehouse,
			qty=100,
			basic_rate=100,
			posting_date=add_days(nowdate(), -2),
		)
		batch3 = get_batch_from_bundle(se3.items[0].serial_and_batch_bundle)

		se3 = make_stock_entry(
			item_code=item.name,
			target=warehouse,
			qty=100,
			basic_rate=100,
			posting_date=nowdate(),
		)

		sle = frappe.get_all(
			"Stock Ledger Entry",
			filters={
				"item_code": item.name,
				"warehouse": warehouse,
				"is_cancelled": 0,
				"voucher_no": se3.name,
			},
			fields=["qty_after_transaction"],
			order_by="posting_time desc, creation desc",
		)

		self.assertEqual(flt(sle[0].qty_after_transaction), flt(300.0))

		sr = create_stock_reconciliation(
			item_code=item.name,
			warehouse=warehouse,
			qty=0,
			batch_no=batch1,
			posting_date=add_days(nowdate(), -1),
			use_serial_batch_fields=1,
			do_not_save=1,
		)

		for batch in [batch2, batch3]:
			sr.append(
				"items",
				{
					"item_code": item.name,
					"warehouse": warehouse,
					"qty": 0,
					"batch_no": batch,
					"use_serial_batch_fields": 1,
				},
			)

		sr.save()
		sr.submit()

		sle = frappe.get_all(
			"Stock Ledger Entry",
			filters={
				"item_code": item.name,
				"warehouse": warehouse,
				"is_cancelled": 0,
				"voucher_no": se3.name,
			},
			fields=["qty_after_transaction"],
			order_by="posting_time desc, creation desc",
		)

		self.assertEqual(flt(sle[0].qty_after_transaction), flt(100.0))

	def test_stock_reco_and_backdated_purchase_receipt(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		item = self.make_item(
			"Test Batch Item Original STOCK RECO Test",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TEST-BATCH-SRCOSRWFEE-.###",
			},
		)

		warehouse = "_Test Warehouse - _TC"

		sr = create_stock_reconciliation(
			item_code=item.name,
			warehouse=warehouse,
			qty=100,
			rate=100,
		)

		sr.reload()
		self.assertTrue(sr.items[0].serial_and_batch_bundle)
		self.assertFalse(sr.items[0].current_serial_and_batch_bundle)
		batch = get_batch_from_bundle(sr.items[0].serial_and_batch_bundle)

		se1 = make_stock_entry(
			item_code=item.name,
			target=warehouse,
			qty=50,
			basic_rate=100,
			posting_date=add_days(nowdate(), -2),
		)

		batch1 = get_batch_from_bundle(se1.items[0].serial_and_batch_bundle)
		self.assertFalse(batch1 == batch)

		sr.reload()
		self.assertTrue(sr.items[0].serial_and_batch_bundle)
		self.assertTrue(sr.items[0].current_serial_and_batch_bundle)

	def test_not_reconcile_all_batch(self):
		from erpnext.stock.doctype.batch.batch import get_batch_qty
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		item = self.make_item(
			"Test Batch Item Not Reconcile All Serial Batch",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TEST-BATCH-NRALL-SRCOSRWFEE-.###",
			},
		)

		warehouse = "_Test Warehouse - _TC"

		batches = []
		for qty in [10, 20, 30]:
			se = make_stock_entry(
				item_code=item.name,
				target=warehouse,
				qty=qty,
				basic_rate=100 + qty,
				posting_date=nowdate(),
			)

			batch_no = get_batch_from_bundle(se.items[0].serial_and_batch_bundle)
			batches.append(frappe._dict({"batch_no": batch_no, "qty": qty}))

		sr = create_stock_reconciliation(
			item_code=item.name,
			warehouse=warehouse,
			qty=100,
			rate=1000,
			reconcile_all_serial_batch=0,
			batch_no=batches[0].batch_no,
		)

		sr.reload()
		self.assertEqual(sr.difference_amount, 98900.0)

		self.assertTrue(sr.items[0].current_valuation_rate)
		current_sabb = sr.items[0].current_serial_and_batch_bundle
		doc = frappe.get_doc("Serial and Batch Bundle", current_sabb)
		for row in doc.entries:
			self.assertEqual(row.batch_no, batches[0].batch_no)
			self.assertEqual(row.qty, batches[0].qty * -1)

		batch_qty = get_batch_qty(batches[0].batch_no, warehouse, item.name)
		self.assertEqual(batch_qty, 100)

		for row in frappe.get_all("Repost Item Valuation", filters={"voucher_no": sr.name}):
			rdoc = frappe.get_doc("Repost Item Valuation", row.name)
			rdoc.cancel()
			rdoc.delete()

		sr.cancel()

		for row in frappe.get_all(
			"Serial and Batch Bundle", fields=["docstatus"], filters={"voucher_no": sr.name}
		):
			self.assertEqual(row.docstatus, 2)

	def test_stock_reco_recalculate_qty_for_backdated_entry(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		item_code = self.make_item(
			"Test Batch Item Stock Reco Recalculate Qty",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TEST-BATCH-RRQ-.###",
			},
		).name

		warehouse = "_Test Warehouse - _TC"

		sr = create_stock_reconciliation(
			item_code=item_code,
			warehouse=warehouse,
			qty=10,
			rate=100,
			use_serial_batch_fields=1,
		)

		sr.reload()
		self.assertEqual(sr.items[0].current_qty, 0)
		self.assertEqual(sr.items[0].current_valuation_rate, 0)

		batch_no = get_batch_from_bundle(sr.items[0].serial_and_batch_bundle)
		stock_ledgers = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": sr.name, "is_cancelled": 0},
			pluck="name",
		)

		self.assertTrue(len(stock_ledgers) == 1)

		make_stock_entry(
			item_code=item_code,
			target=warehouse,
			qty=10,
			basic_rate=100,
			use_serial_batch_fields=1,
			batch_no=batch_no,
		)

		# Make backdated stock reconciliation entry
		create_stock_reconciliation(
			item_code=item_code,
			warehouse=warehouse,
			qty=10,
			rate=100,
			use_serial_batch_fields=1,
			batch_no=batch_no,
			posting_date=add_days(nowdate(), -1),
		)

		stock_ledgers = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": sr.name, "is_cancelled": 0},
			pluck="name",
		)

		sr.reload()
		self.assertEqual(sr.items[0].current_qty, 10)
		self.assertEqual(sr.items[0].current_valuation_rate, 100)

		self.assertTrue(len(stock_ledgers) == 2)

	def test_not_reconcile_all_serial_nos(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.utils import get_incoming_rate

		item = self.make_item(
			"Test Serial NO Item Not Reconcile All Serial Batch",
			{
				"is_stock_item": 1,
				"has_serial_no": 1,
				"serial_no_series": "SNN-TEST-BATCH-NRALL-S-.###",
			},
		)

		warehouse = "_Test Warehouse - _TC"

		serial_nos = []
		for qty in [5, 5, 5]:
			se = make_stock_entry(
				item_code=item.name,
				target=warehouse,
				qty=qty,
				basic_rate=100 + qty,
				posting_date=nowdate(),
			)

			serial_nos.extend(get_serial_nos_from_bundle(se.items[0].serial_and_batch_bundle))

		sr = create_stock_reconciliation(
			item_code=item.name,
			warehouse=warehouse,
			qty=5,
			rate=1000,
			reconcile_all_serial_batch=0,
			serial_no=serial_nos[0:5],
		)

		sr.reload()
		current_sabb = sr.items[0].current_serial_and_batch_bundle
		doc = frappe.get_doc("Serial and Batch Bundle", current_sabb)
		for row in doc.entries:
			self.assertEqual(row.serial_no, serial_nos[row.idx - 1])

		sabb = sr.items[0].serial_and_batch_bundle
		doc = frappe.get_doc("Serial and Batch Bundle", sabb)
		for row in doc.entries:
			self.assertEqual(row.qty, 1)
			self.assertAlmostEqual(row.incoming_rate, 1000.00)
			self.assertEqual(row.serial_no, serial_nos[row.idx - 1])

	def test_stock_reco_with_legacy_batch(self):
		from erpnext.stock.doctype.batch.batch import get_batch_qty

		batch_item_code = self.make_item(
			"Test Batch Item Legacy Batch 1",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "BH1-NRALL-S-.###",
			},
		).name

		warehouse = "_Test Warehouse - _TC"

		frappe.flags.ignore_serial_batch_bundle_validation = True
		frappe.flags.use_serial_and_batch_fields = True

		batch_id = "BH1-NRALL-S-0001"
		if not frappe.db.exists("Batch", batch_id):
			batch_doc = frappe.get_doc(
				{
					"doctype": "Batch",
					"batch_id": batch_id,
					"item": batch_item_code,
					"use_batchwise_valuation": 0,
				}
			).insert(ignore_permissions=True)

			self.assertTrue(batch_doc.use_batchwise_valuation)

		stock_queue = []
		qty_after_transaction = 0
		balance_value = 0
		i = 0
		for qty, valuation in {10: 100, 20: 200}.items():
			i += 1
			stock_queue.append([qty, valuation])
			qty_after_transaction += qty
			balance_value += qty_after_transaction * valuation

			doc = frappe.get_doc(
				{
					"doctype": "Stock Ledger Entry",
					"posting_date": add_days(nowdate(), -2 * i),
					"posting_time": nowtime(),
					"batch_no": batch_id,
					"incoming_rate": valuation,
					"qty_after_transaction": qty_after_transaction,
					"stock_value_difference": valuation * qty,
					"balance_value": balance_value,
					"valuation_rate": balance_value / qty_after_transaction,
					"actual_qty": qty,
					"item_code": batch_item_code,
					"warehouse": "_Test Warehouse - _TC",
					"stock_queue": json.dumps(stock_queue),
				}
			)

			doc.set_posting_datetime()
			doc.flags.ignore_permissions = True
			doc.flags.ignore_mandatory = True
			doc.flags.ignore_links = True
			doc.flags.ignore_validate = True
			doc.submit()
			doc.reload()

		frappe.flags.ignore_serial_batch_bundle_validation = False
		frappe.flags.use_serial_and_batch_fields = False

		batch_doc = frappe.get_doc("Batch", batch_id)

		qty = get_batch_qty(batch_id, warehouse, batch_item_code)
		self.assertEqual(qty, 30)

		sr = create_stock_reconciliation(
			item_code=batch_item_code,
			posting_date=add_days(nowdate(), -3),
			posting_time=nowtime(),
			warehouse=warehouse,
			qty=100,
			rate=1000,
			reconcile_all_serial_batch=0,
			batch_no=batch_id,
			use_serial_batch_fields=1,
		)

		self.assertEqual(sr.items[0].current_qty, 20)
		self.assertEqual(sr.items[0].qty, 100)

		qty = get_batch_qty(batch_id, warehouse, batch_item_code)
		self.assertEqual(qty, 110)

	def test_skip_reposting_for_entries_after_stock_reco(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		item_code = create_item("Test Item For Skip Reposting After Stock Reco", is_stock_item=1).name
		warehouse = "_Test Warehouse - _TC"
		make_stock_entry(
			posting_date="2024-11-01",
			posting_time="11:00",
			item_code=item_code,
			target=warehouse,
			qty=10,
			basic_rate=100,
		)
		create_stock_reconciliation(
			posting_date="2024-11-02",
			posting_time="11:00",
			item_code=item_code,
			warehouse=warehouse,
			qty=20,
			rate=100,
		)
		se = make_stock_entry(
			posting_date="2024-11-03",
			posting_time="11:00",
			item_code=item_code,
			source=warehouse,
			qty=15,
		)
		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": se.name, "is_cancelled": 0}, "stock_value_difference"
		)
		self.assertEqual(stock_value_difference, 1500.00 * -1)
		make_stock_entry(
			posting_date="2024-10-29",
			posting_time="11:00",
			item_code=item_code,
			target=warehouse,
			qty=10,
			basic_rate=100,
		)
		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": se.name, "is_cancelled": 0}, "stock_value_difference"
		)
		self.assertEqual(stock_value_difference, 1500.00 * -1)

	def test_stock_reco_for_negative_batch(self):
		from erpnext.stock.doctype.batch.batch import get_batch_qty
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		item_code = self.make_item(
			"Test Item For Negative Batch",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TEST-BATCH-NB-.###",
			},
		).name
		warehouse = "_Test Warehouse - _TC"
		se = make_stock_entry(
			posting_date="2024-11-01",
			posting_time="11:00",
			item_code=item_code,
			target=warehouse,
			qty=10,
			basic_rate=100,
		)
		batch_no = get_batch_from_bundle(se.items[0].serial_and_batch_bundle)
		se = make_stock_entry(
			posting_date="2024-11-01",
			posting_time="11:00",
			item_code=item_code,
			source=warehouse,
			qty=10,
			basic_rate=100,
			use_serial_batch_fields=1,
			batch_no=batch_no,
		)
		sles = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": se.name, "is_cancelled": 0},
		)
		# intentionally setting negative qty
		doc = frappe.get_doc("Stock Ledger Entry", sles[0].name)
		doc.db_set(
			{
				"actual_qty": -20,
				"qty_after_transaction": -10,
			}
		)
		sabb_doc = frappe.get_doc("Serial and Batch Bundle", doc.serial_and_batch_bundle)
		for row in sabb_doc.entries:
			row.db_set("qty", -20)
		batch_qty = get_batch_qty(batch_no, warehouse, item_code, consider_negative_batches=True)
		self.assertEqual(batch_qty, -10)
		sr = create_stock_reconciliation(
			posting_date="2024-11-02",
			posting_time="11:00",
			item_code=item_code,
			warehouse=warehouse,
			use_serial_batch_fields=1,
			batch_no=batch_no,
			qty=0,
			rate=100,
			do_not_submit=True,
		)
		self.assertEqual(sr.items[0].current_qty, -10)
		sr.submit()
		sr.reload()
		self.assertTrue(sr.items[0].current_serial_and_batch_bundle)
		self.assertFalse(sr.items[0].serial_and_batch_bundle)

	def test_stock_reco_batch_item_current_valuation(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		# Add new serial nos
		item_code = "Stock-Reco-batch-Item-1234"
		warehouse = "_Test Warehouse - _TC"
		self.make_item(
			item_code,
			frappe._dict(
				{
					"is_stock_item": 1,
					"has_batch_no": 1,
					"create_new_batch": 1,
					"batch_number_series": "JJ-SRI1234-.#####",
				}
			),
		)

		se = make_stock_entry(
			item_code=item_code,
			target=warehouse,
			qty=1,
			basic_rate=100,
		)

		batch_no = get_batch_from_bundle(se.items[0].serial_and_batch_bundle)

		sr = create_stock_reconciliation(
			item_code=item_code, warehouse=warehouse, qty=0, rate=100, do_not_save=1
		)

		sr.items[0].batch_no = batch_no
		sr.items[0].use_serial_batch_fields = 1
		sr.save()
		self.assertEqual(sr.items[0].current_valuation_rate, 100)
		self.assertEqual(sr.difference_amount, 100 * -1)
		self.assertTrue(sr.items[0].qty == 0)

	def test_create_stock_reconciliation_for_opening(self):
		frappe.db.set_value("Company", "_Test Company", "enable_perpetual_inventory", 1)
		frappe.db.set_value("Company", "_Test Company", "default_inventory_account", "Stock In Hand - _TC")
		sr = self._create_stock_reconciliation_for_opening()

		sr.save()
		sr.submit()

		self.assertEqual(sr.expense_account, "Temporary Opening - _TC")
		gl_temp_credit = frappe.db.get_value(
			"GL Entry", {"voucher_no": sr.name, "account": "Temporary Opening - _TC"}, "credit"
		)

		self.assertEqual(gl_temp_credit, 4000)

		gl_stock_debit = frappe.db.get_value(
			"GL Entry", {"voucher_no": sr.name, "account": "Stock In Hand - _TC"}, "debit"
		)
		self.assertEqual(gl_stock_debit, 4000)

		actual_qty, incoming_rate = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": sr.name, "voucher_type": "Stock Reconciliation", "warehouse": "Stores - _TC"},
			["qty_after_transaction", "valuation_rate"],
		)
		self.assertEqual(actual_qty, 10)
		self.assertEqual(incoming_rate, 100)

		actual_qty1, incoming_rate1 = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_no": sr.name,
				"voucher_type": "Stock Reconciliation",
				"warehouse": "Finished Goods - _TC",
			},
			["qty_after_transaction", "valuation_rate"],
		)
		self.assertEqual(actual_qty1, 20)
		self.assertEqual(incoming_rate1, 150)

		frappe.db.rollback()

	def _create_stock_reconciliation_for_opening(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import create_company

		item1 = create_item("_Test_reco1")
		item2 = create_item("_Test_reco2")
		create_company("_Test Company")
		sr = frappe.new_doc("Stock Reconciliation")
		sr.purpose = "Opening Stock"
		sr.posting_date = "2025-04-01"
		sr.posting_time = nowtime()
		sr.set_posting_time = 1
		sr.company = "_Test Company"
		sr.expense_account = frappe.db.get_value(
			"Account", {"is_group": 0, "company": sr.company, "account_type": "Temporary"}, "name"
		)
		sr.append(
			"items",
			{
				"item_code": item1,
				"warehouse": "Stores - _TC",
				"qty": 10,
				"valuation_rate": 100,
			},
		)
		sr.append(
			"items",
			{
				"item_code": item2,
				"warehouse": "Finished Goods - _TC",
				"qty": 20,
				"valuation_rate": 150,
			},
		)
		return sr

	def test_create_stock_reconciliation_invalid(self):
		sr = frappe.new_doc("Stock Reconciliation")
		sr.purpose = "Opening Stock"
		sr.posting_date = "2024-04-01"
		sr.posting_time = nowtime()
		sr.set_posting_time = 1
		sr.company = "PP Ltd"
		sr.expense_account = frappe.db.get_value(
			"Account", {"is_group": 0, "company": sr.company, "account_type": "Temporary"}, "name"
		)  # get_difference_account API ref.
		sr.append(
			"items",
			{
				"item_code": "Book",
				"warehouse": "Stores - PP Ltd",
				"qty": -10,
				"valuation_rate": -100,
			},
		)
		sr.append(
			"items",
			{
				"item_code": "Book",
				"warehouse": "Stores - PP Ltd",
				"qty": "ABC",
				"valuation_rate": "ABC",
			},
		)
		self.assertRaises(frappe.ValidationError, sr.save)

	# Verify Impact on Balance Sheet Reports
	def test_create_stock_reco_match_balance_sheet(self):
		from erpnext.accounts.utils import get_balance_on

		pre_stock_in_hand = get_balance_on(account="Stock In Hand - _TC")
		sr = frappe.new_doc("Stock Reconciliation")
		sr.purpose = "Opening Stock"
		sr.posting_date = "2024-04-01"
		sr.posting_time = nowtime()
		sr.set_posting_time = 1
		sr.company = "_Test Company"
		sr.expense_account = frappe.db.get_value(
			"Account", {"is_group": 0, "company": sr.company, "account_type": "Temporary"}, "name"
		)
		sr.append(
			"items",
			{
				"item_code": "_Test Serialized Item With Series",
				"warehouse": "_Test Warehouse - _TC",
				"qty": 14,
				"valuation_rate": 120,
			},
		)

		sr.save()
		sr.submit()

		gl_stock_debit = frappe.db.get_value(
			"GL Entry", {"voucher_no": sr.name, "account": "Stock In Hand - _TC"}, "debit_in_account_currency"
		)
		if not gl_stock_debit:
			gl_stock_debit = 0

		expected_stock_in_hand = pre_stock_in_hand + gl_stock_debit
		current_stock_in_hand = get_balance_on(account="Stock In Hand - _TC")
		self.assertEqual(current_stock_in_hand, expected_stock_in_hand)

	def test_stock_reconciliation_for_opening(self):
		frappe.db.set_value("Company", "_Test Company", "enable_perpetual_inventory", 1)
		frappe.db.set_value("Company", "_Test Company", "default_inventory_account", "Stock In Hand - _TC")
		sr = create_stock_reconciliation_for_opening()

		sr.save()
		sr.submit()

		self.assertEqual(sr.expense_account, "Temporary Opening - _TC")
		gl_temp_credit = frappe.db.get_value(
			"GL Entry", {"voucher_no": sr.name, "account": "Temporary Opening - _TC"}, "credit"
		)

		self.assertEqual(gl_temp_credit, 50000)

		gl_stock_debit = frappe.db.get_value(
			"GL Entry", {"voucher_no": sr.name, "account": "Stock In Hand - _TC"}, "debit"
		)
		self.assertEqual(gl_stock_debit, 50000)

		actual_qty, incoming_rate = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": sr.name, "voucher_type": "Stock Reconciliation", "warehouse": "Stores - _TC"},
			["qty_after_transaction", "valuation_rate"],
		)
		self.assertEqual(actual_qty, 100)
		self.assertEqual(incoming_rate, 500)

		frappe.db.rollback()

	def test_stock_reco_cancel_and_TC_SCK_051(self):
		warehouse = create_warehouse(
			"_Test reco Warehouse",
			{"parent_warehouse": "All Warehouses - _TC"},
		)

		item = create_item(
			"_Test Stock Reco Item",
			is_stock_item=1,
			valuation_rate=500,
			warehouse="_Test reco Warehouse - _TC",
		)

		stock_reco = create_stock_reconciliation(
			item_code=item.name,
			qty=100,
			rate=500,
			posting_date="2024-04-01",
			purpose="Opening Stock",
			warehouse=warehouse,
			expense_account="Temporary Opening - _TC",
		)

		sle = frappe.get_all(
			"Stock Ledger Entry",
			filters={"is_cancelled": 0, "voucher_no": stock_reco.name},
			fields=["qty_after_transaction", "actual_qty", "voucher_type", "voucher_no"],
		)
		self.assertEqual(flt(sle[0]["qty_after_transaction"], 1), 100)

		# stock reco after cancel
		stock_reco.cancel()
		cancel_sle = frappe.get_all(
			"Stock Ledger Entry",
			filters={"is_cancelled": 1, "voucher_no": stock_reco.name},
			fields=["qty_after_transaction", "actual_qty", "voucher_type", "voucher_no"],
			order_by="posting_time desc, creation desc",
		)
		self.assertEqual(flt(sle[0]["actual_qty"], 1), flt(cancel_sle[0]["qty_after_transaction"], 1))
		self.assertEqual(flt(cancel_sle[0]["actual_qty"], 1), -100)

	def test_stock_reco_for_serial_item_TC_SCK_146(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.test_stock_entry import create_company

		company = "_Test Company"
		create_company(company)

		app_name = "india_compliance"
		item_fields = {
			"item_name": "_Test Item146",
			"valuation_rate": 500,
			"has_serial_no": 1,
			"serial_no_series": "Test-SABBMRP-Sno.#####",
		}
		hsn_code = "888890"

		if app_name in frappe.get_installed_apps():
			if not frappe.db.exists("GST HSN Code", "888890"):
				frappe.get_doc(
					{"doctype": "GST HSN Code", "hsn_code": "888890", "description": "test"}
				).insert()

			item_fields["gst_hsn_code"] = hsn_code

		item = make_item("_Test Item146", item_fields)

		stock_reco = create_stock_reconciliation(
			item_code=item.name,
			qty=5,
			posting_date="2025-01-03",
			purpose="Stock Reconciliation",
			warehouse=create_warehouse("Stores-test", properties=None, company="_Test Company"),
			expense_account="Stock Adjustment - _TC",
		)
		self.assertIsNotNone(stock_reco.name)
		self.assertEqual(stock_reco.docstatus, 1)
		serial_nos = frappe.db.get_list(
			"Serial No", filters={"item_code": item.name}, fields=["name", "status"]
		)

		for serial in serial_nos:
			self.assertEqual(serial["status"], "Active", f"Serial No {serial['name']} is not Active")

	def test_has_change_in_serial_batch_detects_difference_TC_SCK_486(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		frappe.set_user("Administrator")
		# Step 1: Ensure test item exists with proper serial config
		if not frappe.db.exists("Item", "_Test Item Serial"):
			make_item(
				"_Test Item Serial",
				{
					"has_serial_no": 1,
					"is_stock_item": 1,
					"maintain_stock": 1,
					"serial_no_series": "SRL-.#####",
					"stock_uom": "Nos",
					"item_group": "All Item Groups",
				},
			)
		else:
			frappe.db.set_value(
				"Item",
				"_Test Item Serial",
				{"has_serial_no": 1, "serial_no_series": "SRL-.#####", "maintain_stock": 1},
			)
		# Step 2: Create warehouse
		warehouse = create_warehouse("_Test WH", company="_Test Company")

		company = frappe.get_doc("Company", "_Test Company")
		company_abbr = company.abbr
		parent_account = ensure_parent_account("Parent Stock Account", "_Test Company", company_abbr)
		w_account = create_account(
			account_name="Sub Stock Account",
			parent_account=parent_account,
			company="_Test Company",
			account_type="Stock",
			account_currency="INR",
		)

		frappe.db.set_value("Warehouse", warehouse, "account", w_account)

		# Step 3: Create Material Receipt to generate serial numbers
		make_stock_entry(
			item_code="_Test Item Serial",
			qty=2,
			target=warehouse,
			stock_entry_type="Material Receipt",
			basic_rate=100,
			is_submit=True,
		)
		serial_nos = frappe.get_all(
			"Serial No", filters={"item_code": "_Test Item Serial"}, pluck="name", limit=2
		)
		assert len(serial_nos) == 2, "Not enough serials created"
		serial_1, serial_2 = serial_nos
		# Step 4: Create 2 Serial and Batch Bundles with different serials
		bundle_1 = frappe.get_doc(
			{
				"doctype": "Serial and Batch Bundle",
				"item_code": "_Test Item Serial",
				"type_of_transaction": "Inward",
				"voucher_type": "Stock Reconciliation",
				"posting_date": nowdate(),
				"posting_time": nowtime(),
				"entries": [{"serial_no": serial_1}],
			}
		).insert()
		bundle_2 = frappe.get_doc(
			{
				"doctype": "Serial and Batch Bundle",
				"item_code": "_Test Item Serial",
				"type_of_transaction": "Inward",
				"voucher_type": "Stock Reconciliation",
				"posting_date": nowdate(),
				"posting_time": nowtime(),
				"entries": [{"serial_no": serial_2}],
			}
		).insert()
		# Step 5: Prepare row dict
		row = frappe._dict(
			{"serial_and_batch_bundle": bundle_1.name, "current_serial_and_batch_bundle": bundle_2.name}
		)
		# Step 6: Call method and assert results
		sr = frappe.new_doc("Stock Reconciliation")
		result = sr.has_change_in_serial_batch(row)
		self.assertTrue(result)
		self.assertIsNone(row.current_serial_and_batch_bundle)
		self.assertFalse(frappe.db.exists("Serial and Batch Bundle", bundle_2.name))

	def test_set_new_serial_and_batch_bundle_logic_TC_SCK_487(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		frappe.set_user("Administrator")

		# Create Item
		if not frappe.db.exists("Item", "_Test Item SBB"):
			make_item(
				"_Test Item SBB",
				{
					"has_serial_no": 1,
					"is_stock_item": 1,
					"maintain_stock": 1,
					"stock_uom": "Nos",
					"serial_no_series": "SRLSBB-.#####",
				},
			)

		warehouse = create_warehouse("_Test WH SBB", company="_Test Company")
		company = frappe.get_doc("Company", "_Test Company")
		company_abbr = company.abbr
		parent_account = ensure_parent_account("Parent Stock Account", "_Test Company", company_abbr)
		w_account = create_account(
			account_name="Sub Stock Account",
			parent_account=parent_account,
			company="_Test Company",
			account_type="Stock",
			account_currency="INR",
		)

		frappe.db.set_value("Warehouse", warehouse, "account", w_account)
		# Create Stock Entry to generate serials
		make_stock_entry(
			item_code="_Test Item SBB",
			qty=2,
			target=warehouse,
			stock_entry_type="Material Receipt",
			basic_rate=150,
			is_submit=True,
		)

		# Fetch generated serials
		serials = frappe.get_all("Serial No", filters={"item_code": "_Test Item SBB"}, pluck="name", limit=2)
		serial_1 = serials[0]

		# Create Serial and Batch Bundle (negative, to simulate outward)
		current_bundle = frappe.get_doc(
			{
				"doctype": "Serial and Batch Bundle",
				"item_code": "_Test Item SBB",
				"type_of_transaction": "Outward",
				"voucher_type": "Stock Entry",
				"posting_date": nowdate(),
				"posting_time": nowtime(),
				"warehouse": warehouse,
				"entries": [{"serial_no": serial_1, "qty": -1, "stock_value_difference": -150}],
			}
		)
		current_bundle.flags.ignore_permissions = True
		current_bundle.insert()
		current_bundle.calculate_qty_and_amount()
		current_bundle.save()

		# ---------- First run to trigger condition (current_bundle -> serial_and_batch_bundle) ----------
		doc = frappe.new_doc("Stock Reconciliation")
		doc.company = "_Test Company"
		doc.set(
			"items",
			[
				{
					"item_code": "_Test Item SBB",
					"warehouse": warehouse,
					"current_serial_and_batch_bundle": current_bundle.name,
					"serial_and_batch_bundle": None,
					"use_serial_batch_fields": 0,
					"qty": 1,
				}
			],
		)
		doc.set_new_serial_and_batch_bundle()

		# Save the bundle name
		item = doc.items[0]
		created_bundle = item.serial_and_batch_bundle

		# ---------- Second run to trigger (serial_and_batch_bundle present, qty/valuation_rate empty) ----------
		doc2 = frappe.new_doc("Stock Reconciliation")
		doc2.company = "_Test Company"
		doc2.set(
			"items",
			[
				{
					"item_code": "_Test Item SBB",
					"warehouse": warehouse,
					"serial_and_batch_bundle": created_bundle,
					"qty": 0,
					"valuation_rate": 0,
					"use_serial_batch_fields": 0,
				}
			],
		)
		doc2.set_new_serial_and_batch_bundle()

		item2 = doc2.items[0]
		bundle_doc = frappe.get_doc("Serial and Batch Bundle", created_bundle)
		bundle_doc.calculate_qty_and_amount()
		bundle_doc.save()

		doc2.set_new_serial_and_batch_bundle()
		item2 = doc2.items[0]
		expected_rate = bundle_doc.avg_rate

		self.assertEqual(item2.valuation_rate, expected_rate)

	def test_make_adjustment_entry_creates_sle_on_difference_TC_SCK_488(self):
		# Mock method to simulate stock difference
		def mock_get_stock_value_difference(item_code, warehouse, posting_date, posting_time, name):
			return 100  # Simulated non-zero stock difference

		# Patch the method
		import erpnext.stock.stock_ledger

		erpnext.stock.stock_ledger.get_stock_value_difference = mock_get_stock_value_difference

		# Create dummy reconciliation doc
		doc = frappe.new_doc("Stock Reconciliation")
		doc.posting_date = nowdate()
		doc.posting_time = "10:00:00"
		doc.name = "TEST-SR"

		# Dummy item row
		row = frappe._dict(
			{
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC",
			}
		)

		# Patch method to return fake SLE args
		doc.get_sle_for_items = lambda r: {
			"item_code": r.item_code,
			"warehouse": r.warehouse,
			"actual_qty": 10,
			"valuation_rate": 200,
		}

		sl_entries = []

		# Call method under test
		doc.make_adjustment_entry(row, sl_entries)

		# Assert
		self.assertEqual(len(sl_entries), 1)
		sle = sl_entries[0]
		self.assertEqual(sle["item_code"], "_Test Item")
		self.assertEqual(sle["stock_value_difference"], -100)
		self.assertEqual(sle["is_adjustment_entry"], 1)

	def test_make_adjustment_entry_skips_on_zero_difference_TC_SCK_489(self):
		# Patch to return zero difference
		import erpnext.stock.stock_ledger

		erpnext.stock.stock_ledger.get_stock_value_difference = lambda *args, **kwargs: 0

		doc = frappe.new_doc("Stock Reconciliation")
		doc.posting_date = nowdate()
		doc.posting_time = "10:00:00"
		doc.name = "TEST-SR-2"

		row = frappe._dict(
			{
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC",
			}
		)

		doc.get_sle_for_items = lambda r: {}

		sl_entries = []
		doc.make_adjustment_entry(row, sl_entries)

		self.assertEqual(sl_entries, [])  # should stay empty

	def test_update_valuation_rate_for_serial_no_applies_to_all_serials_TC_SCK_490(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		frappe.set_user("Administrator")

		# Ensure item exists
		if not frappe.db.exists("Item", "_Test Item UVRSN"):
			make_item(
				"_Test Item UVRSN",
				{
					"item_code": "_Test Item UVRSN",
					"has_serial_no": 1,
					"is_stock_item": 1,
					"stock_uom": "Nos",
					"serial_no_series": "SRLUVR-.#####",
				},
			)

		warehouse = create_warehouse("_Test WH UVRSN", company="_Test Company")
		company = frappe.get_doc("Company", "_Test Company")
		company_abbr = company.abbr
		parent_account = ensure_parent_account("Parent Stock Account", "_Test Company", company_abbr)
		w_account = create_account(
			account_name="Sub Stock Account",
			parent_account=parent_account,
			company="_Test Company",
			account_type="Stock",
			account_currency="INR",
		)

		frappe.db.set_value("Warehouse", warehouse, "account", w_account)
		# Material Receipt to create Serial Nos
		make_stock_entry(
			item_code="_Test Item UVRSN",
			qty=2,
			target=warehouse,
			basic_rate=100,
			stock_entry_type="Material Receipt",
			is_submit=True,
		)

		# Get the generated serial numbers
		serial_nos = frappe.get_all(
			"Serial No", filters={"item_code": "_Test Item UVRSN"}, pluck="name", limit=2
		)
		serial_no_str = "\n".join(serial_nos)

		# Create Stock Reconciliation with valuation_rate
		doc = frappe.new_doc("Stock Reconciliation")
		doc.company = "_Test Company"
		doc.docstatus = 1  # Submitted
		doc.set(
			"items",
			[
				{
					"item_code": "_Test Item UVRSN",
					"warehouse": warehouse,
					"serial_no": serial_no_str,
					"valuation_rate": 500,
				}
			],
		)

		# Call the method
		doc.update_valuation_rate_for_serial_no()

		# Assert all serial numbers got updated
		for sn in serial_nos:
			rate = frappe.db.get_value("Serial No", sn, "purchase_rate")
			self.assertEqual(rate, 500)

	def test_update_valuation_rate_for_serial_nos_respects_docstatus_and_rate_TC_SCK_491(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		frappe.set_user("Administrator")
		warehouse = create_warehouse("_Test WH UVRSN2", company="_Test Company")
		company = frappe.get_doc("Company", "_Test Company")
		company_abbr = company.abbr
		parent_account = ensure_parent_account("Parent Stock Account", "_Test Company", company_abbr)
		w_account = create_account(
			account_name="Sub Stock Account",
			parent_account=parent_account,
			company="_Test Company",
			account_type="Stock",
			account_currency="INR",
		)

		frappe.db.set_value("Warehouse", warehouse, "account", w_account)

		# Create item with serial numbers
		if not frappe.db.exists("Item", "_Test Item UVRSN2"):
			make_item(
				"_Test Item UVRSN2",
				{
					"item_code": "_Test Item UVRSN2",
					"has_serial_no": 1,
					"is_stock_item": 1,
					"stock_uom": "Nos",
					"serial_no_series": "SRLUVR2-.#####",
				},
			)

		# Material Receipt to generate serial numbers
		make_stock_entry(
			item_code="_Test Item UVRSN2",
			qty=1,
			target=warehouse,
			basic_rate=200,
			stock_entry_type="Material Receipt",
			is_submit=True,
		)

		# Fetch generated serial number
		serial_no = frappe.get_all(
			"Serial No", filters={"item_code": "_Test Item UVRSN2"}, pluck="name", limit=1
		)[0]

		# Prepare row with valuation_rate and current_valuation_rate
		row = frappe._dict({"valuation_rate": 750, "current_valuation_rate": 300})

		# Case 1: docstatus = 1 ➝ uses `valuation_rate`
		doc = frappe.new_doc("Stock Reconciliation")
		doc.docstatus = 1
		doc.update_valuation_rate_for_serial_nos(row, [serial_no])
		self.assertEqual(frappe.db.get_value("Serial No", serial_no, "purchase_rate"), 750)

		# Case 2: docstatus = 0 ➝ uses `current_valuation_rate`
		doc.docstatus = 0
		doc.update_valuation_rate_for_serial_nos(row, [serial_no])
		self.assertEqual(frappe.db.get_value("Serial No", serial_no, "purchase_rate"), 300)

		# Case 3: valuation_rate is None ➝ should skip update
		row_none = frappe._dict({"valuation_rate": None, "current_valuation_rate": None})
		doc.update_valuation_rate_for_serial_nos(row_none, [serial_no])
		# No assertion needed — this should simply not throw or update anything

	def test_merge_similar_item_serial_nos_merges_correctly_TC_SCK_492(self):
		doc = frappe.new_doc("Stock Reconciliation")

		sl_entries = [
			frappe._dict(
				{
					"item_code": "_Test Item",
					"warehouse": "_Test WH - _TC",
					"serial_no": "SRL-0001",
					"actual_qty": 1,
					"valuation_rate": 100,
					"qty_after_transaction": 1,
				}
			),
			frappe._dict(
				{
					"item_code": "_Test Item",
					"warehouse": "_Test WH - _TC",
					"serial_no": "SRL-0002",
					"actual_qty": 2,
					"valuation_rate": 200,
					"qty_after_transaction": 2,
				}
			),
			frappe._dict(
				{  # This should not merge due to missing serial no
					"item_code": "_Test Item",
					"warehouse": "_Test WH - _TC",
					"serial_no": "",
					"actual_qty": 3,
					"valuation_rate": 300,
					"qty_after_transaction": 3,
				}
			),
			frappe._dict(
				{  # This should not merge due to negative quantity
					"item_code": "_Test Item",
					"warehouse": "_Test WH - _TC",
					"serial_no": "SRL-0003",
					"actual_qty": -1,
					"valuation_rate": 400,
					"qty_after_transaction": 4,
				}
			),
		]

		result = doc.merge_similar_item_serial_nos(sl_entries)

		# Expecting 3 entries: 1 merged, 1 skipped (no serial), 1 skipped (negative qty)
		self.assertEqual(len(result), 3)

		# Find the merged entry
		merged = next(entry for entry in result if "\n" in (entry.serial_no or ""))

		self.assertEqual(merged.item_code, "_Test Item")
		self.assertEqual(merged.warehouse, "_Test WH - _TC")
		self.assertEqual(merged.actual_qty, 3)  # 1 + 2
		self.assertIn("SRL-0001", merged.serial_no)
		self.assertIn("SRL-0002", merged.serial_no)

		# Check recalculated valuation rate
		expected_total_amount = 1 * 100 + 2 * 200  # 500
		expected_valuation_rate = expected_total_amount / 3
		self.assertAlmostEqual(merged.valuation_rate, expected_valuation_rate)
		self.assertAlmostEqual(merged.incoming_rate, expected_valuation_rate)

	def test_get_items_for_populates_items_based_on_warehouse_TC_SCK_493(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		frappe.set_user("Administrator")

		item_code = "_Test Item GetItems"
		warehouse = create_warehouse("_Test Warehouse GI", company="_Test Company")
		company = frappe.get_doc("Company", "_Test Company")
		company_abbr = company.abbr
		parent_account = ensure_parent_account("Parent Stock Account", "_Test Company", company_abbr)
		w_account = create_account(
			account_name="Sub Stock Account",
			parent_account=parent_account,
			company="_Test Company",
			account_type="Stock",
			account_currency="INR",
		)

		frappe.db.set_value("Warehouse", warehouse, "account", w_account)

		if not frappe.db.exists("Item", item_code):
			make_item(item_code, {"is_stock_item": 1, "valuation_rate": 50})

		make_stock_entry(
			item_code=item_code,
			qty=5,
			target=warehouse,
			stock_entry_type="Material Receipt",
			basic_rate=50,
			is_submit=True,
		)

		doc = frappe.new_doc("Stock Reconciliation")
		doc.company = "_Test Company"
		doc.posting_date = nowdate()
		doc.posting_time = nowtime()

		doc.get_items_for(warehouse)

		self.assertGreater(len(doc.items), 0)

		item_row = doc.items[0]
		self.assertEqual(item_row.item_code, item_code)
		self.assertEqual(item_row.warehouse, warehouse)

	def test_submit_behavior_based_on_item_count_TC_SCK_494(self):
		frappe.set_user("Administrator")

		# Create test item and warehouse
		item_code = "_Test Item Submit"
		warehouse = create_warehouse("_Test WH Submit", company="_Test Company")
		if not frappe.db.exists("Item", item_code):
			make_item(item_code, {"is_stock_item": 1, "valuation_rate": 50})

		# len(items) > 100: should enqueue submit job
		doc2 = frappe.new_doc("Stock Reconciliation")
		doc2.company = "_Test Company"
		doc2.posting_date = nowdate()
		doc2.posting_time = nowtime()

		# Add 101 rows
		for _ in range(101):
			doc2.append(
				"items", {"item_code": item_code, "warehouse": warehouse, "qty": 1, "valuation_rate": 10}
			)

		# Mock queue_action to avoid actual enqueue
		doc2.queue_action = lambda *args, **kwargs: setattr(doc2, "__queued__", True)

		doc2.submit()

		self.assertTrue(getattr(doc2, "__queued__", False))  # Confirm queue was triggered
		self.assertEqual(doc2.docstatus, 0)

		doc2.cancel()
		self.assertTrue(getattr(doc2, "__queued__", False))  # Confirm queue was triggered

	@change_settings(
		"Stock Settings",
		{
			"enable_stock_reservation": 0,
			"allow_negative_stock": 1,
		},
	)
	def test_has_negative_stock_allowed_behavior_TC_SCK_495(self):
		frappe.set_user("Administrator")

		doc = frappe.new_doc("Stock Reconciliation")
		doc.company = "_Test Company"
		doc.set("items", [])
		self.assertTrue(doc.has_negative_stock_allowed())

		# Temporarily disable negative stock
		settings = frappe.get_single("Stock Settings")
		settings.allow_negative_stock = 0
		settings.save()

		doc = frappe.new_doc("Stock Reconciliation")
		doc.company = "_Test Company"
		doc.set(
			"items",
			[
				{
					"item_code": "_Test Item",
					"qty": 5,
					"current_qty": 5,
					"serial_and_batch_bundle": "Some-Bundle",
				}
			],
		)
		self.assertTrue(doc.has_negative_stock_allowed())

		# --- Case 3: Global disabled, and item does NOT satisfy condition
		doc.set(
			"items",
			[
				{
					"item_code": "_Test Item",
					"qty": 10,
					"current_qty": 5,
					"serial_and_batch_bundle": None,
					"batch_no": None,
				}
			],
		)
		self.assertFalse(doc.has_negative_stock_allowed())

	def test_get_item_and_warehouses_returns_correct_structure_TC_SCK_496(self):
		from frappe.utils.nestedset import get_descendants_of

		from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_item_and_warehouses

		frappe.set_user("Administrator")

		# Create group warehouse
		group_warehouse = create_warehouse("Test Group WH", {"is_group": 1}, company="_Test Company")
		# Create two child warehouses
		create_warehouse("Test Child WH 1", {"parent_warehouse": group_warehouse}, company="_Test Company")
		create_warehouse("Test Child WH 2", {"parent_warehouse": group_warehouse}, company="_Test Company")

		# Case 1: Group warehouse, expect children returned
		result = get_item_and_warehouses("_Test Item", group_warehouse)
		child_wh_names = [wh for wh in get_descendants_of("Warehouse", group_warehouse)]

		self.assertEqual(len(result), len(child_wh_names))
		self.assertTrue(all(r["warehouse"] in child_wh_names for r in result))
		self.assertTrue(all(r["item_code"] == "_Test Item" for r in result))

		# Case 2: Leaf warehouse
		# Ensure item exists
		if not frappe.db.exists("Item", "_Test Item W1"):
			make_item("_Test Item W1", {"is_stock_item": 1})

		# Create a leaf warehouse
		leaf_wh = create_warehouse("Test Leaf WH", {"is_group": 0}, company="_Test Company")

		# Confirm its is_group status
		self.assertFalse(frappe.get_cached_value("Warehouse", leaf_wh, "is_group"))

		# Now call the function
		result_leaf = get_item_and_warehouses("_Test Item W1", leaf_wh)

		# Assert
		self.assertEqual(len(result_leaf), 1)
		self.assertEqual(result_leaf[0].warehouse, leaf_wh)
		self.assertEqual(result_leaf[0].item_code, "_Test Item W1")

	def test_get_difference_account_returns_correct_account_TC_SCK_497(self):
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_difference_account

		company = "_Test Company"

		# Ensure parent account exists
		parent_account = frappe.db.get_value("Account", {"account_name": "Expenses", "company": company})
		if not parent_account:
			parent_account = create_account(
				account_name="Expenses",
				company=company,
				is_group=1,
				account_type="Expense Account",
				account_currency="INR",
			)

		# Create Stock Adjustment Account
		stock_adjustment_account = create_account(
			account_name="Stock Adjustment - _TC",
			company=company,
			account_type="Stock Adjustment",
			parent_account=parent_account,
		)

		frappe.db.set_value("Company", company, "stock_adjustment_account", stock_adjustment_account)

		# Validate Stock Reconciliation purpose returns correct account
		recon_account = get_difference_account("Stock Reconciliation", company)
		self.assertEqual(recon_account, stock_adjustment_account)

		# Create Temporary Account for other purpose
		temporary_account = create_account(
			account_name="Temporary Account - _TC",
			company=company,
			account_type="Temporary",
			parent_account=parent_account,
		)

		# Validate other purpose fallback
		other_account = get_difference_account("Other", company)
		self.assertEqual(other_account, temporary_account)


def create_stock_reconciliation_for_opening():
	item1 = create_item("OP-MB-001")

	sr = frappe.new_doc("Stock Reconciliation")
	sr.purpose = "Opening Stock"
	sr.posting_date = today()
	sr.posting_time = nowtime()
	sr.set_posting_time = 1
	sr.company = "_Test Company"
	sr.expense_account = frappe.db.get_value(
		"Account", {"is_group": 0, "company": sr.company, "account_type": "Temporary"}, "name"
	)  # get_difference_account API ref.
	sr.append(
		"items",
		{
			"item_code": item1,
			"warehouse": "Stores - _TC",
			"qty": 100,
			"valuation_rate": 500,
		},
	)
	sr.cost_center = frappe.get_cached_value("Company", sr.company, "cost_center") or frappe.get_cached_value(
		"Cost Center", {"is_group": 0, "company": sr.company}
	)
	return sr


def create_batch_item_with_batch(item_name, batch_id):
	batch_item_doc = create_item(item_name, is_stock_item=1)
	if not batch_item_doc.has_batch_no:
		batch_item_doc.has_batch_no = 1
		batch_item_doc.create_new_batch = 1
		batch_item_doc.save(ignore_permissions=True)

	if not frappe.db.exists("Batch", batch_id):
		b = frappe.new_doc("Batch")
		b.item = item_name
		b.batch_id = batch_id
		b.save()


def insert_existing_sle(warehouse, item_code="_Test Item"):
	from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

	se1 = make_stock_entry(
		posting_date="2012-12-15",
		posting_time="02:00",
		item_code=item_code,
		target=warehouse,
		qty=10,
		basic_rate=700,
	)

	se2 = make_stock_entry(
		posting_date="2012-12-25", posting_time="03:00", item_code=item_code, source=warehouse, qty=15
	)

	se3 = make_stock_entry(
		posting_date="2013-01-05",
		posting_time="07:00",
		item_code=item_code,
		target=warehouse,
		qty=15,
		basic_rate=1200,
	)

	return se1, se2, se3


def create_batch_or_serial_no_items():
	frappe.set_user("Administrator")
	create_warehouse(
		"_Test Warehouse for Stock Reco1",
		{"is_group": 0, "parent_warehouse": "_Test Warehouse Group - _TC"},
	)

	create_warehouse(
		"_Test Warehouse for Stock Reco2",
		{"is_group": 0, "parent_warehouse": "_Test Warehouse Group - _TC"},
	)

	serial_item_doc = create_item("Stock-Reco-Serial-Item-1", is_stock_item=1)
	if not serial_item_doc.has_serial_no:
		serial_item_doc.has_serial_no = 1
		serial_item_doc.serial_no_series = "SRSI.####"
		serial_item_doc.save(ignore_permissions=True)

	serial_item_doc = create_item("Stock-Reco-Serial-Item-2", is_stock_item=1)
	if not serial_item_doc.has_serial_no:
		serial_item_doc.has_serial_no = 1
		serial_item_doc.serial_no_series = "SRSII.####"
		serial_item_doc.save(ignore_permissions=True)

	batch_item_doc = create_item("Stock-Reco-batch-Item-1", is_stock_item=1)
	if not batch_item_doc.has_batch_no:
		batch_item_doc.has_batch_no = 1
		batch_item_doc.create_new_batch = 1
		serial_item_doc.batch_number_series = "BASR.#####"
		batch_item_doc.save(ignore_permissions=True)


def create_stock_reconciliation(**args):
	args = frappe._dict(args)
	sr = frappe.new_doc("Stock Reconciliation")
	sr.purpose = args.purpose or "Stock Reconciliation"
	sr.posting_date = args.posting_date or nowdate()
	sr.posting_time = args.posting_time or nowtime()
	sr.set_posting_time = 1
	sr.company = args.company or "_Test Company"
	sr.expense_account = args.expense_account or (
		(
			frappe.get_cached_value("Company", sr.company, "stock_adjustment_account")
			or frappe.get_cached_value(
				"Account", {"account_type": "Stock Adjustment", "company": sr.company}, "name"
			)
		)
		if frappe.get_all("Stock Ledger Entry", {"company": sr.company})
		else frappe.get_cached_value("Account", {"account_type": "Temporary", "company": sr.company}, "name")
	)
	sr.cost_center = (
		args.cost_center
		or frappe.get_cached_value("Company", sr.company, "cost_center")
		or frappe.get_cached_value("Cost Center", filters={"is_group": 0, "company": sr.company})
	)

	bundle_id = None
	if not args.use_serial_batch_fields and (args.batch_no or args.serial_no) and args.qty:
		batches = frappe._dict({})
		if args.batch_no:
			batches[args.batch_no] = args.qty

		bundle_id = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": args.item_code or "_Test Item",
					"warehouse": args.warehouse or "_Test Warehouse - _TC",
					"qty": args.qty,
					"voucher_type": "Stock Reconciliation",
					"batches": batches,
					"rate": args.rate,
					"serial_nos": args.serial_no,
					"posting_date": sr.posting_date,
					"posting_time": sr.posting_time,
					"type_of_transaction": "Inward" if args.qty > 0 else "Outward",
					"company": args.company or "_Test Company",
					"do_not_submit": True,
				}
			)
		).name

	if args.reconcile_all_serial_batch is None:
		args.reconcile_all_serial_batch = 1

	sr.append(
		"items",
		{
			"item_code": args.item_code or "_Test Item",
			"warehouse": args.warehouse or "_Test Warehouse - _TC",
			"qty": args.qty,
			"reconcile_all_serial_batch": args.reconcile_all_serial_batch,
			"valuation_rate": args.rate,
			"serial_no": args.serial_no if args.use_serial_batch_fields else None,
			"batch_no": args.batch_no if args.use_serial_batch_fields else None,
			"serial_and_batch_bundle": bundle_id,
			"use_serial_batch_fields": args.use_serial_batch_fields,
		},
	)

	if not args.do_not_save:
		sr.insert()
		try:
			if not args.do_not_submit:
				sr.submit()
		except EmptyStockReconciliationItemsError:
			pass

		sr.load_from_db()

	return sr


def set_valuation_method(item_code, valuation_method):
	existing_valuation_method = get_valuation_method(item_code)
	if valuation_method == existing_valuation_method:
		return

	frappe.db.set_value("Item", item_code, "valuation_method", valuation_method)

	for warehouse in frappe.get_all(
		"Warehouse", filters={"company": "_Test Company"}, fields=["name", "is_group"]
	):
		if not warehouse.is_group:
			update_entries_after(
				{"item_code": item_code, "warehouse": warehouse.name}, allow_negative_stock=1
			)


test_dependencies = ["Item", "Warehouse"]


def setup_defaults_data():
	from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
	from erpnext.accounts.doctype.account.test_account import create_account
	from erpnext.stock import get_warehouse_account_map
	create_company()
	acc = create_account(
		account_name="Stock Assets",
		account_type="Stock",
		company="_Test Company",
		is_group=1,
		parent_account = "Current Assets - _TC",
		account_currency="INR",
		do_not_save=True,
	)
	acc.report_type = "Balance Sheet"
	acc.root_type = "Asset"
	acc.save()
	company_doc = frappe.get_doc("Company", "_Test Company")
	frappe._set_document_in_cache("Company", company_doc)
	get_warehouse_account_map(company=company_doc.name)