# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestStockEntryType(ERPNextTestSuite):
	def test_stock_entry_type_non_standard(self):
		stock_entry_type = "Test Manufacturing"

		doc = frappe.get_doc(
			{
				"doctype": "Stock Entry Type",
				"__newname": stock_entry_type,
				"purpose": "Manufacture",
				"is_standard": 1,
			}
		)

		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_stock_entry_type_is_standard(self):
		for stock_entry_type in [
			"Material Issue",
			"Material Receipt",
			"Material Transfer",
			"Material Transfer for Manufacture",
			"Material Consumption for Manufacture",
			"Manufacture",
			"Repack",
			"Send to Subcontractor",
		]:
			self.assertTrue(frappe.db.get_value("Stock Entry Type", stock_entry_type, "is_standard"))

	def test_add_to_transit_not_allowed_on_standard_type(self):
		doc = frappe.get_doc("Stock Entry Type", "Material Transfer")
		doc.add_to_transit = 1
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_patch_clears_add_to_transit_only_on_standard_types(self):
		from erpnext.patches.v16_0.disable_add_to_transit_on_standard_stock_entry_types import execute

		standard_types = ["Material Transfer", "Material Issue"]
		for name in standard_types:
			frappe.db.set_value("Stock Entry Type", name, "add_to_transit", 1)

		custom_type = "_Test Custom Transit Type"
		if not frappe.db.exists("Stock Entry Type", custom_type):
			frappe.get_doc(
				{"doctype": "Stock Entry Type", "__newname": custom_type, "purpose": "Material Transfer"}
			).insert()
		frappe.db.set_value("Stock Entry Type", custom_type, "add_to_transit", 1)

		execute()
		execute()

		for name in standard_types:
			self.assertEqual(frappe.db.get_value("Stock Entry Type", name, "add_to_transit"), 0)
		self.assertEqual(frappe.db.get_value("Stock Entry Type", custom_type, "add_to_transit"), 1)
