import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.serial_batch_identity import SerialBatchIdentity, resolve_serial_batch_numbers
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchIdentityAccess(ERPNextTestSuite):
	def make_stock_user(self):
		return frappe.get_doc(
			{
				"doctype": "User",
				"email": f"serial-access-{frappe.generate_hash()}@example.test",
				"first_name": "Serial Access Test",
				"send_welcome_email": 0,
				"roles": [{"role": "Stock User"}],
			}
		).insert()

	def test_read_only_resolution_never_creates_missing_serials(self):
		item = make_item(properties={"has_serial_no": 1})
		user = self.make_stock_user()
		with self.set_user(user.name):
			self.assertTrue(frappe.has_permission("Purchase Receipt", "write"))
			self.assertTrue(frappe.has_permission("Serial No", "read"))
			self.assertFalse(frappe.has_permission("Serial No", "create"))
			with self.assertRaises(frappe.ValidationError):
				resolve_serial_batch_numbers(item.name, serial_numbers=["UNAUTHORIZED-SERIAL"])
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": item.name}))

	def test_readers_can_resolve_existing_serials(self):
		item = make_item(properties={"has_serial_no": 1})
		names = SerialBatchIdentity("Serial No").resolve(item.name, ["EXISTING-SERIAL"], create=True)
		user = self.make_stock_user()
		with self.set_user(user.name):
			self.assertFalse(frappe.has_permission("Serial No", "create"))
			result = resolve_serial_batch_numbers(item.name, serial_numbers=["EXISTING-SERIAL"])
			self.assertEqual(result["serial_nos"], names)

	def test_even_authorized_resolution_does_not_create_serials(self):
		item = make_item(properties={"has_serial_no": 1})
		with self.assertRaises(frappe.ValidationError):
			resolve_serial_batch_numbers(item.name, serial_numbers=["MISSING-SERIAL"])
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": item.name}))

	def test_draft_save_requires_permission_to_create_missing_serials(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		item = make_item(properties={"has_serial_no": 1})
		user = self.make_stock_user()
		receipt = make_purchase_receipt(item_code=item.name, qty=1, do_not_save=True)
		receipt.items[0].serial_no = "UNAUTHORIZED-ON-SAVE"
		receipt.items[0].set("__serial_batch_input", ["serial_no"])
		with self.set_user(user.name):
			with self.assertRaises(frappe.PermissionError):
				receipt.insert()
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": item.name}))

	def test_bundle_number_input_checks_creation_permissions(self):
		from erpnext.stock.serial_batch_identity import resolve_number_entries

		item = make_item(properties={"has_serial_no": 1})
		serial = SerialBatchIdentity("Serial No").resolve(item.name, ["Existing"], create=True)[0]
		user = self.make_stock_user()
		with self.set_user(user.name):
			entries = [{"serial_number": "Existing"}]
			resolve_number_entries(item.name, entries, create=True)
			self.assertEqual(entries[0]["serial_no"], serial)
			with self.assertRaises(frappe.PermissionError):
				resolve_number_entries(item.name, [{"serial_number": "Unauthorized"}], create=True)
		self.assertFalse(SerialBatchIdentity("Serial No").exists("Unauthorized", item.name))

	def test_bundle_scanning_does_not_create_records(self):
		from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
			resolve_scanned_serial_batch_numbers,
		)

		item = make_item(properties={"has_serial_no": 1})
		with self.assertRaises(frappe.ValidationError):
			resolve_scanned_serial_batch_numbers(item.name, serial_no="Missing")
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": item.name}))
