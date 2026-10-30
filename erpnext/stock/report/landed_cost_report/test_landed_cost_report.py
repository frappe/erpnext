# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.stock.doctype.landed_cost_voucher.test_landed_cost_voucher import (
	create_landed_cost_voucher,
)
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.report.landed_cost_report.landed_cost_report import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestLandedCostReport(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": add_days(today(), -1),
				"to_date": add_days(today(), 1),
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def make_voucher_for_two_receipts(self):
		from erpnext.stock.doctype.landed_cost_voucher.test_landed_cost_voucher import (
			distribute_landed_cost_on_items,
			get_expense_account,
		)

		receipts = [
			make_purchase_receipt(item_code="_Test Item", qty=qty, rate=100, warehouse="Stores - _TC")
			for qty in (10, 5)
		]
		lcv = frappe.new_doc("Landed Cost Voucher")
		lcv.company = "_Test Company"
		lcv.distribute_charges_based_on = "Amount"
		for receipt in receipts:
			lcv.append(
				"purchase_receipts",
				{
					"receipt_document_type": "Purchase Receipt",
					"receipt_document": receipt.name,
					"supplier": receipt.supplier,
					"posting_date": receipt.posting_date,
					"grand_total": receipt.base_grand_total,
				},
			)
		lcv.append(
			"taxes",
			{
				"description": "Freight",
				"expense_account": get_expense_account("_Test Company"),
				"amount": 300,
			},
		)
		lcv.insert()
		distribute_landed_cost_on_items(lcv)
		lcv.submit()
		return lcv, receipts

	def test_receipt_rows_show_their_share_of_the_landed_cost(self):
		lcv, receipts = self.make_voucher_for_two_receipts()

		rows = self.run_report(raw_material_voucher_no=receipts[1].name)

		self.assertEqual(
			[(row.get("voucher_no"), row.get("landed_cost")) for row in rows], [(receipts[1].name, 100)]
		)

	def test_vendor_invoices_are_listed_on_their_own_rows(self):
		lcv, receipts = self.make_voucher_for_two_receipts()
		for idx, invoice in enumerate(("FREIGHT-INV", "CUSTOMS-INV"), start=1):
			frappe.get_doc(
				{
					"doctype": "Landed Cost Vendor Invoice",
					"parent": lcv.name,
					"parenttype": "Landed Cost Voucher",
					"parentfield": "vendor_invoices",
					"vendor_invoice": invoice,
					"idx": idx,
					"docstatus": 1,
				}
			).db_insert()

		rows = self.run_report()
		start = next(idx for idx, row in enumerate(rows) if row.get("name") == lcv.name)

		self.assertEqual(
			[
				(row.get("voucher_no"), row.get("landed_cost"), row.get("vendor_invoice"))
				for row in rows[start : start + 4]
			],
			[
				(receipts[0].name, 200, None),
				(receipts[1].name, 100, None),
				(None, None, "FREIGHT-INV"),
				(None, None, "CUSTOMS-INV"),
			],
		)
