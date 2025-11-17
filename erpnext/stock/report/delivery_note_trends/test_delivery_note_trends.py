import unittest

import frappe
from frappe.utils import add_days, today

from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.report.delivery_note_trends.delivery_note_trends import execute, get_chart_data


class TestDeliveryNoteTrendsReport(unittest.TestCase):
	def setUp(self):
		super().setUp()
		customer = frappe.get_doc(
			{"doctype": "Customer", "customer_name": "_Test Customer DN", "customer_type": "Individual"}
		).insert(ignore_permissions=True)
		item = create_item("_Test Item DN", {"is_stock_item": 1, "stock_uom": "Nos"})
		self.dn = frappe.get_doc(
			{
				"doctype": "Delivery Note",
				"customer": customer.name,
				"posting_date": today(),
				"company": frappe.defaults.get_user_default("Company"),
				"items": [
					{
						"item_code": item.name,
						"qty": 1,
						"rate": 100,
						"warehouse": frappe.defaults.get_user_default("Warehouse"),
					}
				],
			}
		).insert(ignore_permissions=True)
		self.dn.submit()
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")

	def test_execute_with_valid_filters_T_DNT_001(self):
		from frappe import _dict

		from erpnext.stock.report.delivery_note_trends import delivery_note_trends

		fiscal_year = frappe.defaults.get_user_default("fiscal_year") or "2024-2025"

		filters = _dict(
			{
				"value_quantity": "Value",
				"period": "Monthly",
				"based_on": "Customer",
				"group_by": "Item",
				"company": frappe.defaults.get_user_default("company"),
				"from_date": add_days(today(), -30),
				"to_date": today(),
				"fiscal_year": fiscal_year,
			}
		)

		columns, data, _, chart_data = delivery_note_trends.execute(filters)
		self.assertTrue(columns)
		self.assertTrue(data)
		self.assertTrue(chart_data)

	def test_execute_with_fiscal_year_filter_T_DNT_002(self):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": "2025",
				"based_on": "Customer",
				"group_by": "Item",
				"period": "Monthly",
				"period_based_on": "posting_date",
			}
		)

		cols, data, none_val, chart = execute(filters)

		self.assertIsInstance(cols, list)
		self.assertIsInstance(data, list)
		self.assertIsNone(none_val)
		self.assertIsInstance(chart, dict)
		self.assertIn("data", chart)

	def test_get_chart_data_empty_T_DNT_003(self):
		result = get_chart_data([], {})
		self.assertEqual(result, [])

	def test_execute_with_empty_filters_T_DNT_004(self):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": "2025",
				"based_on": "Customer",
				"group_by": "Item",
				"period": "Monthly",
				"period_based_on": "posting_date",
			}
		)

		cols, data, none_val, chart = execute(filters)

		self.assertIsInstance(cols, list)
		self.assertIsInstance(data, list)
		self.assertIsNone(none_val)
		self.assertIsInstance(chart, dict)
		self.assertIn("data", chart)

	def test_get_chart_data_empty_T_DNT_005(self):
		result = get_chart_data([], {})
		self.assertEqual(result, [])

	def test_get_chart_data_group_by_true_T_DNT_006(self):
		data = [["Group 1", 100], [None, 200], ["Group 2", 300]]
		filters = {"group_by": True}
		result = get_chart_data(data, filters)
		self.assertTrue(all(row in ["Group 1", "Group 2"] for row in result["data"]["labels"]))
		self.assertEqual(result["type"], "bar")
		self.assertEqual(result["fieldtype"], "Currency")

	def test_get_chart_data_top_10_T_DNT_007(self):
		data = [[f"Label{i}", i * 10] for i in range(15)]
		filters = {}
		result = get_chart_data(data, filters)
		self.assertEqual(len(result["data"]["labels"]), 10)
		self.assertEqual(result["type"], "bar")

	def test_get_chart_data_less_than_10_no_group_by_T_DNT_008(self):
		data = [["Label A", 150], ["Label B", 250], ["Label C", 50]]
		filters = {}
		result = get_chart_data(data, filters)
		self.assertEqual(set(result["data"]["labels"]), {"Label A", "Label B", "Label C"})
		self.assertEqual(result["type"], "bar")
