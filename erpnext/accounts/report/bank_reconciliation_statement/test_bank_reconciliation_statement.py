# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
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

	def test_finance_books_match_the_ledger_balance(self):
		from erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool import (
			get_account_balance,
		)
		from erpnext.accounts.report.cheques_and_deposits_incorrectly_cleared.cheques_and_deposits_incorrectly_cleared import (
			build_data,
		)

		frappe.db.set_value("Company", "_Test Company", "default_finance_book", "")
		books = [
			frappe.get_doc(doctype="Finance Book", finance_book_name=name).insert().name
			for name in ("_Test BRS Default Book", "_Test BRS Alternative Book")
		]
		opening = make_journal_entry(self.bank, "Cash - _TC", 1000, posting_date="2025-09-01", submit=True)
		self.clear(opening, "2025-09-01")
		incorrectly_cleared = []
		for book in (None, "", *books):
			for posting_date, amount, clearance_date in (
				("2025-09-05", -10, None),
				("2025-09-10", -5, "2025-09-05"),
			):
				journal = make_journal_entry(
					self.bank, "Cash - _TC", amount, posting_date=posting_date, save=False
				)
				journal.finance_book = book
				journal.submit()
				frappe.db.set_value("Journal Entry", journal.name, "finance_book", book)
				if clearance_date:
					self.clear(journal, clearance_date)
					if not book:
						incorrectly_cleared.append(journal.name)

		bank = frappe.get_doc(doctype="Bank", bank_name="_Test BRS Finance Books").insert()
		bank_account = frappe.get_doc(
			doctype="Bank Account",
			account_name="_Test BRS Finance Books",
			bank=bank.name,
			is_company_account=1,
			company="_Test Company",
			account=self.bank,
		).insert()
		for default_book in ("", books[0]):
			frappe.db.set_value("Company", "_Test Company", "default_finance_book", default_book)
			with self.subTest(default_book=default_book):
				rows = self.get_summary_rows("2025-09-08")
				self.assertEqual(rows["Bank Statement balance as per General Ledger"].debit, 980)
				self.assertEqual(rows["Outstanding Cheques and Deposits to clear"].credit, 20)
				self.assertEqual(rows["Cheques and Deposits incorrectly cleared"].credit, 10)
				self.assertEqual(rows["Calculated Bank Statement balance"].debit, 990)
				self.assertEqual(get_account_balance(bank_account.name, "2025-09-08", "_Test Company"), 990)
				filters = frappe._dict(company="_Test Company", account=self.bank, report_date="2025-09-08")
				self.assertCountEqual([row.payment_entry for row in build_data(filters)], incorrectly_cleared)

	def get_summary_rows(self, report_date, **filters):
		filters = frappe._dict(company="_Test Company", account=self.bank, report_date=report_date, **filters)
		return {
			row["payment_entry"]: frappe._dict(row) for row in execute(filters)[1] if row.get("payment_entry")
		}

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
