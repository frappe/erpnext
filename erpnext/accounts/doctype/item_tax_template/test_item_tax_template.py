# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice


class TestItemTaxTemplate(unittest.TestCase):
	def setUp(self):
		make_accounts()
		create_item_tax_template()
		make_item()

	def test_sales_transaction_application(self):
		sales_invoice = create_sales_invoice(item_code="_Test Item Tax Item 1", do_not_save=True)
		sales_invoice.items[0].item_tax_template = "_Test Item Tax Template - _TC"
		sales_invoice.save()

		self.assertEqual(sales_invoice.get("taxes")[0].account_head, "VAT - Sales - _TC")
		self.assertEqual(sales_invoice.get("taxes")[1].account_head, "VAT - Standard - _TC")

	def test_purchase_transaction_application(self):
		purchase_invoice = make_purchase_invoice(item_code="_Test Item Tax Item 2", do_not_save=True)
		purchase_invoice.items[0].item_tax_template = "_Test Item Tax Template - _TC"
		purchase_invoice.save()

		self.assertEqual(purchase_invoice.get("taxes")[0].account_head, "VAT - Purchase - _TC")
		self.assertEqual(purchase_invoice.get("taxes")[1].account_head, "VAT - Standard - _TC")


def make_accounts():
	# Create an account for VAT when selling
	create_account(
		account_name="VAT - Sales",
		company="_Test Company",
		account_type="Tax",
		parent_account="Duties and Taxes - _TC",
	)

	create_account(
		account_name="VAT - Purchase",
		company="_Test Company",
		account_type="Tax",
		parent_account="Duties and Taxes - _TC",
	)

	create_account(
		account_name="VAT - Standard",
		company="_Test Company",
		account_type="Tax",
		parent_account="Duties and Taxes - _TC",
	)


def create_item_tax_template():
	if not frappe.db.exists("Item Tax Template", "_Test Item Tax Template - _TC"):
		frappe.get_doc(
			{
				"doctype": "Item Tax Template",
				"company": "_Test Company",
				"title": "_Test Item Tax Template",
				"taxes": [
					{"tax_type": "VAT - Sales - _TC", "tax_rate": 10, "transaction_type": "Sales"},
					{"tax_type": "VAT - Purchase - _TC", "tax_rate": 10, "transaction_type": "Purchase"},
					{"tax_type": "VAT - Standard - _TC", "tax_rate": 10, "transaction_type": "All"},
				],
			}
		).insert()


def make_item():
	# Create a new Item
	if not frappe.db.exists("Item", "_Test Item Tax Item 1"):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "_Test Item Tax Item 1",
				"item_name": "_Test Item Tax Item 1",
				"item_group": "All Item Groups",
				"taxes": [
					{
						"item_tax_template": "_Test Item Tax Template - _TC",
					}
				],
			}
		).insert()

	# Create a second Item with higher VAT rate
	if not frappe.db.exists("Item", "_Test Item Tax Item 2"):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "_Test Item Tax Item 2",
				"item_name": "_Test Item Tax Item 2",
				"item_group": "All Item Groups",
				"taxes": [
					{
						"item_tax_template": "_Test Item Tax Template - _TC",
					}
				],
			}
		).insert()
