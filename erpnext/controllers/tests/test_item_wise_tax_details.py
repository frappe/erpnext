import json

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals


class TestTaxesAndTotals(FrappeTestCase):
	def setUp(self):
		self.doc = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"customer": "_Test Customer",
				"company": "_Test Company",
				"currency": "INR",
				"conversion_rate": 1,
				"items": [
					{
						"item_code": "_Test Item",
						"qty": 1,
						"rate": 100,
						"income_account": "Sales - _TC",
						"expense_account": "Cost of Goods Sold - _TC",
						"cost_center": "_Test Cost Center - _TC",
					}
				],
				"taxes": [],
			}
		)

	def test_item_wise_tax_detail(self):
		# Test On Net Total
		self.doc.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account VAT - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "VAT",
				"rate": 10,
			},
		)

		# Test On Previous Row Amount
		self.doc.append(
			"taxes",
			{
				"charge_type": "On Previous Row Amount",
				"account_head": "_Test Account Service Tax - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Service Tax",
				"rate": 14,
				"row_id": 1,
			},
		)

		# Test On Previous Row Total
		self.doc.append(
			"taxes",
			{
				"charge_type": "On Previous Row Total",
				"account_head": "_Test Account Customs Duty - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Customs Duty",
				"rate": 5,
				"row_id": 2,
			},
		)

		# Test On Item Quantity
		self.doc.append(
			"taxes",
			{
				"charge_type": "On Item Quantity",
				"account_head": "_Test Account Shipping - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Shipping",
				"rate": 50,
			},
		)
		self.doc.set_missing_item_details()
		calculate_taxes_and_totals(self.doc)

		expected_values = {
			"VAT": {"tax_rate": 10, "tax_amount": 10, "net_amount": 100},
			"Service Tax": {"tax_rate": 14, "tax_amount": 1.4, "net_amount": 10},
			"Customs Duty": {"tax_rate": 5, "tax_amount": 5.57, "net_amount": 111.4},
			"Shipping": {"tax_rate": 50, "tax_amount": 50, "net_amount": 0.0},  # net_amount: here qty
		}

		for tax in self.doc.taxes:
			self.assertIn(tax.description, expected_values)
			item_wise_tax_detail = json.loads(tax.item_wise_tax_detail)
			tax_detail = item_wise_tax_detail[self.doc.items[0].item_code]
			self.assertAlmostEqual(tax_detail.get("tax_rate"), expected_values[tax.description]["tax_rate"])
			self.assertAlmostEqual(
				tax_detail.get("tax_amount"), expected_values[tax.description]["tax_amount"]
			)
			self.assertAlmostEqual(
				tax_detail.get("net_amount"), expected_values[tax.description]["net_amount"]
			)
			# Check if net_total is set for each tax
			self.assertEqual(tax.net_amount, expected_values[tax.description]["net_amount"])
