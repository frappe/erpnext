# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import today

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.report.billed_items_to_be_received.billed_items_to_be_received import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestBilledItemsToBeReceived(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"posting_date": today(),
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def get_rows_for(self, data, pi_name):
		return [row for row in data if row.get("name") == pi_name]

	def test_billed_but_not_received_item_appears(self):
		pi = make_purchase_invoice(
			supplier="_Test Supplier",
			item_code="_Test Item",
			qty=5,
			rate=200,
			update_stock=0,
		)

		rows = self.get_rows_for(self.run_report(), pi.name)
		self.assertEqual(len(rows), 1)

		row = rows[0]
		self.assertEqual(row.get("supplier"), "_Test Supplier")
		self.assertEqual(row.get("company"), "_Test Company")
		self.assertEqual(row.get("item_code"), "_Test Item")
		self.assertEqual(row.get("qty"), 5)
		self.assertEqual(row.get("received_qty"), 0)
		self.assertEqual(row.get("rate"), 200)
		self.assertEqual(row.get("amount"), 1000)

	def test_stock_updating_invoice_is_excluded(self):
		"""update_stock=1 means the item is already received; it must not appear."""
		pi = make_purchase_invoice(
			supplier="_Test Supplier",
			item_code="_Test Item",
			qty=5,
			rate=200,
			update_stock=1,
		)

		rows = self.get_rows_for(self.run_report(), pi.name)
		self.assertEqual(len(rows), 0)

	def test_fully_received_invoice_drops_off(self):
		"""When per_received reaches 100 the invoice is fully received and drops off."""
		pi = make_purchase_invoice(
			supplier="_Test Supplier",
			item_code="_Test Item",
			qty=5,
			rate=200,
			update_stock=0,
		)

		# Present while nothing has been received.
		self.assertEqual(len(self.get_rows_for(self.run_report(), pi.name)), 1)

		frappe.db.set_value("Purchase Invoice", pi.name, "per_received", 100)

		# Absent once fully received.
		self.assertEqual(len(self.get_rows_for(self.run_report(), pi.name)), 0)

	def test_posting_date_upper_bound_filter(self):
		"""A PI posted after the filter's posting_date must be excluded."""
		pi = make_purchase_invoice(
			supplier="_Test Supplier",
			item_code="_Test Item",
			qty=5,
			rate=200,
			update_stock=0,
		)

		rows = self.get_rows_for(self.run_report(posting_date="2000-01-01"), pi.name)
		self.assertEqual(len(rows), 0)

	def test_purchase_invoice_filter_scopes_to_that_invoice(self):
		"""The optional purchase_invoice filter must narrow to that invoice only."""
		pi = make_purchase_invoice(
			supplier="_Test Supplier", item_code="_Test Item", qty=5, rate=200, update_stock=0
		)
		other = make_purchase_invoice(
			supplier="_Test Supplier", item_code="_Test Item", qty=3, rate=200, update_stock=0
		)

		names = {row.get("name") for row in self.run_report(purchase_invoice=pi.name)}
		self.assertEqual(names, {pi.name})
		self.assertNotIn(other.name, names)
