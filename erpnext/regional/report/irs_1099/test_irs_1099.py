# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.utils import get_fiscal_year
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.regional.report.irs_1099.irs_1099 import execute

test_dependencies = ["Supplier Group", "Item", "Account"]

US_COMPANY = "_Test Company 1"


class TestIRS1099(FrappeTestCase):
	def test_total_payments_are_net_payments(self):
		supplier = make_1099_supplier()
		pi = make_us_purchase_invoice(supplier, qty=10, rate=100)
		pay(pi, 600)
		pay(pi, 300).cancel()

		debit_note = make_return_doc("Purchase Invoice", pi.name)
		debit_note.items[0].qty = -1
		debit_note.submit()

		refund = get_payment_entry("Purchase Invoice", debit_note.name, bank_account="Cash - _TC1")
		refund.paid_amount = refund.received_amount = 50
		refund.references = []
		refund.reference_no, refund.reference_date = "_Test Refund", nowdate()
		refund.submit()

		self.assertEqual(get_total_payments(supplier), 550)

	def test_payments_made_on_paid_invoices(self):
		supplier = make_1099_supplier()
		pi = make_us_purchase_invoice(supplier, qty=10, rate=100, is_paid=1, cash_bank_account="Cash - _TC1")

		debit_note = make_return_doc("Purchase Invoice", pi.name)
		debit_note.items[0].qty = -2
		debit_note.submit()

		self.assertEqual(get_total_payments(supplier), 800)

	def test_journal_entries_through_bank_or_cash_only(self):
		supplier = make_1099_supplier()
		make_supplier_journal_entry(supplier, 400, "Cash - _TC1")
		make_supplier_journal_entry(supplier, -100, "Cash - _TC1")
		make_supplier_journal_entry(supplier, 300, "Cash - _TC1").cancel()
		make_supplier_journal_entry(supplier, 70, "Cost of Goods Sold - _TC1")

		self.assertEqual(get_total_payments(supplier), 300)

	def test_total_payments_in_company_currency(self):
		supplier = make_1099_supplier(currency="EUR", payable_account=make_eur_payable_account())
		pi = make_us_purchase_invoice(supplier, currency="EUR", conversion_rate=1.1, qty=10, rate=100)
		payment = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank EUR - _TC1")
		payment.source_exchange_rate = payment.target_exchange_rate = 1.1
		payment.reference_no, payment.reference_date = "_Test Payment", nowdate()
		payment.submit()

		self.assertEqual(get_total_payments(supplier), 1100)

	def test_company_permission(self):
		frappe.permissions.add_user_permission("Company", "_Test Company", "test2@example.com")
		frappe.get_doc("User", "test2@example.com").add_roles("Accounts Manager")

		with self.set_user("test2@example.com"):
			self.assertRaises(frappe.PermissionError, get_total_payments, "_Test Supplier")


def make_1099_supplier(currency: str = "USD", payable_account: str | None = None) -> str:
	supplier = frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": "_Test 1099 Supplier " + frappe.generate_hash(length=6),
			"supplier_group": "_Test Supplier Group",
			"default_currency": currency,
			"irs_1099": 1,
		}
	)
	if payable_account:
		supplier.append("accounts", {"company": US_COMPANY, "account": payable_account})
	return supplier.insert().name


def make_eur_payable_account() -> str:
	account = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": "_Test Payable EUR " + frappe.generate_hash(length=6),
			"company": US_COMPANY,
			"parent_account": "Accounts Payable - _TC1",
			"account_type": "Payable",
			"account_currency": "EUR",
		}
	)
	return account.insert().name


def make_us_purchase_invoice(supplier: str, currency: str = "USD", **args):
	return make_purchase_invoice(
		company=US_COMPANY,
		supplier=supplier,
		currency=currency,
		item="_Test Non Stock Item",
		warehouse="Stores - _TC1",
		cost_center="Main - _TC1",
		expense_account="Cost of Goods Sold - _TC1",
		**args,
	)


def make_supplier_journal_entry(supplier: str, amount: float, against_account: str):
	"""Debits the supplier by `amount` (credits it when negative) against `against_account`."""
	journal_entry = frappe.new_doc("Journal Entry")
	journal_entry.update(
		{"company": US_COMPANY, "posting_date": nowdate(), "cheque_no": "_Test", "cheque_date": nowdate()}
	)
	debit, credit = (amount, 0) if amount > 0 else (0, -amount)
	journal_entry.append(
		"accounts",
		{
			"account": "Creditors - _TC1",
			"party_type": "Supplier",
			"party": supplier,
			"debit_in_account_currency": debit,
			"credit_in_account_currency": credit,
			"cost_center": "Main - _TC1",
		},
	)
	journal_entry.append(
		"accounts",
		{
			"account": against_account,
			"debit_in_account_currency": credit,
			"credit_in_account_currency": debit,
			"cost_center": "Main - _TC1",
		},
	)
	return journal_entry.submit()


def pay(pi, amount: float):
	payment = get_payment_entry("Purchase Invoice", pi.name, party_amount=amount, bank_account="Cash - _TC1")
	payment.reference_no, payment.reference_date = "_Test Payment", nowdate()
	return payment.submit()


def get_total_payments(supplier: str) -> float:
	filters = {"company": US_COMPANY, "fiscal_year": get_fiscal_year(nowdate(), company=US_COMPANY)[0]}
	_columns, data = execute(filters)
	return next((row.payments for row in data if row.supplier == supplier), 0)
