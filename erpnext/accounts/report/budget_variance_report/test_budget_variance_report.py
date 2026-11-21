# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from erpnext.accounts.doctype.budget.test_budget import make_budget
from erpnext.accounts.report.budget_variance_report.budget_variance_report import execute
from erpnext.accounts.utils import get_fiscal_year

ACCOUNT = "_Test Account Cost for Goods Sold - _TC"
COST_CENTER = "_Test Cost Center - _TC"
COST_CENTER_2 = "_Test Cost Center 2 - _TC"

test_dependencies = ["Monthly Distribution"]


class TestBudgetVarianceReport(FrappeTestCase):
	def setUp(self):
		self.fiscal_year = get_fiscal_year(nowdate())[0]

	def get_filters(self, **extra):
		return frappe._dict(
			{
				"company": "_Test Company",
				"from_fiscal_year": self.fiscal_year,
				"to_fiscal_year": self.fiscal_year,
				"period": "Yearly",
				"budget_against": "Cost Center",
				**extra,
			}
		)

	def test_chart_covers_only_permitted_cost_centers(self):
		make_large_budget(COST_CENTER)
		make_large_budget(COST_CENTER_2)
		user = make_user_restricted_to_cost_center(COST_CENTER)

		frappe.set_user(user)
		try:
			_columns, data, _message, chart = execute(self.get_filters())
		finally:
			frappe.set_user("Administrator")

		self.assertEqual({row[0] for row in data}, {COST_CENTER})
		self.assertEqual(chart["data"]["datasets"][0]["values"], [data[0][2]])


def make_user_restricted_to_cost_center(cost_center):
	user = "test_budget_variance@example.com"
	if not frappe.db.exists("User", user):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": user,
				"first_name": "Budget Variance",
				"send_welcome_email": 0,
				"roles": [{"role": "Accounts User"}],
			}
		).insert()
	frappe.permissions.add_user_permission("Cost Center", cost_center, user)
	return user


def make_large_budget(cost_center):
	return make_budget(
		budget_against="Cost Center", cost_center=cost_center, budget_amount=10000000, submit_budget=1
	)
