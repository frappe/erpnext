import frappe
from frappe.model.naming import NamingSeries

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.serial_batch_bundle import SerialBatchCreation
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialNumberGeneration(ERPNextTestSuite):
	def setUp(self):
		self.series = "_Identity-Auto-.###"
		self.item = make_item("_Identity Auto Item", {"has_serial_no": 1, "serial_no_series": self.series})

	def test_generated_numbers_have_separate_ids_and_preserve_counter(self):
		names = self.generator(2).get_auto_created_serial_nos()
		self.assertEqual(len(set(names)), 2)
		for index, name in enumerate(names, start=1):
			serial = frappe.get_doc("Serial No", name)
			self.assertEqual(serial.serial_no, f"_Identity-Auto-{index:03d}")
			self.assertNotEqual(serial.name, serial.serial_no)
			self.assertEqual(serial.item_code, self.item.name)
		self.assertEqual(NamingSeries(self.series).get_current_value(), 2)
		next_name = self.generator(1).get_auto_created_serial_nos()[0]
		self.assertEqual(frappe.db.get_value("Serial No", next_name, "serial_no"), "_Identity-Auto-003")

	def test_generated_number_can_exist_for_another_item(self):
		other = make_item("_Identity Auto Other Item", {"has_serial_no": 1})
		self.make_serial(other.name, "_Identity-Auto-001")
		name = self.generator(1).get_auto_created_serial_nos()[0]
		self.assertEqual(frappe.db.get_value("Serial No", name, "item_code"), self.item.name)
		self.assertEqual(frappe.db.get_value("Serial No", name, "serial_no"), "_Identity-Auto-001")

	def test_series_collision_keeps_naming_series_guidance(self):
		self.make_serial(self.item.name, "_Identity-Auto-001")
		with self.assertRaisesRegex(frappe.UniqueValidationError, "change the naming series"):
			self.generator(1).get_auto_created_serial_nos()

	def generator(self, qty):
		return SerialBatchCreation(
			{
				"item_code": self.item.name,
				"qty": qty,
				"company": "_Test Company",
				"warehouse": "_Test Warehouse - _TC",
				"voucher_type": "Purchase Receipt",
				"voucher_no": "",
				"batch_no": None,
			}
		)

	def make_serial(self, item_code, number):
		return frappe.get_doc(
			{
				"doctype": "Serial No",
				"item_code": item_code,
				"serial_no": number,
				"company": "_Test Company",
			}
		).insert()
