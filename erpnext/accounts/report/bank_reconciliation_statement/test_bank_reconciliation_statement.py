# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.accounts.doctype.bank_clearance.test_bank_clearance import make_bank_account
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.report.bank_reconciliation_statement.bank_reconciliation_statement import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite, if_lending_app_installed


class TestBankReconciliationStatement(ERPNextTestSuite):
	def test_entries_cleared_after_report_date(self):
		make_bank_account()
		payment_entry = create_payment_entry(
			paid_from="_Test Bank Clearance - _TC",
			paid_to="Creditors - _TC",
			save=True,
			submit=True,
		)
		payment_entry.db_set("clearance_date", add_days(today(), 1))

		filters = frappe._dict(
			{
				"company": "_Test Company",
				"account": "_Test Bank Clearance - _TC",
				"report_date": today(),
				"include_entries_cleared_after_report_date": 1,
			}
		)
		self.assertIn(payment_entry.name, [row.get("payment_entry") for row in execute(filters)[1]])

		filters.include_entries_cleared_after_report_date = 0
		self.assertNotIn(payment_entry.name, [row.get("payment_entry") for row in execute(filters)[1]])

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
