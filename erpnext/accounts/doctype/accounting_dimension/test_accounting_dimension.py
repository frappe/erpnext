# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimensions
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.tests.permission_test_utils import as_user, make_company_fenced_user
from erpnext.tests.utils import ERPNextTestSuite


class TestAccountingDimension(ERPNextTestSuite):
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

	def test_fieldname_cannot_change_after_creation(self):
		dimension = frappe.get_doc("Accounting Dimension", "Department")
		dimension.fieldname = "department_renamed"

		self.assertRaisesRegex(frappe.ValidationError, "Cannot change the fieldname", dimension.save)

	def test_get_dimensions_returns_defaults_of_permitted_companies(self):
		dimension = frappe.get_doc("Accounting Dimension", "Department")
		dimension.append(
			"dimension_defaults",
			{"company": "_Test Company 1", "reference_document": "Department", "default_dimension": None},
		)
		dimension.save()

		self.assertIn("_Test Company 1", get_dimensions()[1])

		user = make_company_fenced_user("dimension-reader@example.com", ["Accounts User"], "_Test Company")
		with as_user(user):
			default_dimensions = get_dimensions()[1]

		self.assertIn("_Test Company", default_dimensions)
		self.assertNotIn("_Test Company 1", default_dimensions)

	def test_get_dimensions_reads_permitted_companies_once_per_request(self):
		frappe.local.request_cache.clear()
		with patch("frappe.get_list", wraps=frappe.get_list) as get_list:
			get_dimensions()
			get_dimensions()

		self.assertEqual(get_list.call_count, 1)

	def test_get_dimensions_skips_defaults_of_disabled_dimension(self):
		self.assertIn("location", get_dimensions()[1]["_Test Company"])

		frappe.db.set_value("Accounting Dimension", "Location", "disabled", 1)

		self.assertNotIn("location", get_dimensions()[1]["_Test Company"])

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

	def test_child_table_not_allowed_as_dimension(self):
		dimension = frappe.get_doc({"doctype": "Accounting Dimension", "document_type": "Sales Team"})
		self.assertRaises(frappe.ValidationError, dimension.insert)

	def test_single_doctype_not_allowed_as_dimension(self):
		dimension = frappe.get_doc({"doctype": "Accounting Dimension", "document_type": "Selling Settings"})
		self.assertRaises(frappe.ValidationError, dimension.insert)

	def test_non_scalar_dimension_value_skipped_in_gl_dict(self):
		si = create_sales_invoice(do_not_save=1)

		si.department = "_Test Department - _TC"
		self.assertEqual(si.get_gl_dict({}).get("department"), "_Test Department - _TC")

		si.department = ["_Test Department - _TC"]
		self.assertNotIn("department", si.get_gl_dict({}))

	def test_resave_does_not_warn_about_its_own_fields(self):
		frappe.clear_messages()
		frappe.get_doc("Accounting Dimension", "Location").save()
		self.assertFalse([m for m in frappe.message_log if m.get("title") == "Fieldname Conflict"])

	def test_mandatory(self):
		location = frappe.get_doc("Accounting Dimension", "Location")
		location.dimension_defaults[0].mandatory_for_bs = True
		location.save()

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
