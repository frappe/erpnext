# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.stock.doctype.purchase_receipt.mapper import (
	make_purchase_invoice as make_purchase_invoice_from_receipt,
)
from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_return
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.tests.utils import ERPNextTestSuite

DEDUCT_WITH_VALUATION_MESSAGE = "cannot be .*Deduct.* when .*Consider Tax or Charge for.* is .*Valuation"


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
		self.assertRaisesRegex(frappe.ValidationError, DEDUCT_WITH_VALUATION_MESSAGE, template.insert)

		template.taxes[0].category = "Valuation and Total"
		template.insert()

	def test_deduct_with_valuation_category_in_purchase_documents(self):
		purchase_invoice = make_purchase_invoice(update_stock=1, do_not_save=True)
		purchase_invoice.append("taxes", get_deduct_tax_row("Valuation"))
		self.assertRaisesRegex(frappe.ValidationError, DEDUCT_WITH_VALUATION_MESSAGE, purchase_invoice.insert)

		purchase_receipt = make_purchase_receipt(do_not_save=True)
		purchase_receipt.append("taxes", get_deduct_tax_row("Valuation"))
		self.assertRaisesRegex(frappe.ValidationError, DEDUCT_WITH_VALUATION_MESSAGE, purchase_receipt.insert)

		purchase_invoice = make_purchase_invoice(item_code="_Test Non Stock Item", do_not_save=True)
		purchase_invoice.append("taxes", get_deduct_tax_row("Valuation"))
		purchase_invoice.insert()
		self.assertEqual(purchase_invoice.taxes[0].category, "Total")

	def test_deduct_with_valuation_category_in_existing_purchase_receipt(self):
		purchase_receipt = make_purchase_receipt(do_not_save=True)
		purchase_receipt.append("taxes", get_deduct_tax_row("Valuation"))
		with patch("erpnext.controllers.buying_controller.validate_deduct_with_valuation_category"):
			purchase_receipt.insert()
			purchase_receipt.submit()
		purchase_receipt.cancel()

		amended_receipt = frappe.copy_doc(purchase_receipt)
		amended_receipt.amended_from = purchase_receipt.name
		amended_receipt.append("taxes", get_deduct_tax_row("Valuation", "_Test Account Customs Duty - _TC"))
		self.assertRaisesRegex(frappe.ValidationError, DEDUCT_WITH_VALUATION_MESSAGE, amended_receipt.submit)

		amended_receipt.taxes.pop()
		amended_receipt.submit()

		purchase_return = make_purchase_return(amended_receipt.name)
		purchase_return.append("taxes", get_deduct_tax_row("Valuation", "_Test Account Customs Duty - _TC"))
		self.assertRaisesRegex(frappe.ValidationError, DEDUCT_WITH_VALUATION_MESSAGE, purchase_return.insert)

		purchase_return.taxes.pop()
		purchase_return.submit()

		debit_note = make_purchase_invoice(update_stock=1, is_return=1, qty=-1, do_not_save=True)
		debit_note.append("taxes", get_deduct_tax_row("Valuation"))
		self.assertRaisesRegex(frappe.ValidationError, DEDUCT_WITH_VALUATION_MESSAGE, debit_note.insert)

		purchase_invoice = make_purchase_invoice_from_receipt(amended_receipt.name)
		purchase_invoice.insert()
		self.assertEqual(purchase_invoice.taxes[0].add_deduct_tax, "Deduct")

		purchase_invoice.append("taxes", get_deduct_tax_row("Valuation", "_Test Account Customs Duty - _TC"))
		self.assertRaisesRegex(frappe.ValidationError, DEDUCT_WITH_VALUATION_MESSAGE, purchase_invoice.save)


def get_deduct_tax_row(category, account_head="_Test Account Shipping Charges - _TC"):
	return {
		"charge_type": "Actual",
		"account_head": account_head,
		"cost_center": "_Test Cost Center - _TC",
		"description": "Discount on freight",
		"tax_amount": 50,
		"category": category,
		"add_deduct_tax": "Deduct",
	}
