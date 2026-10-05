# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.report.bank_reconciliation_statement.bank_reconciliation_statement import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite, if_lending_app_installed


class TestBankReconciliationStatement(ERPNextTestSuite):
	def setUp(self):
		self.bank = create_account(
			account_name="_Test BRS Bank",
			parent_account="Bank Accounts - _TC",
			account_type="Bank",
			company="_Test Company",
		)

	def test_vouchers_cleared_before_posting_date_are_signed(self):
		opening = make_journal_entry(self.bank, "Cash - _TC", 10000, posting_date="2025-09-01", submit=True)
		self.clear(opening, "2025-09-01")
		self.clear(self.make_payment("Pay", 1000), "2025-09-05")
		self.clear(self.make_payment("Receive", 500), "2025-09-05")
		self.clear(self.make_paid_purchase_invoice(rate=400), "2025-09-05")

		rows = self.get_summary_rows("2025-09-08")

		self.assertEqual(rows["Cheques and Deposits incorrectly cleared"].credit, 900)
		self.assertEqual(rows["Calculated Bank Statement balance"].debit, 9100)

	def test_foreign_currency_invoices_listed_in_bank_currency(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		opening = make_journal_entry(self.bank, "Cash - _TC", 100000, posting_date="2025-09-01", submit=True)
		self.clear(opening, "2025-09-01")
		self.make_paid_purchase_invoice(
			rate=100, supplier="_Test Supplier USD", currency="USD", conversion_rate=80
		)
		pos_invoice = create_sales_invoice(
			posting_date="2025-09-10",
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=80,
			rate=50,
			do_not_save=True,
		)
		pos_invoice.is_pos = 1
		pos_invoice.set_posting_time = 1
		pos_invoice.append("payments", {"mode_of_payment": self.make_mode_of_payment(), "amount": 50})
		pos_invoice.insert()
		pos_invoice.submit()

		rows = self.get_summary_rows("2025-09-10", include_pos_transactions=1)

		self.assertEqual(rows["Bank Statement balance as per General Ledger"].debit, 96000)
		self.assertEqual(rows["Outstanding Cheques and Deposits to clear"].debit, 4000)
		self.assertEqual(rows["Outstanding Cheques and Deposits to clear"].credit, 8000)
		self.assertEqual(rows["Calculated Bank Statement balance"].debit, 100000)

	def get_summary_rows(self, report_date, **filters):
		filters = frappe._dict(company="_Test Company", account=self.bank, report_date=report_date, **filters)
		return {
			row["payment_entry"]: frappe._dict(row) for row in execute(filters)[1] if row.get("payment_entry")
		}

	def make_payment(self, payment_type, amount):
		is_pay = payment_type == "Pay"
		payment = create_payment_entry(
			payment_type=payment_type,
			party_type="Supplier" if is_pay else "Customer",
			party="_Test Supplier" if is_pay else "_Test Customer",
			paid_from=self.bank if is_pay else "Debtors - _TC",
			paid_to="Creditors - _TC" if is_pay else self.bank,
			paid_amount=amount,
		)
		payment.posting_date = "2025-09-10"
		payment.submit()
		return payment

	def make_paid_purchase_invoice(self, **args):
		invoice = make_purchase_invoice(
			posting_date="2025-09-10", qty=1, is_paid=1, cash_bank_account=self.bank, do_not_save=True, **args
		)
		invoice.set_posting_time = 1
		invoice.insert()
		invoice.paid_amount = invoice.grand_total
		invoice.submit()
		return invoice

	def make_mode_of_payment(self):
		mode_of_payment = frappe.get_doc(
			{
				"doctype": "Mode of Payment",
				"mode_of_payment": "_Test BRS Bank Transfer",
				"type": "Bank",
				"accounts": [{"company": "_Test Company", "default_account": self.bank}],
			}
		)
		return mode_of_payment.insert(ignore_if_duplicate=True).name

	def clear(self, voucher, clearance_date):
		frappe.db.set_value(voucher.doctype, voucher.name, "clearance_date", clearance_date)

	@if_lending_app_installed
	def test_loan_entries_in_bank_reco_statement(self):
		from lending.loan_management.doctype.loan.test_loan import create_loan_accounts

		from erpnext.accounts.doctype.bank_transaction.test_bank_transaction import (
			create_loan_and_repayment,
		)

		create_loan_accounts()

		repayment_entry = create_loan_and_repayment()

		filters = frappe._dict(
			{
				"company": "Test Company",
				"account": "Payment Account - _TC",
				"report_date": "2018-10-30",
			}
		)
		result = execute(filters)

		self.assertEqual(result[1][0].payment_entry, repayment_entry.name)
