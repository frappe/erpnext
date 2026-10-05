# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.report.received_items_to_be_billed.received_items_to_be_billed import execute
from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_invoice as make_pi_from_pr
from erpnext.stock.doctype.purchase_receipt.mapper import (
	make_purchase_return,
	make_purchase_return_against_rejected_warehouse,
)
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

	def test_billing_after_the_as_on_date_is_not_deducted(self):
		pr = make_purchase_receipt(qty=10, rate=100, posting_date="2026-06-01")
		pi = make_pi_from_pr(pr.name)
		pi.set_posting_time = 1
		pi.posting_date = "2026-06-20"
		pi.submit()

		returned_pr = make_purchase_receipt(qty=10, rate=100, posting_date="2026-06-01")
		make_receipt_return(returned_pr.name, qty=-4, posting_date="2026-06-20")

		data = self.run_report(posting_date="2026-06-10")
		row = self.get_row(data, pr.name)
		self.assertEqual((row.billed_amount, row.pending_amount), (0, 1000))
		row = self.get_row(data, returned_pr.name)
		self.assertEqual((row.returned_amount, row.pending_amount), (0, 1000))

		data = self.run_report(posting_date="2026-06-20")
		self.assertIsNone(self.get_row(data, pr.name))
		self.assertEqual(self.get_row(data, returned_pr.name).pending_amount, 600)

	def test_return_in_a_bigger_uom_deducts_its_own_amount(self):
		pr = make_purchase_receipt(
			qty=2, rate=1000, uom="_Test UOM 1", conversion_factor=10, posting_date="2026-06-01"
		)
		make_receipt_return(pr.name, qty=-1, posting_date="2026-06-02")

		row = self.get_row(self.run_report(), pr.name)
		self.assertEqual((row.returned_amount, row.pending_amount), (1000, 1000))

	def test_returning_rejected_qty_keeps_the_pending_amount(self):
		pr = make_purchase_receipt(qty=8, rejected_qty=2, rate=100, posting_date="2026-06-01")
		return_pr = make_purchase_return_against_rejected_warehouse(pr.name)
		return_pr.set_posting_time = 1
		return_pr.posting_date = "2026-06-02"
		return_pr.submit()

		row = self.get_row(self.run_report(), pr.name)
		self.assertEqual((row.returned_amount, row.pending_amount), (0, 800))


def make_receipt_return(purchase_receipt, qty, posting_date):
	return_pr = make_purchase_return(purchase_receipt)
	return_pr.set_posting_time = 1
	return_pr.posting_date = posting_date
	return_pr.items[0].qty = qty
	return_pr.items[0].received_qty = qty
	return_pr.submit()
	return return_pr
