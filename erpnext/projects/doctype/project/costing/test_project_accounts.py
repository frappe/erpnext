# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.utils import nowdate

from erpnext.accounts.doctype.budget.budget import BudgetError
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.utils import get_fiscal_year
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.projects.doctype.project.costing.accounts import get_ledger_entries, get_project_accounts
from erpnext.projects.doctype.project.costing.budgets import account_status, budget_control
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
		self.assertEqual(expense["entries"], 1)
		self.assertEqual(expense["budget"]["amount"], 10000)
		self.assertEqual(expense["budget"]["control"], {"stage": "Purchase Order", "action": "Warn"})
		# orders and actual spend are each checked on their own, and each is within the budget
		self.assertEqual(expense["status"], "ok")

		income = next(row for row in accounts["rows"] if row["root_type"] == "Income")
		self.assertEqual(income["actual"], 2000)
		self.assertIsNone(income["status"])
		self.assertEqual(row_for(accounts, UNBUDGETED_ACCOUNT)["status"], "none")
		# spend against budget leaves out the account without one
		self.assertEqual(accounts["monthly"][-1]["actual"], 6000)
		self.assertGreater(accounts["monthly"][-1]["budget"], 0)

	def test_budget_rules_follow_erpnext_checks(self) -> None:
		"""Each stage the Budget checks compares its own amount with the budget, and with the monthly
		distribution to date; a Stop on any exceeded check blocks the account. The account is named by
		its strongest rule, monthly rules included."""
		self.assertEqual(account_status(None, spend(actual=500)), "none")
		orders_stop = budget_doc(po="Stop")
		self.assertEqual(account_status(orders_stop, spend(ordered=1100)), "blocked")
		self.assertEqual(account_status(budget_doc(po="Warn"), spend(ordered=1100)), "over")
		# up to the budget itself is within it
		self.assertEqual(account_status(orders_stop, spend(ordered=1000)), "ok")
		# requests past the budget trip the request check, not the order check
		self.assertEqual(account_status(orders_stop, spend(ordered=100, requested=1100)), "over")
		# without the cumulative check, stages within the budget each pass however they add up
		mixed = spend(actual=600, ordered=600, requested=600)
		self.assertEqual(account_status(orders_stop, mixed), "ok")
		self.assertEqual(account_status(budget_doc(po="Stop", cumulative="Stop"), mixed), "blocked")

		# within the year, but past the months distributed so far
		by_month = {nowdate()[:7]: 500, "9999-12": 500}
		self.assertEqual(account_status(budget_doc(by_month=by_month), spend(ordered=600)), "over_to_date")
		monthly_stop = budget_doc(by_month=by_month, po_monthly="Stop")
		self.assertEqual(account_status(monthly_stop, spend(ordered=600)), "blocked")

		self.assertEqual(budget_control(monthly_stop), {"stage": "Purchase Order", "action": "Stop"})
		requests_stop = budget_doc(mr="Stop", po="Warn")
		self.assertEqual(budget_control(requests_stop), {"stage": "Material Request", "action": "Stop"})
		self.assertIsNone(budget_control(budget_doc(mr="Ignore", po="Ignore", expense="Ignore")))

	def test_status_matches_what_erpnext_enforces(self) -> None:
		"""ERPNext's budget controller warns on orders past a budget that warns, and refuses the next
		order once the budget stops: the account reads over, then blocked."""
		project = self.project_with_budget(budget_amount=4000)
		self.book(project, invoiced=1000, ordered=[3000, 2000])
		self.assertEqual(row_for(get_project_accounts(project), EXPENSE_ACCOUNT)["status"], "over")

		frappe.db.set_value("Budget", {"project": project}, "action_if_annual_budget_exceeded_on_po", "Stop")
		self.assertEqual(row_for(get_project_accounts(project), EXPENSE_ACCOUNT)["status"], "blocked")
		with self.assertRaises(BudgetError):
			order_for_project(project, rate=100)

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

		accounts_viewer = create_user(ACCOUNTS_VIEWER, "Accounts User", "Projects User").name
		projects_viewer = create_user(PROJECTS_VIEWER, "Projects User").name
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
		"""A user limited by User Permission to one account, and to orders from another supplier, sees
		only that account in the rows, the monthly series and the ledger, and none of the orders."""
		project = self.project_with_budget(budget_amount=10000)
		self.book(project, invoiced=6000, ordered=[3000])
		make_purchase_invoice(
			item_code=make_item(properties={"is_stock_item": 0}).name,
			qty=1,
			rate=777,
			project=project,
			expense_account=UNBUDGETED_ACCOUNT,
		)
		viewer = create_user(RESTRICTED_VIEWER, "Accounts User", "Projects User").name
		# the test orders are from "_Test Supplier"
		for allow, value in (("Account", EXPENSE_ACCOUNT), ("Supplier", "_Test Supplier 1")):
			frappe.get_doc(
				{"doctype": "User Permission", "user": viewer, "allow": allow, "for_value": value}
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
		self.assertEqual(row_for(accounts, EXPENSE_ACCOUNT)["committed"], 0)
		self.assertEqual(row_for(get_project_accounts(project), EXPENSE_ACCOUNT)["committed"], 3000)

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
				# all of it in the first month, so the monthly check is the annual one on any date
				"distribution_frequency": "Yearly",
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
			order_for_project(project, rate, service)
		invoice_for_project(project, qty=2)


def order_for_project(project: str, rate: float, item_code: str | None = None) -> None:
	"""A submitted purchase order for the project on the expense account."""
	item_code = item_code or make_item(properties={"is_stock_item": 0}).name
	order = create_purchase_order(item_code=item_code, qty=1, rate=rate, do_not_save=True)
	order.set_missing_values()
	order.items[0].update({"project": project, "expense_account": EXPENSE_ACCOUNT})
	order.insert()
	order.submit()


def row_for(accounts: dict, account: str) -> dict:
	return next(row for row in accounts["rows"] if row["account"] == account)


def budget_doc(
	po: str = "Warn",
	mr: str = "Warn",
	expense: str = "Warn",
	cumulative: str | None = None,
	po_monthly: str = "Ignore",
	by_month: dict | None = None,
) -> dict:
	"""A Budget of 1,000 checking requests, orders and expenses with these annual actions, the
	monthly rule on orders, and a cumulative check when its action is given. Without `by_month`, all
	of it falls in the first month."""
	return {
		"budget_amount": 1000,
		"by_month": by_month or {"2000-01": 1000},
		"applicable_on_purchase_order": 1,
		"action_if_annual_budget_exceeded_on_po": po,
		"action_if_accumulated_monthly_budget_exceeded_on_po": po_monthly,
		"applicable_on_material_request": 1,
		"action_if_annual_budget_exceeded_on_mr": mr,
		"action_if_accumulated_monthly_budget_exceeded_on_mr": "Ignore",
		"applicable_on_booking_actual_expenses": 1,
		"action_if_annual_budget_exceeded": expense,
		"action_if_accumulated_monthly_budget_exceeded": "Ignore",
		"applicable_on_cumulative_expense": int(bool(cumulative)),
		"action_if_annual_exceeded_on_cumulative_expense": cumulative,
		"action_if_accumulated_monthly_exceeded_on_cumulative_expense": None,
	}


def spend(actual: float = 0, ordered: float = 0, requested: float = 0) -> dict[str, float]:
	return {"actual": actual, "ordered": ordered, "requested": requested}
