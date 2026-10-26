# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.tests.utils import ERPNextTestSuite


class TestPurchaseTaxesandChargesTemplate(ERPNextTestSuite):
	def test_deduct_with_valuation_category_in_template(self):
		template = frappe.get_doc(
			{
				"doctype": "Purchase Taxes and Charges Template",
				"title": "_Test Deduct Valuation Template",
				"company": "_Test Company",
				"taxes": [get_deduct_tax_row("Valuation")],
			}
		)
		self.assertRaises(frappe.ValidationError, template.insert)

		template.taxes[0].category = "Valuation and Total"
		template.insert()

	def test_deduct_with_valuation_category_in_purchase_documents(self):
		purchase_invoice = make_purchase_invoice(update_stock=1, do_not_save=True)
		purchase_invoice.append("taxes", get_deduct_tax_row("Valuation"))
		self.assertRaises(frappe.ValidationError, purchase_invoice.insert)

		purchase_receipt = make_purchase_receipt(do_not_save=True)
		purchase_receipt.append("taxes", get_deduct_tax_row("Valuation"))
		self.assertRaises(frappe.ValidationError, purchase_receipt.insert)

		purchase_invoice = make_purchase_invoice(item_code="_Test Non Stock Item", do_not_save=True)
		purchase_invoice.append("taxes", get_deduct_tax_row("Valuation"))
		purchase_invoice.insert()
		self.assertEqual(purchase_invoice.taxes[0].category, "Total")


def get_deduct_tax_row(category):
	return {
		"charge_type": "Actual",
		"account_head": "_Test Account Shipping Charges - _TC",
		"cost_center": "_Test Cost Center - _TC",
		"description": "Discount on freight",
		"tax_amount": 50,
		"category": category,
		"add_deduct_tax": "Deduct",
	}
