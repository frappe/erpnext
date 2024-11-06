# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate, today

from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order


class TestAdvancePaymentLedgerEntry(AccountsTestMixin, FrappeTestCase):
	"""
	Integration tests for AdvancePaymentLedgerEntry.
	Use this class for testing interactions between multiple components.
	"""

	def setUp(self):
		self.create_company()
		self.create_usd_receivable_account()
		self.create_usd_payable_account()
		self.create_item()
		self.clear_old_entries()

	def tearDown(self):
		frappe.db.rollback()

	def create_sales_order(self, qty=1, rate=100, currency="INR", do_not_submit=False):
		"""
		Helper method
		"""
		so = make_sales_order(
			company=self.company,
			customer=self.customer,
			currency=currency,
			item=self.item,
			qty=qty,
			rate=rate,
			transaction_date=today(),
			do_not_submit=do_not_submit,
		)
		return so

	def create_purchase_order(self, qty=1, rate=100, currency="INR", do_not_submit=False):
		"""
		Helper method
		"""
		po = create_purchase_order(
			company=self.company,
			customer=self.supplier,
			currency=currency,
			item=self.item,
			qty=qty,
			rate=rate,
			transaction_date=today(),
			do_not_submit=do_not_submit,
		)
		return po

	def test_so_advance_paid_and_currency_with_payment(self):
		self.create_customer("_Test USD Customer", "USD")

		so = self.create_sales_order(currency="USD", do_not_submit=True)
		so.conversion_rate = 80
		so.submit()

		pe_exchange_rate = 85
		pe = get_payment_entry(so.doctype, so.name, bank_account=self.cash)
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_from = self.debtors_usd
		pe.paid_from_account_currency = "USD"
		pe.source_exchange_rate = pe_exchange_rate
		pe.paid_amount = so.grand_total
		pe.received_amount = pe_exchange_rate * pe.paid_amount
		pe.references[0].outstanding_amount = 100
		pe.references[0].total_amount = 100
		pe.references[0].allocated_amount = 100
		pe.save().submit()

		so.reload()
		self.assertEqual(so.advance_paid, 100)
		self.assertEqual(so.party_account_currency, "USD")

		# cancel advance payment
		pe.reload()
		pe.cancel()

		so.reload()
		self.assertEqual(so.advance_paid, 0)
		self.assertEqual(so.party_account_currency, "USD")

	def test_so_advance_paid_and_currency_with_journal(self):
		self.create_customer("_Test USD Customer", "USD")

		so = self.create_sales_order(currency="USD", do_not_submit=True)
		so.conversion_rate = 80
		so.submit()

		je_exchange_rate = 85
		je = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"company": self.company,
				"voucher_type": "Journal Entry",
				"posting_date": so.transaction_date,
				"multi_currency": True,
				"accounts": [
					{
						"account": self.debtors_usd,
						"party_type": "Customer",
						"party": so.customer,
						"credit": 8500,
						"credit_in_account_currency": 100,
						"is_advance": "Yes",
						"reference_type": so.doctype,
						"reference_name": so.name,
						"exchange_rate": je_exchange_rate,
					},
					{
						"account": self.cash,
						"debit": 8500,
						"debit_in_account_currency": 8500,
					},
				],
			}
		)
		je.save().submit()
		so.reload()
		self.assertEqual(so.advance_paid, 100)
		self.assertEqual(so.party_account_currency, "USD")

		# cancel advance payment
		je.reload()
		je.cancel()

		so.reload()
		self.assertEqual(so.advance_paid, 0)
		self.assertEqual(so.party_account_currency, "USD")

	def test_po_advance_paid_and_currency_with_payment(self):
		self.create_supplier("_Test USD Supplier", "USD")

		po = self.create_purchase_order(currency="USD", do_not_submit=True)
		po.conversion_rate = 80
		po.submit()

		pe_exchange_rate = 85
		pe = get_payment_entry(po.doctype, po.name, bank_account=self.cash)
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_to = self.creditors_usd
		pe.paid_to_account_currency = "USD"
		pe.target_exchange_rate = pe_exchange_rate
		pe.received_amount = po.grand_total
		pe.paid_amount = pe_exchange_rate * pe.received_amount
		pe.references[0].outstanding_amount = 100
		pe.references[0].total_amount = 100
		pe.references[0].allocated_amount = 100
		pe.save().submit()

		po.reload()
		self.assertEqual(po.advance_paid, 100)
		self.assertEqual(po.party_account_currency, "USD")

		# cancel advance payment
		pe.reload()
		pe.cancel()

		po.reload()
		self.assertEqual(po.advance_paid, 0)
		self.assertEqual(po.party_account_currency, "USD")

	def test_po_advance_paid_and_currency_with_journal(self):
		self.create_supplier("_Test USD Supplier", "USD")

		po = self.create_purchase_order(currency="USD", do_not_submit=True)
		po.conversion_rate = 80
		po.submit()

		je_exchange_rate = 85
		je = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"company": self.company,
				"voucher_type": "Journal Entry",
				"posting_date": po.transaction_date,
				"multi_currency": True,
				"accounts": [
					{
						"account": self.creditors_usd,
						"party_type": "Supplier",
						"party": po.supplier,
						"debit": 8500,
						"debit_in_account_currency": 100,
						"is_advance": "Yes",
						"reference_type": po.doctype,
						"reference_name": po.name,
						"exchange_rate": je_exchange_rate,
					},
					{
						"account": self.cash,
						"credit": 8500,
						"credit_in_account_currency": 8500,
					},
				],
			}
		)
		je.save().submit()
		po.reload()
		self.assertEqual(po.advance_paid, 100)
		self.assertEqual(po.party_account_currency, "USD")

		# cancel advance payment
		je.reload()
		je.cancel()

		po.reload()
		self.assertEqual(po.advance_paid, 0)
		self.assertEqual(po.party_account_currency, "USD")
