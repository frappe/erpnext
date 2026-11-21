# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	BLANK_ACCOUNTING_DIMENSION,
	get_accounting_dimensions,
	get_checks_for_pl_and_bs_accounts,
	get_dimension_filter_sql_condition,
	get_dimension_filter_values,
)
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.tests.utils import ERPNextTestSuite


class TestAccountingDimension(ERPNextTestSuite):
	def test_dimension_lookups_refresh_after_changes(self):
		dimension = frappe.get_doc("Accounting Dimension", "Location")
		original_disabled = dimension.disabled
		original_mandatory = dimension.dimension_defaults[0].mandatory_for_bs
		try:
			dimension.disabled = 0
			dimension.save()
			dimensions = get_accounting_dimensions(as_list=False)
			checks = get_checks_for_pl_and_bs_accounts()
			with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as queries:
				self.assertEqual(get_accounting_dimensions(), [d.fieldname for d in dimensions])
				self.assertEqual(get_checks_for_pl_and_bs_accounts(), checks)
				self.assertEqual(queries.call_count, 0)

			dimensions[0].fieldname = "changed"
			checks[0].mandatory_for_bs = "changed"
			self.assertNotIn("changed", get_accounting_dimensions())
			self.assertNotIn("changed", [d.mandatory_for_bs for d in get_checks_for_pl_and_bs_accounts()])

			dimension.dimension_defaults[0].mandatory_for_bs = not original_mandatory
			dimension.save()
			self.assertEqual(
				next(
					d.mandatory_for_bs
					for d in get_checks_for_pl_and_bs_accounts()
					if d.fieldname == dimension.fieldname
					and d.company == dimension.dimension_defaults[0].company
				),
				not original_mandatory,
			)

			dimension.disabled = 1
			dimension.save()
			self.assertNotIn(dimension.fieldname, get_accounting_dimensions())
			self.assertNotIn(dimension.fieldname, [d.fieldname for d in get_checks_for_pl_and_bs_accounts()])
		finally:
			dimension.disabled = original_disabled
			dimension.dimension_defaults[0].mandatory_for_bs = original_mandatory
			dimension.save()

	def test_blank_dimension_filter_sql_condition(self):
		condition, values = get_dimension_filter_sql_condition(
			"department",
			f'["_Test Department - _TC", "{BLANK_ACCOUNTING_DIMENSION}"]',
		)

		self.assertEqual(
			condition,
			"(department IN (?) OR (department IS NULL OR department = ''))",
		)
		self.assertEqual(values, ["_Test Department - _TC"])

	def test_dimension_filter_values_preserve_plain_string_names(self):
		values, include_blank = get_dimension_filter_values("null")

		self.assertEqual(values, ["null"])
		self.assertFalse(include_blank)

		values, include_blank = get_dimension_filter_values("__blank__")

		self.assertEqual(values, ["__blank__"])
		self.assertFalse(include_blank)

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
