# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, unittest
from frappe.utils import flt, nowdate, nowtime
from erpnext.accounts.utils import get_stock_and_account_balance
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import set_perpetual_inventory
from erpnext.stock.stock_ledger import get_previous_sle, update_entries_after
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import EmptyStockReconciliationItemsError, get_items
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.utils import get_stock_balance, get_incoming_rate, get_available_serial_nos, get_stock_value_on
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

class TestStockReconciliation(unittest.TestCase):
	@classmethod
	def setUpClass(self):
		create_batch_or_serial_no_items()
		frappe.db.set_value("Stock Settings", None, "allow_negative_stock", 1)

	def test_reco_for_fifo(self):
		self._test_reco_sle_gle("FIFO")

	def test_reco_for_moving_average(self):
		self._test_reco_sle_gle("Moving Average")

	def _test_reco_sle_gle(self, valuation_method):
		insert_existing_sle(warehouse='Stores - TCP1')
		company = frappe.db.get_value('Warehouse', 'Stores - TCP1', 'company')
		# [[qty, valuation_rate, posting_date,
		#		posting_time, expected_stock_value, bin_qty, bin_valuation]]
		input_data = [
			[50, 1000, "2012-12-26", "12:00"],
			[25, 900, "2012-12-26", "12:00"],
			["", 1000, "2012-12-20", "12:05"],
			[20, "", "2012-12-26", "12:05"],
			[0, "", "2012-12-31", "12:10"]
		]

		for d in input_data:
			set_valuation_method("_Test Item", valuation_method)

			last_sle = get_previous_sle({
				"item_code": "_Test Item",
				"warehouse": "Stores - TCP1",
				"posting_date": d[2],
				"posting_time": d[3]
			})

			# submit stock reconciliation
			stock_reco = create_stock_reconciliation(qty=d[0], rate=d[1],
				posting_date=d[2], posting_time=d[3], warehouse="Stores - TCP1",
				company=company, expense_account = "Stock Adjustment - TCP1")

			# check stock value
			sle = frappe.db.sql("""select * from `tabStock Ledger Entry`
				where voucher_type='Stock Reconciliation' and voucher_no=%s""", stock_reco.name, as_dict=1)

			qty_after_transaction = flt(d[0]) if d[0] != "" else flt(last_sle.get("qty_after_transaction"))

			valuation_rate = flt(d[1]) if d[1] != "" else flt(last_sle.get("valuation_rate"))

			if qty_after_transaction == last_sle.get("qty_after_transaction") \
				and valuation_rate == last_sle.get("valuation_rate"):
					self.assertFalse(sle)
			else:
				self.assertEqual(sle[0].qty_after_transaction, qty_after_transaction)
				self.assertEqual(sle[0].stock_value, qty_after_transaction * valuation_rate)

				# no gl entries
				self.assertTrue(frappe.db.get_value("Stock Ledger Entry",
					{"voucher_type": "Stock Reconciliation", "voucher_no": stock_reco.name}))

				acc_bal, stock_bal, wh_list = get_stock_and_account_balance("Stock In Hand - TCP1",
					stock_reco.posting_date, stock_reco.company)
				self.assertEqual(acc_bal, stock_bal)

				stock_reco.cancel()

				self.assertFalse(frappe.db.get_value("Stock Ledger Entry",
					{"voucher_type": "Stock Reconciliation", "voucher_no": stock_reco.name}))

				self.assertFalse(frappe.db.get_value("GL Entry",
					{"voucher_type": "Stock Reconciliation", "voucher_no": stock_reco.name}))

	def test_get_items(self):
		create_warehouse("_Test Warehouse Group 1", {"is_group": 1})
		create_warehouse("_Test Warehouse Ledger 1",
			{"is_group": 0, "parent_warehouse": "_Test Warehouse Group 1 - _TC"})

		create_item("_Test Stock Reco Item", is_stock_item=1, valuation_rate=100,
			warehouse="_Test Warehouse Ledger 1 - _TC", opening_stock=100)

		items = get_items("_Test Warehouse Group 1 - _TC", nowdate(), nowtime(), "_Test Company")

		self.assertEqual(["_Test Stock Reco Item", "_Test Warehouse Ledger 1 - _TC", 100],
			[items[0]["item_code"], items[0]["warehouse"], items[0]["qty"]])

	def test_stock_reco_for_serialized_item(self):
		set_perpetual_inventory()

		to_delete_records = []
		to_delete_serial_nos = []

		# Add new serial nos
		serial_item_code = "Stock-Reco-Serial-Item-1"
		serial_warehouse = "_Test Warehouse for Stock Reco1 - _TC"

		sr = create_stock_reconciliation(item_code=serial_item_code,
			warehouse = serial_warehouse, qty=5, rate=200)

		# print(sr.name)
		serial_nos = get_serial_nos(sr.items[0].serial_no)
		self.assertEqual(len(serial_nos), 5)

		args = {
			"item_code": serial_item_code,
			"warehouse": serial_warehouse,
			"posting_date": nowdate(),
			"posting_time": nowtime(),
			"serial_no": sr.items[0].serial_no
		}

		valuation_rate = get_incoming_rate(args)
		self.assertEqual(valuation_rate, 200)

		to_delete_records.append(sr.name)

		sr = create_stock_reconciliation(item_code=serial_item_code,
			warehouse = serial_warehouse, qty=5, rate=300)

		# print(sr.name)
		serial_nos1 = get_serial_nos(sr.items[0].serial_no)
		self.assertEqual(len(serial_nos1), 5)

		args = {
			"item_code": serial_item_code,
			"warehouse": serial_warehouse,
			"posting_date": nowdate(),
			"posting_time": nowtime(),
			"serial_no": sr.items[0].serial_no
		}

		valuation_rate = get_incoming_rate(args)
		self.assertEqual(valuation_rate, 300)

		to_delete_records.append(sr.name)
		to_delete_records.reverse()

		for d in to_delete_records:
			stock_doc = frappe.get_doc("Stock Reconciliation", d)
			stock_doc.cancel()

		for d in serial_nos + serial_nos1:
			if frappe.db.exists("Serial No", d):
				frappe.delete_doc("Serial No", d)

	def test_stock_reco_for_batch_item(self):
		set_perpetual_inventory()

		to_delete_records = []
		to_delete_serial_nos = []

		# Add new serial nos
		item_code = "Stock-Reco-batch-Item-1"
		warehouse = "_Test Warehouse for Stock Reco2 - _TC"

		sr = create_stock_reconciliation(item_code=item_code,
			warehouse = warehouse, qty=5, rate=200, do_not_save=1, do_not_submit=1)
		sr.save(ignore_permissions=True)
		sr.submit()

		self.assertTrue(sr.items[0].batch_no)
		to_delete_records.append(sr.name)

		sr1 = create_stock_reconciliation(item_code=item_code,
			warehouse = warehouse, qty=6, rate=300, batch_no=sr.items[0].batch_no)

		args = {
			"item_code": item_code,
			"warehouse": warehouse,
			"posting_date": nowdate(),
			"posting_time": nowtime(),
		}

		valuation_rate = get_incoming_rate(args)
		self.assertEqual(valuation_rate, 300)
		to_delete_records.append(sr1.name)


		sr2 = create_stock_reconciliation(item_code=item_code,
			warehouse = warehouse, qty=0, rate=0, batch_no=sr.items[0].batch_no)

		stock_value = get_stock_value_on(warehouse, nowdate(), item_code)
		self.assertEqual(stock_value, 0)
		to_delete_records.append(sr2.name)

		to_delete_records.reverse()
		for d in to_delete_records:
			stock_doc = frappe.get_doc("Stock Reconciliation", d)
			stock_doc.cancel()

	def test_stock_reco_for_serial_and_batch_item(self):
		set_perpetual_inventory()

		item = frappe.db.exists("Item", {'item_name': 'Batched and Serialised Item 1'})
		if not item:
			item = create_item("Batched and Serialised Item 1")
			item.has_batch_no = 1
			item.create_new_batch = 1
			item.has_serial_no = 1
			item.batch_number_series = "B-BATCH-.##"
			item.serial_no_series = "S-.####"
			item.save()
		else:
			item = frappe.get_doc("Item", {'item_name': 'Batched and Serialised Item 1'})

		warehouse = "_Test Warehouse for Stock Reco2 - _TC"

		sr = create_stock_reconciliation(item_code=item.item_code,
			warehouse = warehouse, qty=1, rate=100)

		batch_no = sr.items[0].batch_no

		serial_nos = get_serial_nos(sr.items[0].serial_no)
		self.assertEqual(len(serial_nos), 1)
		self.assertEqual(frappe.db.get_value("Serial No", serial_nos[0], "batch_no"), batch_no)

		sr.cancel()

		self.assertEqual(frappe.db.get_value("Serial No", serial_nos[0], "status"), "Inactive")
		self.assertEqual(frappe.db.exists("Batch", batch_no), None)

		if frappe.db.exists("Serial No", serial_nos[0]):
			frappe.delete_doc("Serial No", serial_nos[0])

	def test_stock_reco_for_serial_and_batch_item_with_future_dependent_entry(self):
		"""
			Behaviour: 1) Create Stock Reconciliation, which will be the origin document
				of a new batch having a serial no
				2) Create a Stock Entry that adds a serial no to the same batch following this
					Stock Reconciliation
				3) Cancel Stock Reconciliation
				4) Cancel Stock Entry
			Expected Result: 3) Cancelling the Stock Reco throws a LinkExistsError since
				Stock Entry is dependent on the batch involved
				4) Serial No only in the Stock Entry is Inactive and Batch qty decreases
		"""
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.doctype.batch.batch import get_batch_qty

		set_perpetual_inventory()

		item = frappe.db.exists("Item", {'item_name': 'Batched and Serialised Item 1'})
		if not item:
			item = create_item("Batched and Serialised Item 1")
			item.has_batch_no = 1
			item.create_new_batch = 1
			item.has_serial_no = 1
			item.batch_number_series = "B-BATCH-.##"
			item.serial_no_series = "S-.####"
			item.save()
		else:
			item = frappe.get_doc("Item", {'item_name': 'Batched and Serialised Item 1'})

		warehouse = "_Test Warehouse for Stock Reco2 - _TC"

		stock_reco = create_stock_reconciliation(item_code=item.item_code,
			warehouse = warehouse, qty=1, rate=100)
		batch_no = stock_reco.items[0].batch_no
		serial_no = get_serial_nos(stock_reco.items[0].serial_no)[0]

		stock_entry = make_stock_entry(item_code=item.item_code, target=warehouse, qty=1, basic_rate=100,
			batch_no=batch_no)
		serial_no_2 = get_serial_nos(stock_entry.items[0].serial_no)[0]

		# Check Batch qty after 2 transactions
		batch_qty = get_batch_qty(batch_no, warehouse, item.item_code)
		self.assertEqual(batch_qty, 2)
		frappe.db.commit()

		# Cancelling Origin Document of Batch
		self.assertRaises(frappe.LinkExistsError, stock_reco.cancel)
		frappe.db.rollback()

		stock_entry.cancel()

		# Check Batch qty after cancellation
		batch_qty = get_batch_qty(batch_no, warehouse, item.item_code)
		self.assertEqual(batch_qty, 1)

		# Check if Serial No from Stock Reconcilation is intact
		self.assertEqual(frappe.db.get_value("Serial No", serial_no, "batch_no"), batch_no)
		self.assertEqual(frappe.db.get_value("Serial No", serial_no, "status"), "Active")

		# Check if Serial No from Stock Entry is Unlinked and Inactive
		self.assertEqual(frappe.db.get_value("Serial No", serial_no_2, "batch_no"), None)
		self.assertEqual(frappe.db.get_value("Serial No", serial_no_2, "status"), "Inactive")

		stock_reco.load_from_db()
		stock_reco.cancel()

		for sn in (serial_no, serial_no_2):
			if frappe.db.exists("Serial No", sn):
				frappe.delete_doc("Serial No", sn)

	def test_stock_reco_for_same_item_with_multiple_batches(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		set_perpetual_inventory()

		item_code = "Stock-Reco-batch-Item-2"
		warehouse = "_Test Warehouse for Stock Reco3 - _TC"

		create_warehouse("_Test Warehouse for Stock Reco3", {"is_group": 0,
			"parent_warehouse": "_Test Warehouse Group - _TC", "company": "_Test Company"})

		batch_item_doc = create_item(item_code, is_stock_item=1)
		if not batch_item_doc.has_batch_no:
			frappe.db.set_value("Item", item_code, {
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "Test-C.####"
			})

		# inward entries with different batch and valuation rate
		ste1=make_stock_entry(posting_date="2012-12-15", posting_time="02:00", item_code=item_code,
			target=warehouse, qty=6, basic_rate=700)
		ste2=make_stock_entry(posting_date="2012-12-16", posting_time="02:00", item_code=item_code,
			target=warehouse, qty=3, basic_rate=200)
		ste3=make_stock_entry(posting_date="2012-12-17", posting_time="02:00", item_code=item_code,
			target=warehouse, qty=2, basic_rate=500)
		ste4=make_stock_entry(posting_date="2012-12-17", posting_time="02:00", item_code=item_code,
			target=warehouse, qty=4, basic_rate=100)

		batchwise_item_details = {}
		for stock_doc in [ste1, ste2, ste3, ste4]:
			self.assertEqual(item_code, stock_doc.items[0].item_code)
			batchwise_item_details[stock_doc.items[0].batch_no] = [stock_doc.items[0].qty, 0.01]

		stock_balance = frappe.get_all("Stock Ledger Entry",
			filters = {"item_code": item_code, "warehouse": warehouse},
			fields=["sum(stock_value_difference)"], as_list=1)

		self.assertEqual(flt(stock_balance[0][0]), 6200.00)

		sr = create_stock_reconciliation(item_code=item_code,
			warehouse = warehouse, batch_details = batchwise_item_details)

		stock_balance = frappe.get_all("Stock Ledger Entry",
			filters = {"item_code": item_code, "warehouse": warehouse},
			fields=["sum(stock_value_difference)"], as_list=1)

		self.assertEqual(flt(stock_balance[0][0]), 0.15)

		for doc in [sr, ste1, ste2, ste3, ste4]:
			doc.cancel()
			frappe.delete_doc(doc.doctype, doc.name)

	def test_allow_negative_for_batch(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		item_code = "Stock-Reco-batch-Item-5"
		warehouse = "_Test Warehouse for Stock Reco5 - _TC"

		create_warehouse("_Test Warehouse for Stock Reco5", {"is_group": 0,
			"parent_warehouse": "_Test Warehouse Group - _TC", "company": "_Test Company"})

		batch_item_doc = create_item(item_code, is_stock_item=1)
		if not batch_item_doc.has_batch_no:
			frappe.db.set_value("Item", item_code, {
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "Test-C.####"
			})

		ste1=make_stock_entry(posting_date="2020-10-07", posting_time="02:00", item_code=item_code,
			target=warehouse, qty=2, basic_rate=100)

		batch_no = ste1.items[0].batch_no

		ste2=make_stock_entry(posting_date="2020-10-09", posting_time="02:00", item_code=item_code,
			source=warehouse, qty=2, basic_rate=100, batch_no=batch_no)

		sr = create_stock_reconciliation(item_code=item_code,
			warehouse = warehouse, batch_no=batch_no, rate=200)

		for doc in [sr, ste2, ste1]:
			doc.cancel()
			frappe.delete_doc(doc.doctype, doc.name)

	def test_stock_reco_with_serial_and_batch(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		warehouse = "_Test Warehouse for Stock Reco1 - _TC"
		ste1=make_stock_entry(item_code="Stock-Reco-Serial-Item-1",
			target=warehouse, qty=2, basic_rate=100)

		ste2=make_stock_entry(item_code="Stock-Reco-batch-Item-1",
			target=warehouse, qty=2, basic_rate=100)

		sr = create_stock_reconciliation(item_code="Stock-Reco-Serial-Item-1",
			warehouse = warehouse, rate=200, do_not_submit=True)

		sr.append("items", {
			"item_code": "Stock-Reco-batch-Item-1",
			"warehouse": warehouse,
			"batch_no": ste2.items[0].batch_no,
			"valuation_rate": 200
		})

		sr.submit()
		sle = frappe.get_all("Stock Ledger Entry", filters={"item_code": "Stock-Reco-batch-Item-1",
			"warehouse": warehouse, "voucher_no": sr.name, "voucher_type": sr.doctype})

		self.assertEquals(len(sle), 1)

		for doc in [sr, ste2, ste1]:
			doc.cancel()

def insert_existing_sle(warehouse):
	from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

	make_stock_entry(posting_date="2012-12-15", posting_time="02:00", item_code="_Test Item",
		target=warehouse, qty=10, basic_rate=700)

	make_stock_entry(posting_date="2012-12-25", posting_time="03:00", item_code="_Test Item",
		source=warehouse, qty=15)

	make_stock_entry(posting_date="2013-01-05", posting_time="07:00", item_code="_Test Item",
		target=warehouse, qty=15, basic_rate=1200)

def create_batch_or_serial_no_items():
	create_warehouse("_Test Warehouse for Stock Reco1",
		{"is_group": 0, "parent_warehouse": "_Test Warehouse Group - _TC"})

	create_warehouse("_Test Warehouse for Stock Reco2",
		{"is_group": 0, "parent_warehouse": "_Test Warehouse Group - _TC"})

	serial_item_doc = create_item("Stock-Reco-Serial-Item-1", is_stock_item=1)
	if not serial_item_doc.has_serial_no:
		serial_item_doc.has_serial_no = 1
		serial_item_doc.serial_no_series = "SRSI.####"
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
	sr.expense_account = args.expense_account or \
		("Stock Adjustment - _TC" if frappe.get_all("Stock Ledger Entry") else "Temporary Opening - _TC")
	sr.cost_center = args.cost_center \
		or frappe.get_cached_value("Company", sr.company, "cost_center") \
		or "_Test Cost Center - _TC"

	if not args.batch_details:
		sr.append("items", {
			"item_code": args.item_code or "_Test Item",
			"warehouse": args.warehouse or "_Test Warehouse - _TC",
			"qty": args.qty,
			"valuation_rate": args.rate,
			"serial_no": args.serial_no,
			"batch_no": args.batch_no
		})
	elif args.batch_details:
		for batch, data in args.batch_details.items():
			sr.append("items", {
				"item_code": args.item_code or "_Test Item",
				"warehouse": args.warehouse or "_Test Warehouse - _TC",
				"qty": data[0],
				"valuation_rate": data[1],
				"batch_no": batch
			})

	if not args.do_not_save:
		sr.insert()
		try:
			if not args.do_not_submit:
				sr.submit()
		except EmptyStockReconciliationItemsError:
			pass

	return sr

def set_valuation_method(item_code, valuation_method):
	frappe.db.set_value("Item", item_code, "valuation_method", valuation_method)

	for warehouse in frappe.get_all("Warehouse", filters={"company": "_Test Company"}, fields=["name", "is_group"]):
		if not warehouse.is_group:
			update_entries_after({
				"item_code": item_code,
				"warehouse": warehouse.name
			}, allow_negative_stock=1)

test_dependencies = ["Item", "Warehouse"]

