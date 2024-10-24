# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from erpnext.accounts.report.bank_reconciliation_statement.bank_reconciliation_statement import (
	execute,
)
from erpnext.tests.utils import if_lending_app_installed


class TestBankReconciliationStatement(IntegrationTestCase):
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
