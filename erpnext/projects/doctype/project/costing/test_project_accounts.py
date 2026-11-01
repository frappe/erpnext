# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt, nowdate

from erpnext.accounts.doctype.budget.budget import get_ordered_amount, get_requested_amount
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.utils import get_fiscal_year
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.projects.doctype.project.costing.accounts import (
	account_status,
	budget_control,
	budget_summary,
	get_ledger_entries,
	get_project_accounts,
)
from erpnext.projects.doctype.project.costing.test_project_costing import invoice_for_project
from erpnext.projects.doctype.project.test_project import make_project
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite

EXPENSE_ACCOUNT = "_Test Account Cost for Goods Sold - _TC"
UNBUDGETED_ACCOUNT = "Administrative Expenses - _TC"
ACCOUNTS_VIEWER = "accounts-viewer@example.com"
PROJECTS_VIEWER = "projects-viewer@example.com"
RESTRICTED_VIEWER = "accounts-restricted@example.com"


class TestProjectAccounts(ERPNextTestSuite):
	def test_accounts_join_ledger_commitments_and_budget(self) -> None:
		"""Each account shows what the ledger booked, what open orders commit, and its Budget for the
		fiscal year; income counts credit less debit and carries no budget status."""
		project = self.project_with_budget(budget_amount=10000)
		self.book(project, invoiced=6000, ordered=[3000, 2000])
		make_purchase_invoice(
			item_code=make_item(properties={"is_stock_item": 0}).name,
			qty=1,
			rate=1500,
			project=project,
			expense_account=UNBUDGETED_ACCOUNT,
		)

		accounts = get_project_accounts(project)
		expense = row_for(accounts, EXPENSE_ACCOUNT)
		self.assertEqual((expense["actual"], expense["committed"]), (6000, 5000))
		self.assertEqual(expense["committed"], budget_committed(project, EXPENSE_ACCOUNT))
		self.assertEqual(expense["entries"], 1)
		self.assertEqual(expense["budget"]["amount"], 10000)
		self.assertEqual(expense["budget"]["control"], {"stage": "Purchase Order", "action": "Warn"})
		self.assertEqual(expense["status"], "over_committed")

		income = next(row for row in accounts["rows"] if row["root_type"] == "Income")
		self.assertEqual(income["actual"], 2000)
		self.assertIsNone(income["status"])
		self.assertEqual(row_for(accounts, UNBUDGETED_ACCOUNT)["status"], "none")
		# spend against budget leaves out the account without one
		self.assertEqual(accounts["monthly"][-1]["actual"], 6000)
		self.assertGreater(accounts["monthly"][-1]["budget"], 0)

	def test_account_status_follows_budget_control(self) -> None:
		orders_stop = {"amount": 1000, "stops": ["Purchase Order"]}
		self.assertEqual(account_status(status_row(None, actual=500)), "none")
		self.assertEqual(account_status(status_row(orders_stop, actual=1100)), "over")
		self.assertEqual(
			account_status(status_row(orders_stop, actual=600, committed=500, ordered=500)), "blocked"
		)
		# a purchase order's check counts orders only: requests past the budget leave orders open
		requested = status_row(orders_stop, actual=100, committed=1100, ordered=100)
		self.assertEqual(account_status(requested), "over_committed")
		both_stop = {**orders_stop, "stops": ["Purchase Order", "Material Request"]}
		self.assertEqual(account_status({**requested, "budget": both_stop}), "requests_blocked")
		self.assertEqual(account_status(status_row(orders_stop, actual=600, committed=300)), "near")
		self.assertEqual(account_status(status_row(orders_stop, actual=600, committed=100)), "ok")
		requests_stop = {**orders_stop, "stops": ["Material Request"]}
		self.assertEqual(
			account_status(status_row(requests_stop, actual=600, committed=500)), "requests_blocked"
		)
		expense_stop = {**orders_stop, "stops": ["Expense"]}
		self.assertEqual(
			account_status(status_row(expense_stop, actual=600, committed=500)), "over_committed"
		)

	def test_budget_control_names_the_strongest_rule(self) -> None:
		"""A stop wins over a warning wherever each applies, so a request stop with an order warning
		names the stop, and an order stop with a request warning names the order stop."""
		requests_stop = budget_doc(mr="Stop", po="Warn")
		self.assertEqual(budget_control(requests_stop), {"stage": "Material Request", "action": "Stop"})
		self.assertEqual(budget_summary(requests_stop)["stops"], ["Material Request"])
		orders_stop = budget_doc(mr="Warn", po="Stop")
		self.assertEqual(budget_control(orders_stop), {"stage": "Purchase Order", "action": "Stop"})
		self.assertEqual(budget_summary(orders_stop)["stops"], ["Purchase Order"])
		self.assertIsNone(budget_control(budget_doc(mr="Ignore", po="Ignore", expense="Ignore")))

	def test_ledger_entries_filter_by_account_and_root_type(self) -> None:
		project = self.project_with_budget(budget_amount=10000)
		self.book(project, invoiced=6000)

		expense = get_ledger_entries(project, account=EXPENSE_ACCOUNT)
		self.assertEqual([(row.account, row.debit) for row in expense], [(EXPENSE_ACCOUNT, 6000)])
		income = get_ledger_entries(project, root_type="Income")
		self.assertTrue(income)
		self.assertTrue(all(row.credit for row in income))
		# the creditor and debtor sides of the same invoices are left out
		accounts = {row.account for row in get_ledger_entries(project)}
		self.assertEqual(accounts, {EXPENSE_ACCOUNT, *(row.account for row in income)})

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

	def test_accounts_keep_to_what_the_user_may_read(self) -> None:
		"""A user limited to one account by User Permission sees only that account, in the rows, the
		monthly series and the ledger list alike."""
		project = self.project_with_budget(budget_amount=10000)
		self.book(project, invoiced=6000)
		make_purchase_invoice(
			item_code=make_item(properties={"is_stock_item": 0}).name,
			qty=1,
			rate=777,
			project=project,
			expense_account=UNBUDGETED_ACCOUNT,
		)
		viewer = make_user(RESTRICTED_VIEWER, "Accounts User", "Projects User")
		frappe.get_doc(
			{"doctype": "User Permission", "user": viewer, "allow": "Account", "for_value": EXPENSE_ACCOUNT}
		).insert()

		try:
			frappe.set_user(viewer)
			accounts = get_project_accounts(project)
			ledger = get_ledger_entries(project, root_type="Expense")
		finally:
			frappe.set_user("Administrator")

		self.assertEqual([row["account"] for row in accounts["rows"]], [EXPENSE_ACCOUNT])
		self.assertEqual(accounts["monthly"][-1]["actual"], 6000)
		self.assertEqual({row.account for row in ledger}, {EXPENSE_ACCOUNT})

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


def budget_committed(project: str, account: str) -> float:
	"""What ERPNext's Budget counts as committed on the account, one account at a time."""
	fiscal_year = get_fiscal_year(nowdate(), company="_Test Company")[0]
	params = frappe._dict(
		expense_account=account,
		budget_against_field="project",
		project=project,
		from_fiscal_year=fiscal_year,
		to_fiscal_year=fiscal_year,
	)
	return flt(get_ordered_amount(params)) + flt(get_requested_amount(params))


def row_for(accounts: dict, account: str) -> dict:
	return next(row for row in accounts["rows"] if row["account"] == account)


def budget_doc(mr: str, po: str, expense: str = "Warn") -> dict:
	"""A Budget checking material requests, purchase orders and expenses, with these actions."""
	return {
		"name": "BUDGET-TEST",
		"revision_of": None,
		"by_month": {},
		"applicable_on_material_request": 1,
		"action_if_annual_budget_exceeded_on_mr": mr,
		"applicable_on_purchase_order": 1,
		"action_if_annual_budget_exceeded_on_po": po,
		"applicable_on_booking_actual_expenses": 1,
		"action_if_annual_budget_exceeded": expense,
	}


def status_row(budget: dict | None, actual: float, committed: float = 0, ordered: float = 0) -> dict:
	return {"budget": budget, "actual": actual, "committed": committed, "ordered": ordered}


def make_user(email: str, *roles: str) -> str:
	if not frappe.db.exists("User", email):
		user = frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0]}).insert()
		user.add_roles(*roles)
	return email
