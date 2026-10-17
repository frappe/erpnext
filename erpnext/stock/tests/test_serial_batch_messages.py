from unittest.mock import patch

import frappe

from erpnext.stock.doctype.item.test_item import make_item
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
