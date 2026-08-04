# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.selling.report.sales_person_wise_transaction_summary.sales_person_wise_transaction_summary import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestSalesPersonWiseTransactionSummary(ERPNextTestSuite):
	"""Item-level summary joining a sales document with its Sales Team rows, showing
	each sales person's contributed qty and amount per item line."""

	def setUp(self):
		self.sales_person = "_Test Sales Person"

	def make_invoice_with_commission(self, qty=5, rate=200, percentage=100):
		si = create_sales_invoice(
			item="_Test Item", qty=qty, rate=rate, do_not_save=True, posting_date="2026-06-01"
		)
		si.append("sales_team", {"sales_person": self.sales_person, "allocated_percentage": percentage})
		si.insert()
		si.submit()
		return si

	def run_report(self, **extra):
		filters = frappe._dict(
			{"company": "_Test Company", "doc_type": "Sales Invoice", "sales_person": self.sales_person}
		)
		filters.update(extra)
		return execute(filters)[1]

	def test_doc_type_is_mandatory(self):
		self.assertRaises(frappe.ValidationError, execute, frappe._dict({"company": "_Test Company"}))

	def test_invalid_doc_type_throws(self):
		self.assertRaises(
			frappe.ValidationError,
			execute,
			frappe._dict({"company": "_Test Company", "doc_type": "Purchase Invoice"}),
		)

	def test_item_line_contribution(self):
		si = self.make_invoice_with_commission(qty=5, rate=200, percentage=100)
		item = si.items[0]

		rows = self.run_report()
		row = next((r for r in rows if r[0] == si.name and r[5] == "_Test Item"), None)
		self.assertIsNotNone(row, "Invoice item line missing from report")

		# row: name, customer, territory, warehouse, posting_date, item_code, item_group,
		#      brand, stock_qty, base_net_amount, sales_person, allocated_percentage,
		#      contributed_qty, contribution_amt, currency
		self.assertEqual(row[1], si.customer)
		self.assertEqual(row[8], item.stock_qty)
		self.assertEqual(row[9], item.base_net_amount)
		self.assertEqual(row[10], self.sales_person)
		self.assertEqual(row[11], 100)
		self.assertEqual(row[12], item.stock_qty * 100 / 100)  # contributed qty
		self.assertEqual(row[13], item.base_net_amount * 100 / 100)  # contribution amount

	def test_appends_total_row(self):
		self.make_invoice_with_commission()
		rows = self.run_report()
		self.assertTrue(rows)
		self.assertEqual(rows[-1], [""] * len(rows[0]))
