# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.report.received_items_to_be_billed.received_items_to_be_billed import execute
from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_invoice as make_pi_from_pr
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.tests.utils import ERPNextTestSuite


class TestReceivedItemsToBeBilled(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"posting_date": "2026-06-30",
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def get_row(self, data, purchase_receipt):
		matches = [row for row in data if row.get("name") == purchase_receipt]
		return matches[0] if matches else None

	def test_unbilled_receipt_appears_with_pending_amount(self):
		pr = make_purchase_receipt(
			item_code="_Test Item",
			qty=5,
			rate=200,
			supplier="_Test Supplier",
			posting_date="2026-06-01",
		)

		row = self.get_row(self.run_report(), pr.name)

		self.assertIsNotNone(row, "Unbilled Purchase Receipt should appear in the report")
		self.assertEqual(row.get("supplier"), "_Test Supplier")
		self.assertEqual(row.get("item_code"), "_Test Item")
		self.assertEqual(row.get("amount"), 1000.0)
		self.assertEqual(row.get("billed_amount"), 0.0)
		self.assertEqual(row.get("returned_amount"), 0.0)
		self.assertEqual(row.get("pending_amount"), 1000.0)

	def test_billed_receipt_drops_out_of_report(self):
		pr = make_purchase_receipt(
			item_code="_Test Item",
			qty=5,
			rate=200,
			supplier="_Test Supplier",
			posting_date="2026-06-01",
		)

		self.assertIsNotNone(self.get_row(self.run_report(), pr.name))

		pi = make_pi_from_pr(pr.name)
		pi.set_posting_time = 1
		pi.posting_date = "2026-06-02"
		pi.submit()

		self.assertIsNone(
			self.get_row(self.run_report(), pr.name),
			"Fully billed Purchase Receipt should no longer appear in the report",
		)

	def test_reference_field_filter_limits_to_single_receipt(self):
		first_pr = make_purchase_receipt(
			item_code="_Test Item",
			qty=5,
			rate=200,
			supplier="_Test Supplier",
			posting_date="2026-06-01",
		)
		second_pr = make_purchase_receipt(
			item_code="_Test Item",
			qty=3,
			rate=100,
			supplier="_Test Supplier",
			posting_date="2026-06-01",
		)

		data = self.run_report(purchase_receipt=first_pr.name)

		self.assertIsNotNone(self.get_row(data, first_pr.name))
		self.assertIsNone(self.get_row(data, second_pr.name))

	def test_posting_date_cutoff_excludes_later_receipts(self):
		pr = make_purchase_receipt(
			item_code="_Test Item",
			qty=5,
			rate=200,
			supplier="_Test Supplier",
			posting_date="2026-06-15",
		)

		self.assertIsNone(
			self.get_row(self.run_report(posting_date="2026-06-01"), pr.name),
			"Receipt dated after the cutoff should be excluded",
		)
		self.assertIsNotNone(self.get_row(self.run_report(posting_date="2026-06-30"), pr.name))
