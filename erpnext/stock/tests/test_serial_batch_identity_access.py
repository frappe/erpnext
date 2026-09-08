import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.serial_batch_identity import resolve_transaction_serial_numbers
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

	def test_inward_resolution_requires_serial_create_permission(self):
		item = make_item(properties={"has_serial_no": 1})
		user = self.make_stock_user()
		parent = {"doctype": "Purchase Receipt", "__islocal": 1, "company": "_Test Company"}
		row = {"item_code": item.name, "qty": 1}
		with self.set_user(user.name):
			self.assertTrue(frappe.has_permission("Purchase Receipt", "write"))
			self.assertTrue(frappe.has_permission("Serial No", "read"))
			self.assertFalse(frappe.has_permission("Serial No", "create"))
			with self.assertRaises(frappe.PermissionError):
				resolve_transaction_serial_numbers(parent, row, ["UNAUTHORIZED-SERIAL"])
		self.assertFalse(frappe.db.exists("Serial No", {"item_code": item.name}))

	def test_readers_can_resolve_existing_outward_serials(self):
		item = make_item(properties={"has_serial_no": 1})
		parent = {"doctype": "Purchase Receipt", "__islocal": 1, "company": "_Test Company"}
		row = {"item_code": item.name, "qty": 1}
		names = resolve_transaction_serial_numbers(parent, row, ["EXISTING-SERIAL"])
		parent["is_return"] = 1
		row["qty"] = -1
		user = self.make_stock_user()
		with self.set_user(user.name):
			self.assertFalse(frappe.has_permission("Serial No", "create"))
			self.assertEqual(resolve_transaction_serial_numbers(parent, row, ["EXISTING-SERIAL"]), names)

	def test_authorized_inward_resolution_creates_serials(self):
		item = make_item(properties={"has_serial_no": 1})
		parent = {"doctype": "Purchase Receipt", "__islocal": 1, "company": "_Test Company"}
		row = {"item_code": item.name, "qty": 1}
		names = resolve_transaction_serial_numbers(parent, row, ["AUTHORIZED-SERIAL"])
		serial = frappe.get_doc("Serial No", names[0])
		self.assertEqual(serial.item_code, item.name)
		self.assertEqual(serial.serial_no, "AUTHORIZED-SERIAL")
		self.assertEqual(serial.company, parent["company"])
		self.assertEqual(resolve_transaction_serial_numbers(parent, row, ["AUTHORIZED-SERIAL"]), names)
