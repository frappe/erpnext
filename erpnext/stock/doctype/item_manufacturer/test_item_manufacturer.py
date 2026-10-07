# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


class TestItemManufacturer(ERPNextTestSuite):
	def setUp(self):
		self.item_code = make_item(properties={"is_stock_item": 1}).name
		for manufacturer in ("_Test IM Maker 1", "_Test IM Maker 2"):
			if not frappe.db.exists("Manufacturer", manufacturer):
				frappe.get_doc({"doctype": "Manufacturer", "short_name": manufacturer}).insert()

	def make_row(self, manufacturer, part_no, is_default=0):
		return frappe.get_doc(
			{
				"doctype": "Item Manufacturer",
				"item_code": self.item_code,
				"manufacturer": manufacturer,
				"manufacturer_part_no": part_no,
				"is_default": is_default,
			}
		).insert()

	def get_item_default(self):
		return tuple(
			frappe.db.get_value(
				"Item", self.item_code, ["default_item_manufacturer", "default_manufacturer_part_no"]
			)
		)

	def test_editing_row_into_duplicate_is_refused(self):
		self.make_row("_Test IM Maker 1", "P-1", is_default=1)
		other = self.make_row("_Test IM Maker 1", "P-2")

		other.manufacturer_part_no = "P-1"
		self.assertRaises(frappe.ValidationError, other.save)
		self.assertEqual(self.get_item_default(), ("_Test IM Maker 1", "P-1"))

	def test_editing_default_row_clears_old_item_default(self):
		row = self.make_row("_Test IM Maker 1", "P-1", is_default=1)

		row.update({"manufacturer": "_Test IM Maker 2", "manufacturer_part_no": "Q-9", "is_default": 0})
		row.save()

		self.assertEqual(self.get_item_default(), (None, None))

	def test_default_needs_item_write_permission(self):
		from frappe.core.doctype.user_permission.test_user_permission import create_user

		user = create_user("test_item_manufacturer@example.com", "Stock User")
		frappe.set_user(user.name)
		try:
			self.assertRaises(frappe.PermissionError, self.make_row, "_Test IM Maker 2", "SU-1", 1)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(self.get_item_default(), (None, None))
