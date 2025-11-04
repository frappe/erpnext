import unittest
from functools import partial

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.core.doctype.user_permission.user_permission import add_user_permissions
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from erpnext.controllers import queries
from erpnext.tests.utils import ERPNextTestSuite


def add_default_params(func, doctype):
	return partial(func, doctype=doctype, txt="", searchfield="name", start=0, page_len=20, filters=None)


EXTRA_TEST_RECORD_DEPENDENCIES = ["Item", "BOM", "Account"]


class TestQueries(ERPNextTestSuite):
	# All tests are based on self.globalTestRecords[doctype]

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.make_employees()
		cls.make_leads()
		cls.make_projects()

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
		query = add_default_params(queries.get_project_name, "Project")

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

	def test_employee_query_with_user_permissions(self):
		# party field is a dynamic link field in Payment Entry doctype with ignore_user_permissions=0
		ps = make_property_setter(
			doctype="Payment Entry",
			fieldname="party",
			property="ignore_user_permissions",
			value=1,
			property_type="Check",
		)

		user = create_user("test_employee_query@example.com", "Accounts User", "HR User")
		add_user_permissions(
			{
				"user": user.name,
				"doctype": "Employee",
				"docname": self.employees[0].name,
				"is_default": 1,
				"apply_to_all_doctypes": 1,
				"applicable_doctypes": [],
				"hide_descendants": 0,
			}
		)

		with self.set_user(user.name):
			params = {
				"doctype": "Employee",
				"txt": "",
				"searchfield": "name",
				"start": 0,
				"page_len": 20,
				"filters": None,
				"reference_doctype": "Payment Entry",
				"ignore_user_permissions": 1,
			}

			result = queries.employee_query(**params)
			self.assertGreater(len(result), 1)

			ps.delete(ignore_permissions=1, force=1, delete_permanently=1)

			# only one employee should be returned even though ignore_user_permissions is passed as 1
			result = queries.employee_query(**params)
			self.assertEqual(len(result), 1)
