import unittest
from functools import partial

import frappe

from erpnext.controllers import queries


def add_default_params(func, doctype):
	return partial(
		func, doctype=doctype, txt="", searchfield="name", start=0, page_len=20, filters=None
	)


class TestQueries(unittest.TestCase):

	# All tests are based on doctype/test_records.json

	def assert_nested_in(self, item, container):
		self.assertIn(item, [vals for tuples in container for vals in tuples])

	def test_employee_query(self):
		query = add_default_params(queries.employee_query, "Employee")

		self.assertGreaterEqual(len(query(txt="_Test Employee")), 3)
		self.assertGreaterEqual(len(query(txt="_Test Employee 1")), 1)

	def test_lead_query(self):
		query = add_default_params(queries.lead_query, "Lead")

		self.assertGreaterEqual(len(query(txt="_Test Lead")), 4)
		self.assertEqual(len(query(txt="_Test Lead 4")), 1)

	def test_customer_query(self):
		query = add_default_params(queries.customer_query, "Customer")

		self.assertGreaterEqual(len(query(txt="_Test Customer")), 7)
		self.assertGreaterEqual(len(query(txt="_Test Customer USD")), 1)

	def test_supplier_query(self):
		query = add_default_params(queries.supplier_query, "Supplier")

		self.assertGreaterEqual(len(query(txt="_Test Supplier")), 7)
		self.assertGreaterEqual(len(query(txt="_Test Supplier USD")), 1)

	def test_item_query(self):
		query = add_default_params(queries.item_query, "Item")

		self.assertGreaterEqual(len(query(txt="_Test Item")), 7)
		self.assertEqual(len(query(txt="_Test Item Home Desktop 100 3")), 1)

		fg_item = "_Test FG Item"
		stock_items = query(txt=fg_item, filters={"is_stock_item": 1})
		self.assert_nested_in("_Test FG Item", stock_items)

		bundled_stock_items = query(txt="_test product bundle item 5", filters={"is_stock_item": 1})
		self.assertEqual(len(bundled_stock_items), 0)

		# empty customer/supplier should be stripped of instead of failure
		query(txt="", filters={"customer": None})
		query(txt="", filters={"customer": ""})
		query(txt="", filters={"supplier": None})
		query(txt="", filters={"supplier": ""})

	def test_bom_qury(self):
		query = add_default_params(queries.bom, "BOM")

		self.assertGreaterEqual(len(query(txt="_Test Item Home Desktop Manufactured")), 1)

	def test_project_query(self):
		query = add_default_params(queries.get_project_name, "BOM")

		self.assertGreaterEqual(len(query(txt="_Test Project")), 1)

	def test_account_query(self):
		query = add_default_params(queries.get_account_list, "Account")

		debtor_accounts = query(txt="Debtors", filters={"company": "_Test Company"})
		self.assert_nested_in("Debtors - _TC", debtor_accounts)

	def test_income_account_query(self):
		query = add_default_params(queries.get_income_account, "Account")

		self.assertGreaterEqual(len(query(filters={"company": "_Test Company"})), 1)

	def test_expense_account_query(self):
		query = add_default_params(queries.get_expense_account, "Account")

		self.assertGreaterEqual(len(query(filters={"company": "_Test Company"})), 1)

	def test_warehouse_query(self):
		query = add_default_params(queries.warehouse_query, "Account")

		wh = query(filters=[["Bin", "item_code", "=", "_Test Item"]])
		self.assertGreaterEqual(len(wh), 1)

	def test_default_uoms(self):
		self.assertGreaterEqual(frappe.db.count("UOM", {"enabled": 1}), 10)
