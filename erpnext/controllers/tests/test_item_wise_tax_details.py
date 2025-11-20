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
				"account_head": "_Test Account Shipping Charges - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Shipping",
				"rate": 50,
			},
		)
		self.doc.save()

		expected_values = [
			{
				"item_row": self.doc.items[0].name,
				"tax_row": self.doc.taxes[0].name,
				"rate": 10.0,
				"amount": 10.0,
				"taxable_amount": 100.0,
			},
			{
				"item_row": self.doc.items[0].name,
				"tax_row": self.doc.taxes[1].name,
				"rate": 14.0,
				"amount": 1.4,
				"taxable_amount": 10.0,
			},
			{
				"item_row": self.doc.items[0].name,
				"tax_row": self.doc.taxes[2].name,
				"rate": 5.0,
				"amount": 5.57,
				"taxable_amount": 111.4,
			},
			{
				"item_row": self.doc.items[0].name,
				"tax_row": self.doc.taxes[3].name,
				"rate": 50.0,
				"amount": 50.0,
				"taxable_amount": 0.0,
			},
		]

		actual_values = [
			{
				"item_row": row.item_row,
				"tax_row": row.tax_row,
				"rate": row.rate,
				"amount": row.amount,
				"taxable_amount": row.taxable_amount,
			}
			for row in self.doc.item_wise_tax_details
		]

		self.assertEqual(actual_values, expected_values)
