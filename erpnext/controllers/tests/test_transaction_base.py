import unittest

import frappe


class TestUtils(unittest.TestCase):
	def test_reset_default_field_value(self):
		doc = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"set_warehouse": "Warehouse 1",
			}
		)

		# Same values
		doc.items = [
			{"warehouse": "Warehouse 1"},
			{"warehouse": "Warehouse 1"},
			{"warehouse": "Warehouse 1"},
		]
		doc.reset_default_field_value("set_warehouse", "items", "warehouse")
		self.assertEqual(doc.set_warehouse, "Warehouse 1")

		# Mixed values
		doc.items = [
			{"warehouse": "Warehouse 1"},
			{"warehouse": "Warehouse 2"},
			{"warehouse": "Warehouse 1"},
		]
		doc.reset_default_field_value("set_warehouse", "items", "warehouse")
		self.assertEqual(doc.set_warehouse, None)

	def test_reset_default_field_value_in_mfg_stock_entry(self):
		# manufacture stock entry with rows having blank source/target wh
		se = frappe.get_doc(
			doctype="Stock Entry",
			purpose="Manufacture",
			stock_entry_type="Manufacture",
			company="_Test Company",
			from_warehouse="_Test Warehouse - _TC",
			to_warehouse="_Test Warehouse 1 - _TC",
			items=[
				frappe._dict(
					item_code="_Test Item", qty=1, basic_rate=200, s_warehouse="_Test Warehouse - _TC"
				),
				frappe._dict(
					item_code="_Test FG Item",
					qty=4,
					t_warehouse="_Test Warehouse 1 - _TC",
					is_finished_item=1,
				),
			],
		)
		se.save()

		# default fields must be untouched
		self.assertEqual(se.from_warehouse, "_Test Warehouse - _TC")
		self.assertEqual(se.to_warehouse, "_Test Warehouse 1 - _TC")

		se.delete()

	def test_reset_default_field_value_in_transfer_stock_entry(self):
		doc = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"purpose": "Material Receipt",
				"from_warehouse": "Warehouse 1",
				"to_warehouse": "Warehouse 2",
			}
		)

		# Same values
		doc.items = [
			{"s_warehouse": "Warehouse 1", "t_warehouse": "Warehouse 2"},
			{"s_warehouse": "Warehouse 1", "t_warehouse": "Warehouse 2"},
			{"s_warehouse": "Warehouse 1", "t_warehouse": "Warehouse 2"},
		]

		doc.reset_default_field_value("from_warehouse", "items", "s_warehouse")
		doc.reset_default_field_value("to_warehouse", "items", "t_warehouse")
		self.assertEqual(doc.from_warehouse, "Warehouse 1")
		self.assertEqual(doc.to_warehouse, "Warehouse 2")

		# Mixed values in source wh
		doc.items = [
			{"s_warehouse": "Warehouse 1", "t_warehouse": "Warehouse 2"},
			{"s_warehouse": "Warehouse 3", "t_warehouse": "Warehouse 2"},
			{"s_warehouse": "Warehouse 1", "t_warehouse": "Warehouse 2"},
		]

		doc.reset_default_field_value("from_warehouse", "items", "s_warehouse")
		doc.reset_default_field_value("to_warehouse", "items", "t_warehouse")
		self.assertEqual(doc.from_warehouse, None)
		self.assertEqual(doc.to_warehouse, "Warehouse 2")
