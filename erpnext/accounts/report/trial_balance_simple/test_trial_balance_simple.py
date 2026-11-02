from unittest.mock import patch

import frappe
from frappe.desk.query_report import run
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry


class TestTrialBalanceSimple(FrappeTestCase):
	def test_rows_limited_to_permitted_accounts(self):
		make_journal_entry("_Test Account Cost for Goods Sold - _TC", "_Test Bank - _TC", 100, submit=True)
		# run the shipped query even if the site has not been migrated since it changed
		report_path = frappe.get_module_path(
			"accounts", "report", "trial_balance_simple", "trial_balance_simple.json"
		)
		frappe.db.set_value(
			"Report", "Trial Balance (Simple)", "query", frappe.get_file_json(report_path)["query"]
		)

		user = "test_trial_balance_simple@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "TBS", "roles": [{"role": "Accounts User"}]}
			).insert()
		frappe.permissions.add_user_permission("Account", "_Test Bank - _TC", user)

		frappe.set_user(user)
		try:
			# Report.execute_query_report opens and rolls back its own transaction
			with patch.object(frappe.db, "begin"), patch.object(frappe.db, "rollback"):
				result = run("Trial Balance (Simple)", filters={"company": "_Test Company"})["result"]
		finally:
			frappe.set_user("Administrator")

		accounts = {row.get("account") for row in result if isinstance(row, dict) and row.get("account")}
		self.assertEqual(accounts, {"_Test Bank - _TC"})
