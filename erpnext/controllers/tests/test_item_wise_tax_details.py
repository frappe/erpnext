import frappe
from frappe.utils import flt

from erpnext.tests.utils import ERPNextTestSuite, change_settings


class TestTaxesAndTotals(ERPNextTestSuite):
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

	@change_settings("Selling Settings", {"allow_multiple_items": 1})
	def test_item_wise_tax_detail_high_conversion_rate(self):
		"""
		With a high conversion rate (e.g. USD -> KRW ~1300), independently rounding
		each item's base tax amount causes per-item errors that accumulate and exceed
		the 0.5-unit safety threshold, raising a validation error.

		Error diffusion fixes this: the cumulative base total after the last item
		equals base_tax_amount_after_discount_amount exactly, so the sum of all
		per-item amounts is always exact regardless of item count or rate magnitude.

		Analytically with conversion_rate=1300, rate=7.77 x3 items, VAT 16%:
		per-item txn tax = 1.2432
		OLD independent: flt(1.2432 * 1300, 2) = 1616.16 -> sum 4848.48
		expected base:   flt(flt(3.7296, 2) * 1300, 0) = flt(3.73 * 1300, 0) = 4849
		diff = 0.52 -> exceeds 0.5 threshold -> would throw with old code
		"""
		doc = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"customer": "_Test Customer",
				"company": "_Test Company",
				"currency": "USD",
				"debit_to": "_Test Receivable USD - _TC",
				"conversion_rate": 1300,
				"items": [
					{
						"item_code": "_Test Item",
						"qty": 1,
						"rate": 7.77,
						"income_account": "Sales - _TC",
						"expense_account": "Cost of Goods Sold - _TC",
						"cost_center": "_Test Cost Center - _TC",
					},
					{
						"item_code": "_Test Item",
						"qty": 1,
						"rate": 7.77,
						"income_account": "Sales - _TC",
						"expense_account": "Cost of Goods Sold - _TC",
						"cost_center": "_Test Cost Center - _TC",
					},
					{
						"item_code": "_Test Item",
						"qty": 1,
						"rate": 7.77,
						"income_account": "Sales - _TC",
						"expense_account": "Cost of Goods Sold - _TC",
						"cost_center": "_Test Cost Center - _TC",
					},
				],
				"taxes": [
					{
						"charge_type": "On Net Total",
						"account_head": "_Test Account VAT - _TC",
						"cost_center": "_Test Cost Center - _TC",
						"description": "VAT",
						"rate": 16,
					},
					{
						"charge_type": "On Previous Row Amount",
						"account_head": "_Test Account Service Tax - _TC",
						"cost_center": "_Test Cost Center - _TC",
						"description": "Service Tax",
						"rate": 10,
						"row_id": 1,
					},
				],
			}
		)
		doc.save()

		details_by_tax = {}
		for detail in doc.item_wise_tax_details:
			bucket = details_by_tax.setdefault(detail.tax_row, 0.0)
			details_by_tax[detail.tax_row] = bucket + detail.amount

		for tax in doc.taxes:
			self.assertEqual(details_by_tax[tax.name], tax.base_tax_amount_after_discount_amount)

	@change_settings("Selling Settings", {"allow_multiple_items": 1})
	def test_rounding_in_item_wise_tax_details(self):
		"""
		This test verifies the amounts are properly rounded.
		"""
		doc = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"customer": "_Test Customer",
				"company": "_Test Company",
				"currency": "INR",
				"conversion_rate": 1,
				"items": [
					{
						"item_code": "_Test Item",
						"qty": 5,
						"rate": 20,
						"income_account": "Sales - _TC",
						"expense_account": "Cost of Goods Sold - _TC",
						"cost_center": "_Test Cost Center - _TC",
					},
					{
						"item_code": "_Test Item",
						"qty": 3,
						"rate": 19,
						"income_account": "Sales - _TC",
						"expense_account": "Cost of Goods Sold - _TC",
						"cost_center": "_Test Cost Center - _TC",
					},
					{
						"item_code": "_Test Item",
						"qty": 1,
						"rate": 1000,
						"income_account": "Sales - _TC",
						"expense_account": "Cost of Goods Sold - _TC",
						"cost_center": "_Test Cost Center - _TC",
					},
				],
				"taxes": [
					{
						"charge_type": "On Net Total",
						"account_head": "_Test Account VAT - _TC",
						"cost_center": "_Test Cost Center - _TC",
						"description": "VAT",
						"rate": 9,
					},
				],
			}
		)
		doc.save()

		# item 1: taxable=100, tax=9.0; item 2: taxable=57, tax=5.13; item 3: taxable=1000, tax=90.0
		# error diffusion: 14.13 - 9.0 = 5.130000000000001 without rounding
		for detail in doc.item_wise_tax_details:
			self.assertEqual(detail.amount, flt(detail.amount, detail.precision("amount")))

	def test_item_wise_tax_detail_with_multi_currency_with_single_item(self):
		"""
		When the tax amount (in transaction currency) has more decimals than
		the field precision, rounding must happen *before* multiplying by
		conversion_rate — the same order used by _set_in_company_currency.
		"""
		doc = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"customer": "_Test Customer",
				"company": "_Test Company",
				"currency": "USD",
				"debit_to": "_Test Receivable USD - _TC",
				"conversion_rate": 129.99,
				"items": [
					{
						"item_code": "_Test Item",
						"qty": 1,
						"rate": 47.41,
						"income_account": "Sales - _TC",
						"expense_account": "Cost of Goods Sold - _TC",
						"cost_center": "_Test Cost Center - _TC",
					}
				],
				"taxes": [
					{
						"charge_type": "On Net Total",
						"account_head": "_Test Account VAT - _TC",
						"cost_center": "_Test Cost Center - _TC",
						"description": "VAT",
						"rate": 16,
					},
				],
			}
		)
		doc.save()

		tax = doc.taxes[0]
		detail = doc.item_wise_tax_details[0]
		self.assertEqual(detail.amount, tax.base_tax_amount_after_discount_amount)
