# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.report.bank_reconciliation_statement.bank_reconciliation_statement import (
	execute,
)
from erpnext.tests.utils import if_lending_app_installed
from unittest.mock import patch



class TestBankReconciliationStatement(FrappeTestCase):
	def setUp(self):
		for dt in [
			"Journal Entry",
			"Journal Entry Account",
			"Payment Entry",
		]:
			frappe.db.delete(dt)
		clear_loan_transactions()

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

	def test_execute_full_paths_TC_ACC_448(self):
		# No filters
		cols, data = execute(None)
		self.assertIsInstance(cols, list)
		self.assertEqual(data, [])

		# Filters with no account
		cols, data = execute({})
		self.assertIsInstance(cols, list)
		self.assertEqual(data, [])

		# Full path with account and report_date
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"account": "Bank Accounts - _TC",
				"report_date": "2024-01-01",
			}
		)

		fake_entries = [
			frappe._dict({"debit": 100.0, "credit": 0.0}),
			frappe._dict({"debit": 0.0, "credit": 50.0}),
		]

		with patch("frappe.get_cached_value", return_value="INR"), \
			patch("erpnext.accounts.report.bank_reconciliation_statement.bank_reconciliation_statement.get_entries", return_value=fake_entries), \
			patch("erpnext.accounts.utils.get_balance_on", return_value=500.0), \
			patch("erpnext.accounts.report.bank_reconciliation_statement.bank_reconciliation_statement.get_amounts_not_reflected_in_system", return_value=25.0):

			cols, data = execute(filters)

		# Ensure summary rows exist
		labels = [d.get("payment_entry") for d in data if isinstance(d, dict)]
		assert any("Bank Statement balance as per General Ledger" in str(l) for l in labels)
		assert any("Calculated Bank Statement balance" in str(l) for l in labels)
		# Ensure debit/credit from fake entries are included
		assert any(r.get("debit") == 100.0 for r in data)
		assert any(r.get("credit") == 50.0 for r in data)


@if_lending_app_installed
def clear_loan_transactions():
	for dt in [
		"Loan Disbursement",
		"Loan Repayment",
	]:
		frappe.db.delete(dt)
