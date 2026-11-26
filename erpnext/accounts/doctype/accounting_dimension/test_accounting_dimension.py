# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.handler import execute_cmd
from frappe.utils import set_request

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_dimensions,
	get_dimensions_for_user,
)
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.tests.permission_test_utils import as_user, make_fenced_user

test_dependencies = ["Cost Center", "Location", "Warehouse", "Department"]

GET_DIMENSIONS = "erpnext.accounts.doctype.accounting_dimension.accounting_dimension.get_dimensions"


class TestAccountingDimension(unittest.TestCase):
	def setUp(self):
		create_dimension()

	def test_client_dimension_defaults_only_for_companies_the_user_can_see(self):
		default_row = add_dimension_default("Department", "_Test Company 1", "_Test Department - _TC")
		# unittest.TestCase does not roll back, and later tests save this dimension as a company-fenced user
		self.addCleanup(frappe.db.delete, "Accounting Dimension Detail", {"name": default_row})
		limited_user = make_fenced_user(
			"_test_dimension_limited@example.com", ["Accounts User"], [("Company", "_Test Company")]
		)
		stock_user = make_fenced_user("_test_dimension_stock@example.com", ["Stock User"])
		dimensions = get_dimensions()[0]

		self.addCleanup(setattr, frappe.local, "request", None)
		with as_user(limited_user):
			limited_dimensions, limited_defaults = get_dimensions_for_user()
			# client scripts call the old path, which the hooks send to get_dimensions_for_user
			set_request(method="GET", path=f"/api/method/{GET_DIMENSIONS}")
			self.assertEqual(execute_cmd(GET_DIMENSIONS)[1], limited_defaults)
		self.assertEqual(limited_dimensions, dimensions)
		self.assertEqual(set(limited_defaults), {"_Test Company"})

		with as_user(stock_user):
			stock_dimensions, stock_defaults = get_dimensions_for_user(with_cost_center_and_project="true")
		self.assertEqual(stock_defaults["_Test Company 1"], {"department": "_Test Department - _TC"})
		self.assertEqual(
			[d.fieldname for d in stock_dimensions][-2:],
			["cost_center", "project"],
		)

	def test_client_dimension_lookup_refuses_website_users(self):
		website_user = make_fenced_user("_test_dimension_website@example.com", [])
		self.addCleanup(setattr, frappe.local, "request", None)

		with as_user(website_user):
			self.assertRaises(frappe.PermissionError, get_dimensions_for_user)

			set_request(method="GET", path=f"/api/method/{GET_DIMENSIONS}")
			self.assertRaises(frappe.PermissionError, execute_cmd, GET_DIMENSIONS)

			# server code keeps the unscoped lookup for any user
			self.assertIn("_Test Company", get_dimensions()[1])

	def test_dimension_against_sales_invoice(self):
		si = create_sales_invoice(do_not_save=1)

		si.location = "Block 1"
		si.append(
			"items",
			{
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC",
				"qty": 1,
				"rate": 100,
				"income_account": "Sales - _TC",
				"expense_account": "Cost of Goods Sold - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"department": "_Test Department - _TC",
				"location": "Block 1",
			},
		)

		si.save()
		si.submit()

		gle = frappe.get_doc("GL Entry", {"voucher_no": si.name, "account": "Sales - _TC"})

		self.assertEqual(gle.get("department"), "_Test Department - _TC")

	def test_dimension_against_journal_entry(self):
		je = make_journal_entry("Sales - _TC", "Sales Expenses - _TC", 500, save=False)
		je.accounts[0].update({"department": "_Test Department - _TC"})
		je.accounts[1].update({"department": "_Test Department - _TC"})

		je.accounts[0].update({"location": "Block 1"})
		je.accounts[1].update({"location": "Block 1"})

		je.save()
		je.submit()

		gle = frappe.get_doc("GL Entry", {"voucher_no": je.name, "account": "Sales - _TC"})
		gle1 = frappe.get_doc("GL Entry", {"voucher_no": je.name, "account": "Sales Expenses - _TC"})
		self.assertEqual(gle.get("department"), "_Test Department - _TC")
		self.assertEqual(gle1.get("department"), "_Test Department - _TC")

	def test_mandatory(self):
		si = create_sales_invoice(do_not_save=1)
		si.append(
			"items",
			{
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC",
				"qty": 1,
				"rate": 100,
				"income_account": "Sales - _TC",
				"expense_account": "Cost of Goods Sold - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"location": "",
			},
		)

		si.save()
		self.assertRaises(frappe.ValidationError, si.submit)

	def tearDown(self):
		disable_dimension()
		frappe.flags.accounting_dimensions_details = None
		frappe.flags.dimension_filter_map = None


def create_dimension():
	frappe.set_user("Administrator")

	if not frappe.db.exists("Accounting Dimension", {"document_type": "Department"}):
		dimension = frappe.get_doc(
			{
				"doctype": "Accounting Dimension",
				"document_type": "Department",
			}
		)
		dimension.append(
			"dimension_defaults",
			{
				"company": "_Test Company",
				"reference_document": "Department",
				"default_dimension": "_Test Department - _TC",
			},
		)
		dimension.insert()
		dimension.save()
	else:
		dimension = frappe.get_doc("Accounting Dimension", "Department")
		dimension.disabled = 0
		dimension.save()

	if not frappe.db.exists("Accounting Dimension", {"document_type": "Location"}):
		dimension1 = frappe.get_doc(
			{
				"doctype": "Accounting Dimension",
				"document_type": "Location",
			}
		)

		dimension1.append(
			"dimension_defaults",
			{
				"company": "_Test Company",
				"reference_document": "Location",
				"default_dimension": "Block 1",
				"mandatory_for_bs": 1,
			},
		)

		dimension1.insert()
		dimension1.save()
	else:
		dimension1 = frappe.get_doc("Accounting Dimension", "Location")
		dimension1.disabled = 0
		dimension1.save()


def disable_dimension():
	dimension1 = frappe.get_doc("Accounting Dimension", "Department")
	dimension1.disabled = 1
	dimension1.save()

	dimension2 = frappe.get_doc("Accounting Dimension", "Location")
	dimension2.disabled = 1
	dimension2.save()


def add_dimension_default(dimension, company, default_dimension):
	dimension_doc = frappe.get_doc("Accounting Dimension", dimension)
	default_row = frappe.get_doc(
		{
			"doctype": "Accounting Dimension Detail",
			"parent": dimension_doc.name,
			"parenttype": "Accounting Dimension",
			"parentfield": "dimension_defaults",
			"idx": len(dimension_doc.dimension_defaults) + 1,
			"company": company,
			"reference_document": dimension_doc.document_type,
			"default_dimension": default_dimension,
		}
	)
	default_row.db_insert()
	return default_row.name
