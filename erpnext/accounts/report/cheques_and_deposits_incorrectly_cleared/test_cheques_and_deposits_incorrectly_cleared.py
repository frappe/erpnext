# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate

from erpnext.accounts.report.cheques_and_deposits_incorrectly_cleared.cheques_and_deposits_incorrectly_cleared import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestChequesAndDepositsIncorrectlyCleared(ERPNextTestSuite):
	def test_report_executes_with_case_amount(self):
		# Exercises the Payment Entry branch whose amount column uses a db-aware CASE expression
		# (previously a MySQL-only IF()). IF() does not compile on postgres, so running the report
		# query guards the portability fix on both databases.
		company = frappe.db.get_value("Company", {}, "name")
		account = frappe.db.get_value(
			"Account", {"account_type": "Bank", "company": company, "is_group": 0}, "name"
		)
		columns, data = execute(frappe._dict({"account": account, "report_date": nowdate()}))
		self.assertTrue(columns)
		self.assertIsInstance(data, list)
