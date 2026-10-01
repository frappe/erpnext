from unittest.mock import patch

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import SerialNoDuplicateError
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchMessages(ERPNextTestSuite):
	def setUp(self):
		self.item = make_item(properties={"has_serial_no": 1, "has_batch_no": 1})
		self.batch = frappe.get_doc(doctype="Batch", item=self.item.name, batch_id="LOT<001>").insert()
		self.serial = frappe.get_doc(
			doctype="Serial No",
			item_code=self.item.name,
			serial_no="SER&001",
			batch_no=self.batch.name,
			company="_Test Company",
		).insert()
		self.bundle = frappe.get_doc(
			doctype="Serial and Batch Bundle",
			item_code=self.item.name,
			has_serial_no=1,
			has_batch_no=1,
			warehouse="Stores - _TC",
			voucher_type="Purchase Receipt",
			type_of_transaction="Inward",
			entries=[{"serial_no": self.serial.name, "batch_no": self.batch.name, "qty": 1}],
		)

	def test_duplicate_messages_preserve_references(self):
		for field, name, label in (
			("serial_no", self.serial.name, "SER&amp;001"),
			("batch_no", self.batch.name, "LOT&lt;001&gt;"),
		):
			with self.subTest(field=field):
				self.bundle.set("entries", [{field: name, "qty": 1}, {field: name, "qty": 1}])
				with self.assertRaises(frappe.ValidationError) as error:
					self.bundle.validate_duplicate_serial_and_batch_no()
				self.assertIn(label, str(error.exception))
				self.assertNotIn(name, str(error.exception))
				self.assertEqual([row.get(field) for row in self.bundle.entries], [name, name])

	def test_existing_stock_message_shows_physical_serial(self):
		with patch(
			"erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.get_available_serial_nos",
			return_value=[frappe._dict(serial_no=self.serial.name, warehouse=self.bundle.warehouse)],
		):
			with self.assertRaises(SerialNoDuplicateError) as error:
				self.bundle.validate_serial_nos_duplicate()
		self.assertIn("SER&amp;001", str(error.exception))
		self.assertIn(self.bundle.warehouse, str(error.exception))
		self.assertNotIn(self.serial.name, str(error.exception))

	def test_serial_batch_mismatch_shows_both_physical_numbers(self):
		other_batch = frappe.get_doc(doctype="Batch", item=self.item.name, batch_id="LOT<002>").insert()
		with self.assertRaises(frappe.ValidationError) as error:
			self.bundle.validate_serial_batch_no({self.serial.name: other_batch.name})
		message = str(error.exception)
		self.assertIn("SER&amp;001", message)
		self.assertIn("LOT&lt;002&gt;", message)
		self.assertNotIn(self.serial.name, message)
		self.assertNotIn(other_batch.name, message)
		self.assertEqual(self.serial.reload().batch_no, self.batch.name)

	def test_return_message_identifies_the_invalid_batch(self):
		original_batch = frappe.get_doc(
			doctype="Batch", item=self.item.name, batch_id="ORIGINAL-LOT"
		).insert()
		self.bundle.has_serial_no = 0
		self.bundle.returned_against = "Original Receipt Row"
		self.bundle.set("entries", [{"batch_no": self.batch.name, "qty": -1}])
		with patch.object(
			self.bundle,
			"get_orignal_document_data",
			return_value=[frappe._dict(batch_no=original_batch.name, stock_qty=1)],
		):
			with self.assertRaises(frappe.ValidationError) as error:
				self.bundle.validate_serial_and_batch_no_for_returned()
		message = str(error.exception)
		self.assertIn("LOT&lt;001&gt;", message)
		self.assertNotIn(original_batch.batch_id, message)
		self.assertNotIn(self.batch.name, message)
		self.assertEqual(self.bundle.entries[0].batch_no, self.batch.name)
