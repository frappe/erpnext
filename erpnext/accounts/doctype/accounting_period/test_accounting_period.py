# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_months, nowdate

from erpnext.accounts.doctype.accounting_period.accounting_period import (
	ClosedAccountingPeriod,
	OverlapError,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

test_dependencies = ["Item"]


class TestAccountingPeriod(unittest.TestCase):
	def test_overlap(self):
		ap1 = create_accounting_period(
			start_date="2018-04-01", end_date="2018-06-30", company="Wind Power LLC"
		)
		ap1.save()

		ap2 = create_accounting_period(
			start_date="2018-06-30",
			end_date="2018-07-10",
			company="Wind Power LLC",
			period_name="Test Accounting Period 1",
		)
		self.assertRaises(OverlapError, ap2.save)

	def test_accounting_period(self):
		ap1 = create_accounting_period(period_name="Test Accounting Period 2")
		ap1.save()

		doc = create_sales_invoice(do_not_save=1, cost_center="_Test Company - _TC", warehouse="Stores - _TC")
		self.assertRaises(ClosedAccountingPeriod, doc.save)

	def tearDown(self):
		for d in frappe.get_all("Accounting Period"):
			frappe.delete_doc("Accounting Period", d.name)

	def test_get_doctypes_for_closing_TC_ACC_229(self):
		frappe.flags.in_test = True
		# Patch frappe.get_hooks safely
		original_get_hooks = frappe.get_hooks
		frappe.get_hooks = (
			lambda hook_name: ["Sales Invoice", "Purchase Invoice"]
			if hook_name == "period_closing_doctypes"
			else []
		)

		ap = frappe.new_doc("Accounting Period")

		docs_for_closing = ap.get_doctypes_for_closing()

		# Assertion: verify returned list structure
		self.assertEqual(len(docs_for_closing), 2)
		self.assertIn({"document_type": "Sales Invoice", "closed": 1}, docs_for_closing)
		self.assertIn({"document_type": "Purchase Invoice", "closed": 1}, docs_for_closing)

		# Restore original get_hooks after test
		frappe.get_hooks = original_get_hooks
		frappe.flags.in_test = False

	def test_bootstrap_doctypes_for_closing_TC_ACC_230(self):
		from frappe import _dict
		frappe.flags.in_test = True
		try:
			# Create test Accounting Period doc
			ap = frappe.new_doc("Accounting Period")
			ap.company = "_Test Company"
			ap.start_date = "2024-01-01"
			ap.end_date = "2024-12-31"
			ap.status = "Open"
			ap.set("closed_documents", [])

			# Patch get_doctypes_for_closing to return dict-like list
			ap.get_doctypes_for_closing = lambda: [
				_dict(document_type="Sales Invoice", closed=1),
				_dict(document_type="Purchase Invoice", closed=1),
			]
			
			# Call bootstrap method
			ap.bootstrap_doctypes_for_closing()

			# Assertions: verify child table populated
			self.assertEqual(len(ap.closed_documents), 2)
			document_types = [d.document_type for d in ap.closed_documents]
			self.assertIn("Sales Invoice", document_types)
			self.assertIn("Purchase Invoice", document_types)
		finally:
			frappe.flags.in_test = False

	def test_validate_accounting_period_on_doc_save_TC_ACC_231(self):
		from erpnext.accounts.doctype.accounting_period.accounting_period import (
			validate_accounting_period_on_doc_save,
		)

		frappe.flags.in_test = True

		# Create dummy Bank Clearance doc
		class DummyDoc:
			doctype = "Bank Clearance"
			company = "_Test Company"

		validate_accounting_period_on_doc_save(DummyDoc())

		# Create dummy Asset doc
		class DummyDoc:
			doctype = "Asset"
			company = "_Test Company"
			is_existing_asset = True

		# Create dummy Asset doc with available_for_use_date
		validate_accounting_period_on_doc_save(DummyDoc())

		class DummyDoc:
			doctype = "Asset"
			company = "_Test Company"
			is_existing_asset = False
			available_for_use_date = "2024-06-01"

		validate_accounting_period_on_doc_save(DummyDoc())
		frappe.flags.in_test = False


def create_accounting_period(**args):
	args = frappe._dict(args)

	accounting_period = frappe.new_doc("Accounting Period")
	accounting_period.start_date = args.start_date or nowdate()
	accounting_period.end_date = args.end_date or add_months(nowdate(), 1)
	accounting_period.company = args.company or "_Test Company"
	accounting_period.period_name = args.period_name or "_Test_Period_Name_1"
	accounting_period.append("closed_documents", {"document_type": "Sales Invoice", "closed": 1})

	return accounting_period
