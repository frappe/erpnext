# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.utils import today

from erpnext.accounts.report.trial_balance.trial_balance import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestTrialBalance(ERPNextTestSuite):
	def setUp(self):
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.utils import get_fiscal_year

		create_cost_center(
			cost_center_name="Test Cost Center",
			company="Trial Balance Company",
			parent_cost_center="Trial Balance Company - TBC",
		)
		create_account(
			account_name="Offsetting",
			company="Trial Balance Company",
			parent_account="Temporary Accounts - TBC",
		)
		self.fiscal_year = get_fiscal_year(today(), company="Trial Balance Company")[0]
		dim = frappe.get_doc("Accounting Dimension", "Branch")
		dim.append(
			"dimension_defaults",
			{
				"company": "Trial Balance Company",
				"automatically_post_balancing_accounting_entry": 1,
				"offsetting_account": "Offsetting - TBC",
			},
		)
		dim.save()

	def test_offsetting_entries_for_accounting_dimensions(self):
		"""
		Checks if Trial Balance Report is balanced when filtered using a particular Accounting Dimension
		"""
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		frappe.db.sql("delete from `tabSales Invoice` where company='Trial Balance Company'")
		frappe.db.sql("delete from `tabGL Entry` where company='Trial Balance Company'")

		branch1 = frappe.new_doc("Branch")
		branch1.branch = "Location 1"
		branch1.insert(ignore_if_duplicate=True)
		branch2 = frappe.new_doc("Branch")
		branch2.branch = "Location 2"
		branch2.insert(ignore_if_duplicate=True)

		si = create_sales_invoice(
			company="Trial Balance Company",
			debit_to="Debtors - TBC",
			cost_center="Test Cost Center - TBC",
			income_account="Sales - TBC",
			do_not_submit=1,
		)
		si.branch = "Location 1"
		si.items[0].branch = "Location 2"
		si.save()
		si.submit()

		filters = frappe._dict(
			{"company": "Trial Balance Company", "fiscal_year": self.fiscal_year, "branch": ["Location 1"]}
		)
		total_row = execute(filters)[1][-1]
		self.assertEqual(total_row["debit"], total_row["credit"])
