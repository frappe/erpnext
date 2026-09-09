import frappe
from frappe.utils import add_days, escape_html, now_datetime, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
	BatchNegativeStockError,
	SerialNoDuplicateError,
	SerialNoExistsInFutureTransactionError,
	SerialNoWarehouseError,
)
from erpnext.stock.serial_batch_bundle import throw_negative_batch_validation
from erpnext.stock.serial_batch_identity import SerialBatchIdentity
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchMessages(ERPNextTestSuite):
	def setUp(self):
		super().setUp()
		self.item = make_item(properties={"has_serial_no": 1, "has_batch_no": 1})
		self.batch_number = "Batch<&>"
		self.serial_number = "Serial<&>"
		self.batch = SerialBatchIdentity("Batch").resolve(self.item.name, [self.batch_number], create=True)[0]
		self.serial = SerialBatchIdentity("Serial No").resolve(
			self.item.name,
			[self.serial_number],
			create=True,
			defaults={"company": "_Test Company", "batch_no": self.batch},
		)[0]
		self.bundle = frappe.get_doc(
			{
				"doctype": "Serial and Batch Bundle",
				"item_code": self.item.name,
				"has_serial_no": 1,
				"has_batch_no": 1,
				"voucher_type": "Purchase Receipt",
				"type_of_transaction": "Inward",
				"warehouse": "_Test Warehouse - _TC",
				"entries": [{"serial_no": self.serial, "batch_no": self.batch, "qty": 1}],
			}
		)

	def test_duplicate_receipt_shows_serial_number(self):
		args = {
			"item_code": self.item.name,
			"qty": 1,
			"serial_no": self.serial,
			"batch_no": self.batch,
			"use_serial_batch_fields": 1,
		}
		make_purchase_receipt(**args)
		receipt = make_purchase_receipt(**args, do_not_submit=True)
		with self.assertRaises(SerialNoDuplicateError) as error:
			receipt.submit()
		self.assert_number_message(error, self.serial, self.serial_number)
		self.assertIn("already present in the warehouse", str(error.exception))
		self.assertEqual(receipt.items[0].serial_no, self.serial)
		self.assertEqual(frappe.db.get_value("Serial No", self.serial, "warehouse"), self.bundle.warehouse)

	def test_missing_serial_inventory_shows_number(self):
		self.bundle.type_of_transaction = "Outward"
		with self.assertRaises(SerialNoWarehouseError) as error:
			self.bundle.validate_serial_nos_inventory()
		self.assert_number_message(error, self.serial, self.serial_number)

	def test_duplicate_entries_show_numbers(self):
		for doctype, field, name, number in self.number_cases():
			with self.subTest(doctype=doctype):
				self.bundle.set("entries", [{field: name, "qty": 1}, {field: name, "qty": 1}])
				with self.assertRaises(frappe.ValidationError) as error:
					self.bundle.validate_duplicate_serial_and_batch_no()
				self.assert_number_message(error, name, number)
				self.assertEqual([row.get(field) for row in self.bundle.entries], [name, name])

	def test_wrong_item_shows_numbers(self):
		self.bundle.item_code = make_item().name
		for doctype, _field, name, number in self.number_cases():
			with self.subTest(doctype=doctype):
				validate = (
					self.bundle.validate_incorrect_serial_nos
					if doctype == "Serial No"
					else self.bundle.validate_incorrect_batch_nos
				)
				with self.assertRaises(frappe.ValidationError) as error:
					validate([name])
				self.assert_number_message(error, name, number)

	def test_return_error_shows_numbers(self):
		for doctype, field, name, number in self.number_cases():
			with self.subTest(doctype=doctype):
				with self.assertRaises(frappe.ValidationError) as error:
					self.bundle.validate_returned_serial_batch_no(
						"Original Receipt", frappe._dict({field: name}), {"serial_nos": [], "batches": []}
					)
				self.assert_number_message(error, name, number)

	def test_negative_stock_shows_batch_number(self):
		with self.assertRaises(BatchNegativeStockError) as error:
			self.bundle.validate_negative_batch(self.batch, -1)
		self.assert_number_message(error, self.batch, self.batch_number)

	def test_expired_batch_shows_number(self):
		frappe.db.set_value("Batch", self.batch, "expiry_date", add_days(today(), -1))
		entry = frappe.get_doc(
			{
				"doctype": "Stock Ledger Entry",
				"batch_no": self.batch,
				"item_code": self.item.name,
				"voucher_type": "Delivery Note",
				"actual_qty": -1,
				"posting_date": today(),
			}
		)
		with self.assertRaises(frappe.ValidationError) as error:
			entry.validate_batch()
		self.assert_number_message(error, self.batch, self.batch_number)
		self.assertEqual(entry.batch_no, self.batch)

	def test_serial_batch_mismatch_shows_both_numbers(self):
		batch_number = "Other Batch<&>"
		batch = SerialBatchIdentity("Batch").resolve(self.item.name, [batch_number], create=True)[0]
		with self.assertRaises(frappe.ValidationError) as error:
			self.bundle.validate_serial_batch_no({self.serial: batch})
		self.assert_number_message(error, self.serial, self.serial_number)
		self.assert_number_message(error, batch, batch_number)

	def test_future_transaction_shows_serial_number_and_document_link(self):
		receipt = make_purchase_receipt(
			item_code=self.item.name, qty=1, serial_no=[self.serial], batch_no=self.batch
		)
		self.bundle.name = "new-bundle"
		self.bundle.posting_datetime = add_days(now_datetime(), -1)
		with self.assertRaises(SerialNoExistsInFutureTransactionError) as error:
			self.bundle.check_future_entries_exists()
		self.assert_number_message(error, self.serial, self.serial_number)
		self.assertIn(f'/purchase-receipt/{receipt.name}"', str(error.exception))

	def test_legacy_and_missing_records_keep_the_number(self):
		frappe.db.set_value("Serial No", self.serial, "serial_no", self.serial)
		for name in (self.serial, "Missing<&>"):
			with self.subTest(name=name):
				self.bundle.set("entries", [{"serial_no": name}, {"serial_no": name}])
				with self.assertRaises(frappe.ValidationError) as error:
					self.bundle.validate_duplicate_serial_and_batch_no()
				self.assertIn(escape_html(name), str(error.exception))

	def test_batch_error_link_keeps_id_and_displays_number(self):
		with self.assertRaises(frappe.ValidationError) as error:
			throw_negative_batch_validation(self.batch, -1)
		message = str(error.exception)
		self.assertIn(f'/batch/{self.batch}"', message)
		self.assertIn(f">{escape_html(self.batch_number)}</a>", message)
		self.assertNotIn(f">{self.batch}</a>", message)
		self.assertNotIn(self.batch_number, message)

	def number_cases(self):
		return [
			("Serial No", "serial_no", self.serial, self.serial_number),
			("Batch", "batch_no", self.batch, self.batch_number),
		]

	def assert_number_message(self, error, name, number):
		message = str(error.exception)
		self.assertIn(escape_html(number), message)
		self.assertNotIn(name, message)
		self.assertNotIn(number, message)
