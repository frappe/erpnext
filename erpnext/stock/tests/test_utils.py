import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.utils import scan_barcode


class TestStockUtilities(FrappeTestCase):
	def test_barcode_scanning(self):
		simple_item = make_item(properties={"barcodes": [{"barcode": "12399"}]})
		self.assertEqual(scan_barcode("12399")["item_code"], simple_item.name)

		batch_item = make_item(properties={"has_batch_no": 1, "create_new_batch": 1})
		batch = frappe.get_doc(doctype="Batch", item=batch_item.name).insert()

		batch_scan = scan_barcode(batch.name)
		self.assertEqual(batch_scan["item_code"], batch_item.name)
		self.assertEqual(batch_scan["batch_no"], batch.name)
		self.assertEqual(batch_scan["has_batch_no"], 1)
		self.assertEqual(batch_scan["has_serial_no"], 0)

		serial_item = make_item(properties={"has_serial_no": 1})
		serial = frappe.get_doc(
			doctype="Serial No", item_code=serial_item.name, serial_no=frappe.generate_hash()
		).insert()

		serial_scan = scan_barcode(serial.name)
		self.assertEqual(serial_scan["item_code"], serial_item.name)
		self.assertEqual(serial_scan["serial_no"], serial.name)
		self.assertEqual(serial_scan["has_batch_no"], 0)
		self.assertEqual(serial_scan["has_serial_no"], 1)
