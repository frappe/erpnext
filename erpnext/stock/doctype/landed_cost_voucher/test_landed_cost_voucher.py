# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt \
	import set_perpetual_inventory, get_gl_entries, test_records as pr_test_records


class TestLandedCostVoucher(unittest.TestCase):
	def test_landed_cost_voucher(self):
		set_perpetual_inventory(1)
		pr = self.submit_pr()
		self.submit_landed_cost_voucher(pr)
		
		pr_lc_value = frappe.db.get_value("Purchase Receipt Item", {"parent": pr.name}, "landed_cost_voucher_amount")
		self.assertEquals(pr_lc_value, 25.0)
		
		gl_entries = get_gl_entries("Purchase Receipt", pr.name)

		self.assertTrue(gl_entries)

		stock_in_hand_account = pr.get("purchase_receipt_details")[0].warehouse
		fixed_asset_account = pr.get("purchase_receipt_details")[1].warehouse
		

		expected_values = {
			stock_in_hand_account: [400.0, 0.0],
			fixed_asset_account: [400.0, 0.0],
			"Stock Received But Not Billed - _TC": [0.0, 500.0],
			"Expenses Included In Valuation - _TC": [0.0, 300.0]
		}

		for gle in gl_entries:
			self.assertEquals(expected_values[gle.account][0], gle.debit)
			self.assertEquals(expected_values[gle.account][1], gle.credit)

		set_perpetual_inventory(0)
		
	def submit_landed_cost_voucher(self, pr):
		lcv = frappe.new_doc("Landed Cost Voucher")
		lcv.company = "_Test Company"
		lcv.set("landed_cost_purchase_receipts", [{
			"purchase_receipt": pr.name,
			"supplier": pr.supplier,
			"posting_date": pr.posting_date,
			"grand_total": pr.grand_total
		}])
		lcv.set("landed_cost_taxes_and_charges", [{
			"description": "Insurance Charges",
			"account": "_Test Account Insurance Charges - _TC",
			"amount": 50.0
		}])
		
		lcv.insert()
		lcv.submit()
		
	def submit_pr(self):
		pr = frappe.copy_doc(pr_test_records[0])
		pr.submit()
		return pr
		
	

test_records = frappe.get_test_records('Landed Cost Voucher')