# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.utils import get_fiscal_year
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.projects.doctype.project.costing.accounts import (
	account_status,
	get_ledger_entries,
	get_project_accounts,
)
from erpnext.projects.doctype.project.costing.test_project_costing import invoice_for_project
from erpnext.projects.doctype.project.test_project import make_project
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite

EXPENSE_ACCOUNT = "_Test Account Cost for Goods Sold - _TC"
ACCOUNTS_VIEWER = "accounts-viewer@example.com"
PROJECTS_VIEWER = "projects-viewer@example.com"


class TestProjectAccounts(ERPNextTestSuite):
	def test_accounts_join_ledger_commitments_and_budget(self) -> None:
		"""Each account shows what the ledger booked, what open orders commit, and its Budget for the
		fiscal year; income counts credit less debit and carries no budget status."""
		project = self.project_with_budget(budget_amount=10000)
		self.book(project, invoiced=6000, ordered=[3000, 2000])

		accounts = get_project_accounts(project)
		expense = row_for(accounts, EXPENSE_ACCOUNT)
		self.assertEqual((expense["actual"], expense["committed"]), (6000, 5000))
		self.assertEqual(expense["entries"], 1)
		self.assertEqual(expense["budget"]["amount"], 10000)
		self.assertEqual(expense["budget"]["control"], {"stage": "Purchase Order", "action": "Warn"})
		self.assertEqual(expense["status"], "over_committed")

		income = next(row for row in accounts["rows"] if row["root_type"] == "Income")
		self.assertEqual(income["actual"], 2000)
		self.assertIsNone(income["status"])
		self.assertEqual(accounts["monthly"][-1]["actual"], 6000)
		self.assertGreater(accounts["monthly"][-1]["budget"], 0)

	def test_account_status_follows_budget_control(self) -> None:
		budget = {"amount": 1000, "control": {"stage": "Purchase Order", "action": "Stop"}}
		self.assertEqual(account_status(status_row(None, actual=500)), "none")
		self.assertEqual(account_status(status_row(budget, actual=1100)), "over")
		self.assertEqual(account_status(status_row(budget, actual=600, committed=500)), "blocked")
		self.assertEqual(account_status(status_row(budget, actual=600, committed=300)), "near")
		self.assertEqual(account_status(status_row(budget, actual=600, committed=100)), "ok")
		on_expense = {**budget, "control": {"stage": "Expense", "action": "Stop"}}
		self.assertEqual(account_status(status_row(on_expense, actual=600, committed=500)), "over_committed")

	def test_ledger_entries_filter_by_account_and_root_type(self) -> None:
		project = self.project_with_budget(budget_amount=10000)
		self.book(project, invoiced=6000)

		expense = get_ledger_entries(project, account=EXPENSE_ACCOUNT)
		self.assertEqual([(row.account, row.debit) for row in expense], [(EXPENSE_ACCOUNT, 6000)])
		income = get_ledger_entries(project, root_type="Income")
		self.assertTrue(income)
		self.assertTrue(all(row.credit for row in income))

	def test_budgets_and_ledger_follow_the_viewer_roles(self) -> None:
		"""An Accounts User sees the ledger without Budget records; a Projects User sees neither."""
		project = self.project_with_budget(budget_amount=10000)
		self.book(project, invoiced=6000)

		accounts_viewer = make_user(ACCOUNTS_VIEWER, "Accounts User", "Projects User")
		projects_viewer = make_user(PROJECTS_VIEWER, "Projects User")
		try:
			frappe.set_user(accounts_viewer)
			accounts = get_project_accounts(project)
			frappe.set_user(projects_viewer)
			self.assertRaises(frappe.PermissionError, get_project_accounts, project)
		finally:
			frappe.set_user("Administrator")

		self.assertFalse(accounts["access"]["budgets"])
		self.assertEqual(row_for(accounts, EXPENSE_ACCOUNT)["actual"], 6000)
		self.assertIsNone(row_for(accounts, EXPENSE_ACCOUNT)["budget"])

	def project_with_budget(self, budget_amount: float) -> str:
		"""A customer project with a Budget on the expense account: warn from purchase order."""
		project = make_project({"project_name": f"_Test Accounts {frappe.generate_hash(length=6)}"}).name
		fiscal_year = get_fiscal_year(nowdate(), company="_Test Company")[0]
		budget = frappe.get_doc(
			{
				"doctype": "Budget",
				"budget_against": "Project",
				"project": project,
				"company": "_Test Company",
				"account": EXPENSE_ACCOUNT,
				"budget_amount": budget_amount,
				"from_fiscal_year": fiscal_year,
				"to_fiscal_year": fiscal_year,
				"distribution_frequency": "Monthly",
				"distribute_equally": 1,
				"applicable_on_booking_actual_expenses": 1,
				"action_if_annual_budget_exceeded": "Warn",
				"action_if_accumulated_monthly_budget_exceeded": "Ignore",
				"applicable_on_purchase_order": 1,
				"action_if_annual_budget_exceeded_on_po": "Warn",
				"action_if_accumulated_monthly_budget_exceeded_on_po": "Ignore",
			}
		)
		budget.insert()
		budget.submit()
		return project

	def book(self, project: str, invoiced: float, ordered: list[float] | None = None) -> None:
		"""A purchase invoice and open purchase orders on the expense account, and a sales invoice."""
		service = make_item(properties={"is_stock_item": 0}).name
		make_purchase_invoice(item_code=service, qty=1, rate=invoiced, project=project)
		for rate in ordered or []:
			order = create_purchase_order(item_code=service, qty=1, rate=rate, do_not_save=True)
			order.set_missing_values()
			order.items[0].update({"project": project, "expense_account": EXPENSE_ACCOUNT})
			order.insert()
			order.submit()
		invoice_for_project(project, qty=2)


def row_for(accounts: dict, account: str) -> dict:
	return next(row for row in accounts["rows"] if row["account"] == account)


def status_row(budget: dict | None, actual: float, committed: float = 0) -> dict:
	return {"budget": budget, "actual": actual, "committed": committed}


def make_user(email: str, *roles: str) -> str:
	if not frappe.db.exists("User", email):
		user = frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0]}).insert()
		user.add_roles(*roles)
	return email
