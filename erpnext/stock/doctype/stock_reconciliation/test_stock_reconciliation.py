# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt


import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, cstr, flt, nowdate, nowtime

from erpnext.accounts.utils import get_stock_and_account_balance
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
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
		self.assertFalse(sr.items[0].current_serial_and_batch_bundle)

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
