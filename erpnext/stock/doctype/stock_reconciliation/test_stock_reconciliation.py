# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt


import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, cstr, flt, nowdate, nowtime, random_string

from erpnext.accounts.utils import get_stock_and_account_balance
from erpnext.stock.doctype.item.test_item import create_item, make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import (
	EmptyStockReconciliationItemsError,
	get_items,
)
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.stock_ledger import get_previous_sle, update_entries_after
from erpnext.stock.utils import get_incoming_rate, get_stock_value_on, get_valuation_method


class TestStockReconciliation(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		create_batch_or_serial_no_items()
		super().setUpClass()
		frappe.db.set_value("Stock Settings", None, "allow_negative_stock", 1)

	def tearDown(self):
		frappe.local.future_sle = {}

	def test_reco_for_fifo(self):
		self._test_reco_sle_gle("FIFO")

	def test_reco_for_moving_average(self):
		self._test_reco_sle_gle("Moving Average")

	def _test_reco_sle_gle(self, valuation_method):
		item_code = make_item(properties={"valuation_method": valuation_method}).name

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
						"Stock Ledger Entry", {"voucher_type": "Stock Reconciliation", "voucher_no": stock_reco.name}
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
		to_delete_serial_nos = []

		# Add new serial nos
		serial_item_code = "Stock-Reco-Serial-Item-1"
		serial_warehouse = "_Test Warehouse for Stock Reco1 - _TC"

		sr = create_stock_reconciliation(
			item_code=serial_item_code, warehouse=serial_warehouse, qty=5, rate=200
		)

		serial_nos = get_serial_nos(sr.items[0].serial_no)
		self.assertEqual(len(serial_nos), 5)

		args = {
			"item_code": serial_item_code,
			"warehouse": serial_warehouse,
			"posting_date": nowdate(),
			"posting_time": nowtime(),
			"serial_no": sr.items[0].serial_no,
		}

		valuation_rate = get_incoming_rate(args)
		self.assertEqual(valuation_rate, 200)

		to_delete_records.append(sr.name)

		sr = create_stock_reconciliation(
			item_code=serial_item_code, warehouse=serial_warehouse, qty=5, rate=300
		)

		serial_nos1 = get_serial_nos(sr.items[0].serial_no)
		self.assertEqual(len(serial_nos1), 5)

		args = {
			"item_code": serial_item_code,
			"warehouse": serial_warehouse,
			"posting_date": nowdate(),
			"posting_time": nowtime(),
			"serial_no": sr.items[0].serial_no,
		}

		valuation_rate = get_incoming_rate(args)
		self.assertEqual(valuation_rate, 300)

		to_delete_records.append(sr.name)
		to_delete_records.reverse()

		for d in to_delete_records:
			stock_doc = frappe.get_doc("Stock Reconciliation", d)
			stock_doc.cancel()

	def test_stock_reco_for_merge_serialized_item(self):
		to_delete_records = []

		# Add new serial nos
		serial_item_code = "Stock-Reco-Serial-Item-2"
		serial_warehouse = "_Test Warehouse for Stock Reco1 - _TC"

		sr = create_stock_reconciliation(
			item_code=serial_item_code,
			serial_no=random_string(6),
			warehouse=serial_warehouse,
			qty=1,
			rate=100,
			do_not_submit=True,
			purpose="Opening Stock",
		)

		for i in range(3):
			sr.append(
				"items",
				{
					"item_code": serial_item_code,
					"warehouse": serial_warehouse,
					"qty": 1,
					"valuation_rate": 100,
					"serial_no": random_string(6),
				},
			)

		sr.save()
		sr.submit()

		sle_entries = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": sr.name}, fields=["name", "incoming_rate"]
		)

		self.assertEqual(len(sle_entries), 1)
		self.assertEqual(sle_entries[0].incoming_rate, 100)

		to_delete_records.append(sr.name)
		to_delete_records.reverse()

		for d in to_delete_records:
			stock_doc = frappe.get_doc("Stock Reconciliation", d)
			stock_doc.cancel()

	def test_stock_reco_for_batch_item(self):
		to_delete_records = []

		# Add new serial nos
		item_code = "Stock-Reco-batch-Item-1"
		warehouse = "_Test Warehouse for Stock Reco2 - _TC"

		sr = create_stock_reconciliation(
			item_code=item_code, warehouse=warehouse, qty=5, rate=200, do_not_submit=1
		)
		sr.save()
		sr.submit()

		batch_no = sr.items[0].batch_no
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
			"batch_no": batch_no,
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

	def test_customer_provided_items(self):
		item_code = "Stock-Reco-customer-Item-100"
		create_item(
			item_code, is_customer_provided_item=1, customer="_Test Customer", is_purchase_item=0
		)

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
		SR5		| Reco	|	0	|	8	(posting date: today-4) [backdated]
		PR1		| PR	|	10	|	18	(posting date: today-3)
		PR2		| PR	|	1	|	19	(posting date: today-2)
		SR4		| Reco	|	0	|	6	(posting date: today-1) [backdated]
		PR3		| PR	|	1	|	7	(posting date: today) # can't post future PR
		"""
		item_code = make_item().name
		warehouse = "_Test Warehouse - _TC"

		pr1 = make_purchase_receipt(
			item_code=item_code, warehouse=warehouse, qty=10, rate=100, posting_date=add_days(nowdate(), -3)
		)
		pr2 = make_purchase_receipt(
			item_code=item_code, warehouse=warehouse, qty=1, rate=100, posting_date=add_days(nowdate(), -2)
		)
		pr3 = make_purchase_receipt(
			item_code=item_code, warehouse=warehouse, qty=1, rate=100, posting_date=nowdate()
		)

		pr1_balance = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": pr1.name, "is_cancelled": 0}, "qty_after_transaction"
		)
		pr3_balance = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": pr3.name, "is_cancelled": 0}, "qty_after_transaction"
		)
		self.assertEqual(pr1_balance, 10)
		self.assertEqual(pr3_balance, 12)

		# post backdated stock reco in between
		sr4 = create_stock_reconciliation(
			item_code=item_code, warehouse=warehouse, qty=6, rate=100, posting_date=add_days(nowdate(), -1)
		)
		pr3_balance = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": pr3.name, "is_cancelled": 0}, "qty_after_transaction"
		)
		self.assertEqual(pr3_balance, 7)

		# post backdated stock reco at the start
		sr5 = create_stock_reconciliation(
			item_code=item_code, warehouse=warehouse, qty=8, rate=100, posting_date=add_days(nowdate(), -4)
		)
		pr1_balance = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": pr1.name, "is_cancelled": 0}, "qty_after_transaction"
		)
		pr2_balance = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": pr2.name, "is_cancelled": 0}, "qty_after_transaction"
		)
		sr4_balance = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": sr4.name, "is_cancelled": 0}, "qty_after_transaction"
		)
		self.assertEqual(pr1_balance, 18)
		self.assertEqual(pr2_balance, 19)
		self.assertEqual(sr4_balance, 6)  # check if future stock reco is unaffected

		# cancel backdated stock reco and check future impact
		sr5.cancel()
		pr1_balance = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": pr1.name, "is_cancelled": 0}, "qty_after_transaction"
		)
		pr2_balance = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": pr2.name, "is_cancelled": 0}, "qty_after_transaction"
		)
		sr4_balance = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": sr4.name, "is_cancelled": 0}, "qty_after_transaction"
		)
		self.assertEqual(pr1_balance, 10)
		self.assertEqual(pr2_balance, 11)
		self.assertEqual(sr4_balance, 6)  # check if future stock reco is unaffected

		# teardown
		sr4.cancel()
		pr3.cancel()
		pr2.cancel()
		pr1.cancel()

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

		item_code = make_item().name
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

		item_code = make_item().name
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

		repost_exists = bool(frappe.db.exists("Repost Item Valuation", {"voucher_no": sr.name}))
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
		self.addCleanup(frappe.flags.pop, "dont_execute_stock_reposts")

		item_code = make_item().name
		warehouse = "_Test Warehouse - _TC"

		sr = create_stock_reconciliation(
			item_code=item_code, warehouse=warehouse, qty=10, rate=100, posting_date=add_days(nowdate(), 10)
		)

		dn = create_delivery_note(
			item_code=item_code, warehouse=warehouse, qty=5, rate=120, posting_date=add_days(nowdate(), 12)
		)
		old_bin_qty = frappe.db.get_value(
			"Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty"
		)

		sr2 = create_stock_reconciliation(
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
		sr = create_stock_reconciliation(
			item_code="Testing Batch Item 1", qty=1, rate=100, batch_no="002", do_not_submit=True
		)
		self.assertRaises(frappe.ValidationError, sr.submit)

	def test_serial_no_cancellation(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		item = create_item("Stock-Reco-Serial-Item-9", is_stock_item=1)
		if not item.has_serial_no:
			item.has_serial_no = 1
			item.serial_no_series = "SRS9.####"
			item.save()

		item_code = item.name
		warehouse = "_Test Warehouse - _TC"

		se1 = make_stock_entry(item_code=item_code, target=warehouse, qty=10, basic_rate=700)

		serial_nos = get_serial_nos(se1.items[0].serial_no)
		# reduce 1 item
		serial_nos.pop()
		new_serial_nos = "\n".join(serial_nos)

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

		sr = create_stock_reconciliation(
			item_code=item.name,
			warehouse=warehouse,
			serial_no="SR-CREATED-SR-NO",
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
		"Stock Adjustment - _TC" if frappe.get_all("Stock Ledger Entry") else "Temporary Opening - _TC"
	)
	sr.cost_center = (
		args.cost_center
		or frappe.get_cached_value("Company", sr.company, "cost_center")
		or "_Test Cost Center - _TC"
	)

	sr.append(
		"items",
		{
			"item_code": args.item_code or "_Test Item",
			"warehouse": args.warehouse or "_Test Warehouse - _TC",
			"qty": args.qty,
			"valuation_rate": args.rate,
			"serial_no": args.serial_no,
			"batch_no": args.batch_no,
		},
	)

	try:
		if not args.do_not_submit:
			sr.submit()
	except EmptyStockReconciliationItemsError:
		pass
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
