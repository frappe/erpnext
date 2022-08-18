# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cint, flt

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.stock.doctype.batch.batch import UnableToSelectBatchError, get_batch_no, get_batch_qty
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.get_item_details import get_item_details


class TestBatch(FrappeTestCase):
	def test_item_has_batch_enabled(self):
		self.assertRaises(
			ValidationError,
			frappe.get_doc({"doctype": "Batch", "name": "_test Batch", "item": "_Test Item"}).save,
		)

	@classmethod
	def make_batch_item(cls, item_name=None):
		from erpnext.stock.doctype.item.test_item import make_item

		if not frappe.db.exists("Item", item_name):
			return make_item(item_name, dict(has_batch_no=1, create_new_batch=1, is_stock_item=1))
		else:
			return frappe.get_doc("Item", item_name)

	def test_purchase_receipt(self, batch_qty=100):
		"""Test automated batch creation from Purchase Receipt"""
		self.make_batch_item("ITEM-BATCH-1")

		receipt = frappe.get_doc(
			dict(
				doctype="Purchase Receipt",
				supplier="_Test Supplier",
				company="_Test Company",
				items=[dict(item_code="ITEM-BATCH-1", qty=batch_qty, rate=10, warehouse="Stores - _TC")],
			)
		).insert()
		receipt.submit()

		self.assertTrue(receipt.items[0].batch_no)
		self.assertEqual(get_batch_qty(receipt.items[0].batch_no, receipt.items[0].warehouse), batch_qty)

		return receipt

	def test_stock_entry_incoming(self):
		"""Test batch creation via Stock Entry (Work Order)"""

		self.make_batch_item("ITEM-BATCH-1")

		stock_entry = frappe.get_doc(
			dict(
				doctype="Stock Entry",
				purpose="Material Receipt",
				company="_Test Company",
				items=[
					dict(
						item_code="ITEM-BATCH-1",
						qty=90,
						t_warehouse="_Test Warehouse - _TC",
						cost_center="Main - _TC",
						rate=10,
					)
				],
			)
		)

		stock_entry.set_stock_entry_type()
		stock_entry.insert()
		stock_entry.submit()

		self.assertTrue(stock_entry.items[0].batch_no)
		self.assertEqual(
			get_batch_qty(stock_entry.items[0].batch_no, stock_entry.items[0].t_warehouse), 90
		)

	def test_delivery_note(self):
		"""Test automatic batch selection for outgoing items"""
		batch_qty = 15
		receipt = self.test_purchase_receipt(batch_qty)
		item_code = "ITEM-BATCH-1"

		delivery_note = frappe.get_doc(
			dict(
				doctype="Delivery Note",
				customer="_Test Customer",
				company=receipt.company,
				items=[
					dict(item_code=item_code, qty=batch_qty, rate=10, warehouse=receipt.items[0].warehouse)
				],
			)
		).insert()
		delivery_note.submit()

		# shipped from FEFO batch
		self.assertEqual(
			delivery_note.items[0].batch_no, get_batch_no(item_code, receipt.items[0].warehouse, batch_qty)
		)

	def test_delivery_note_fail(self):
		"""Test automatic batch selection for outgoing items"""
		receipt = self.test_purchase_receipt(100)
		delivery_note = frappe.get_doc(
			dict(
				doctype="Delivery Note",
				customer="_Test Customer",
				company=receipt.company,
				items=[
					dict(item_code="ITEM-BATCH-1", qty=5000, rate=10, warehouse=receipt.items[0].warehouse)
				],
			)
		)
		self.assertRaises(UnableToSelectBatchError, delivery_note.insert)

	def test_stock_entry_outgoing(self):
		"""Test automatic batch selection for outgoing stock entry"""

		batch_qty = 16
		receipt = self.test_purchase_receipt(batch_qty)
		item_code = "ITEM-BATCH-1"

		stock_entry = frappe.get_doc(
			dict(
				doctype="Stock Entry",
				purpose="Material Issue",
				company=receipt.company,
				items=[
					dict(
						item_code=item_code,
						qty=batch_qty,
						s_warehouse=receipt.items[0].warehouse,
					)
				],
			)
		)

		stock_entry.set_stock_entry_type()
		stock_entry.insert()
		stock_entry.submit()

		# assert same batch is selected
		self.assertEqual(
			stock_entry.items[0].batch_no, get_batch_no(item_code, receipt.items[0].warehouse, batch_qty)
		)

	def test_batch_split(self):
		"""Test batch splitting"""
		receipt = self.test_purchase_receipt()
		from erpnext.stock.doctype.batch.batch import split_batch

		new_batch = split_batch(
			receipt.items[0].batch_no, "ITEM-BATCH-1", receipt.items[0].warehouse, 22
		)

		self.assertEqual(get_batch_qty(receipt.items[0].batch_no, receipt.items[0].warehouse), 78)
		self.assertEqual(get_batch_qty(new_batch, receipt.items[0].warehouse), 22)

	def test_get_batch_qty(self):
		"""Test getting batch quantities by batch_numbers, item_code or warehouse"""
		self.make_batch_item("ITEM-BATCH-2")
		self.make_new_batch_and_entry("ITEM-BATCH-2", "batch a", "_Test Warehouse - _TC")
		self.make_new_batch_and_entry("ITEM-BATCH-2", "batch b", "_Test Warehouse - _TC")

		self.assertEqual(
			get_batch_qty(item_code="ITEM-BATCH-2", warehouse="_Test Warehouse - _TC"),
			[{"batch_no": "batch a", "qty": 90.0}, {"batch_no": "batch b", "qty": 90.0}],
		)

		self.assertEqual(get_batch_qty("batch a", "_Test Warehouse - _TC"), 90)

	def test_total_batch_qty(self):
		self.make_batch_item("ITEM-BATCH-3")
		existing_batch_qty = flt(frappe.db.get_value("Batch", "B100", "batch_qty"))
		stock_entry = self.make_new_batch_and_entry("ITEM-BATCH-3", "B100", "_Test Warehouse - _TC")

		current_batch_qty = flt(frappe.db.get_value("Batch", "B100", "batch_qty"))
		self.assertEqual(current_batch_qty, existing_batch_qty + 90)

		stock_entry.cancel()
		current_batch_qty = flt(frappe.db.get_value("Batch", "B100", "batch_qty"))
		self.assertEqual(current_batch_qty, existing_batch_qty)

	@classmethod
	def make_new_batch_and_entry(cls, item_name, batch_name, warehouse):
		"""Make a new stock entry for given target warehouse and batch name of item"""

		if not frappe.db.exists("Batch", batch_name):
			batch = frappe.get_doc(dict(doctype="Batch", item=item_name, batch_id=batch_name)).insert(
				ignore_permissions=True
			)
			batch.save()

		stock_entry = frappe.get_doc(
			dict(
				doctype="Stock Entry",
				purpose="Material Receipt",
				company="_Test Company",
				items=[
					dict(
						item_code=item_name,
						qty=90,
						t_warehouse=warehouse,
						cost_center="Main - _TC",
						rate=10,
						batch_no=batch_name,
						allow_zero_valuation_rate=1,
					)
				],
			)
		)

		stock_entry.set_stock_entry_type()
		stock_entry.insert()
		stock_entry.submit()

		return stock_entry

	def test_batch_name_with_naming_series(self):
		stock_settings = frappe.get_single("Stock Settings")
		use_naming_series = cint(stock_settings.use_naming_series)

		if not use_naming_series:
			frappe.set_value("Stock Settings", "Stock Settings", "use_naming_series", 1)

		batch = self.make_new_batch("_Test Stock Item For Batch Test1")
		batch_name = batch.name

		self.assertTrue(batch_name.startswith("BATCH-"))

		batch.delete()
		batch = self.make_new_batch("_Test Stock Item For Batch Test2")

		self.assertEqual(batch_name, batch.name)

		# reset Stock Settings
		if not use_naming_series:
			frappe.set_value("Stock Settings", "Stock Settings", "use_naming_series", 0)

	def make_new_batch(self, item_name=None, batch_id=None, do_not_insert=0):
		batch = frappe.new_doc("Batch")
		item = self.make_batch_item(item_name)
		batch.item = item.name

		if batch_id:
			batch.batch_id = batch_id

		if not do_not_insert:
			batch.insert()

		return batch

	def test_batch_wise_item_price(self):
		if not frappe.db.get_value("Item", "_Test Batch Price Item"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"is_stock_item": 1,
					"item_code": "_Test Batch Price Item",
					"item_group": "Products",
					"has_batch_no": 1,
					"create_new_batch": 1,
				}
			).insert(ignore_permissions=True)

		batch1 = create_batch("_Test Batch Price Item", 200, 1)
		batch2 = create_batch("_Test Batch Price Item", 300, 1)
		batch3 = create_batch("_Test Batch Price Item", 400, 0)

		company = "_Test Company with perpetual inventory"
		currency = frappe.get_cached_value("Company", company, "default_currency")

		args = frappe._dict(
			{
				"item_code": "_Test Batch Price Item",
				"company": company,
				"price_list": "_Test Price List",
				"currency": currency,
				"doctype": "Sales Invoice",
				"conversion_rate": 1,
				"price_list_currency": "_Test Currency",
				"plc_conversion_rate": 1,
				"customer": "_Test Customer",
				"name": None,
			}
		)

		# test price for batch1
		args.update({"batch_no": batch1})
		details = get_item_details(args)
		self.assertEqual(details.get("price_list_rate"), 200)

		# test price for batch2
		args.update({"batch_no": batch2})
		details = get_item_details(args)
		self.assertEqual(details.get("price_list_rate"), 300)

		# test price for batch3
		args.update({"batch_no": batch3})
		details = get_item_details(args)
		self.assertEqual(details.get("price_list_rate"), 400)

	def test_autocreation_of_batches(self):
		"""
		Test if auto created batch no excludes existing batch numbers
		"""
		item_code = make_item(
			properties={
				"has_batch_no": 1,
				"batch_number_series": "BATCHEXISTING.###",
				"create_new_batch": 1,
			}
		).name

		manually_created_batch = self.make_new_batch(item_code, batch_id="BATCHEXISTING001").name

		pr_1 = make_purchase_receipt(item_code=item_code, qty=1, batch_no=manually_created_batch)
		pr_2 = make_purchase_receipt(item_code=item_code, qty=1)

		self.assertNotEqual(pr_1.items[0].batch_no, pr_2.items[0].batch_no)
		self.assertEqual("BATCHEXISTING002", pr_2.items[0].batch_no)


def create_batch(item_code, rate, create_item_price_for_batch):
	pi = make_purchase_invoice(
		company="_Test Company",
		warehouse="Stores - _TC",
		cost_center="Main - _TC",
		update_stock=1,
		expense_account="_Test Account Cost for Goods Sold - _TC",
		item_code=item_code,
	)

	batch = frappe.db.get_value("Batch", {"item": item_code, "reference_name": pi.name})

	if not create_item_price_for_batch:
		create_price_list_for_batch(item_code, None, rate)
	else:
		create_price_list_for_batch(item_code, batch, rate)

	return batch


def create_price_list_for_batch(item_code, batch, rate):
	frappe.get_doc(
		{
			"doctype": "Item Price",
			"item_code": "_Test Batch Price Item",
			"price_list": "_Test Price List",
			"batch_no": batch,
			"price_list_rate": rate,
		}
	).insert()


def make_new_batch(**args):
	args = frappe._dict(args)

	try:
		batch = frappe.get_doc(
			{
				"doctype": "Batch",
				"batch_id": args.batch_id,
				"item": args.item_code,
				"expiry_date": args.expiry_date,
			}
		)

		if args.expiry_date:
			batch.expiry_date = args.expiry_date

		batch.insert()

	except frappe.DuplicateEntryError:
		batch = frappe.get_doc("Batch", args.batch_id)

	return batch
