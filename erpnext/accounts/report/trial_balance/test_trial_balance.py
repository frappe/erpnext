# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from erpnext.accounts.report.trial_balance.trial_balance import execute


class TestTrialBalance(IntegrationTestCase):
	def setUp(self):
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.utils import get_fiscal_year

		self.company = create_company()
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
		create_accounting_dimension()

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
			company=self.company,
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
			{"company": self.company, "fiscal_year": self.fiscal_year, "branch": ["Location 1"]}
		)
		total_row = execute(filters)[1][-1]
		self.assertEqual(total_row["debit"], total_row["credit"])

	def tearDown(self):
		clear_dimension_defaults("Branch")
		disable_dimension()


def create_company(**args):
	args = frappe._dict(args)
	company = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": args.company_name or "Trial Balance Company",
			"country": args.country or "India",
			"default_currency": args.currency or "INR",
		}
	)
	company.insert(ignore_if_duplicate=True)
	return company.name


def create_accounting_dimension(**args):
	args = frappe._dict(args)
	document_type = args.document_type or "Branch"
	if frappe.db.exists("Accounting Dimension", document_type):
		accounting_dimension = frappe.get_doc("Accounting Dimension", document_type)
		accounting_dimension.disabled = 0
	else:
		accounting_dimension = frappe.new_doc("Accounting Dimension")
		accounting_dimension.document_type = document_type
		accounting_dimension.insert()

	accounting_dimension.set("dimension_defaults", [])
	accounting_dimension.append(
		"dimension_defaults",
		{
			"company": args.company or "Trial Balance Company",
			"automatically_post_balancing_accounting_entry": 1,
			"offsetting_account": args.offsetting_account or "Offsetting - TBC",
		},
	)
	accounting_dimension.save()


def disable_dimension(**args):
	args = frappe._dict(args)
	document_type = args.document_type or "Branch"
	dimension = frappe.get_doc("Accounting Dimension", document_type)
	dimension.disabled = 1
	dimension.save()


def clear_dimension_defaults(dimension_name):
	accounting_dimension = frappe.get_doc("Accounting Dimension", dimension_name)
	accounting_dimension.dimension_defaults = []
	accounting_dimension.save()
