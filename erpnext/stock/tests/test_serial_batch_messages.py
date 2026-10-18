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
