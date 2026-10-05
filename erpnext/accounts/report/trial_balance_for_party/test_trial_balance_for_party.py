# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.trial_balance_for_party.trial_balance_for_party import execute
from erpnext.accounts.utils import get_fiscal_year


class TestTrialBalanceForParty(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def run_report(self, **extra):
		fiscal_year, from_date, to_date = get_fiscal_year(today(), company="_Test Company")
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"party_type": "Customer",
				"fiscal_year": fiscal_year,
				"from_date": from_date,
				"to_date": to_date,
				**extra,
			}
		)
		return execute(filters)[1]

	def party_row(self, party, **extra):
		return next(row for row in self.run_report(party=party, **extra) if row.get("party") == party)

	def test_company_without_permission_is_refused(self):
		user = "test_tbp_company_permission@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "TBP", "roles": [{"role": "Accounts User"}]}
			).insert()
		frappe.permissions.add_user_permission("Company", "_Test Company 1", user)

		frappe.set_user(user)
		try:
			self.assertRaises(frappe.PermissionError, self.run_report)
		finally:
			frappe.set_user("Administrator")

	def test_balances_follow_gl_entry_permissions(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		other_receivable = create_account(
			account_name="_Test TBP Receivable",
			company="_Test Company",
			parent_account="Accounts Receivable - _TC",
			account_type="Receivable",
		)
		customer = "_Test TBP Customer"
		if not frappe.db.exists("Customer", customer):
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": customer,
					"customer_group": "_Test Customer Group",
					"territory": "_Test Territory",
				}
			).insert()
		create_sales_invoice(customer=customer, qty=1, rate=10000)
		create_sales_invoice(customer=customer, qty=1, rate=6000, debit_to=other_receivable)

		user = "test_tbp_account_permission@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "TBP", "roles": [{"role": "Accounts User"}]}
			).insert()
		frappe.permissions.add_user_permission("Account", "Debtors - _TC", user, applicable_for="GL Entry")

		frappe.set_user(user)
		try:
			row = self.party_row(customer)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(row["debit"], 10000)

	def test_totals_cover_only_permitted_parties(self):
		permitted, other = (
			make_customer("_Test TBP Permitted Customer"),
			make_customer("_Test TBP Other Customer"),
		)
		create_sales_invoice(customer=permitted, qty=1, rate=10000)
		create_sales_invoice(customer=other, qty=1, rate=6000)

		user = "test_tbp_party_permission@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "TBP", "roles": [{"role": "Accounts User"}]}
			).insert()
		frappe.permissions.add_user_permission("Customer", permitted, user)

		frappe.set_user(user)
		try:
			data = self.run_report()
		finally:
			frappe.set_user("Administrator")

		self.assertEqual({row["party"] for row in data[:-1]}, {permitted})
		self.assertEqual(data[-1]["debit"], 10000)


def make_customer(customer_name: str) -> str:
	if not frappe.db.exists("Customer", customer_name):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": customer_name,
				"customer_group": "_Test Customer Group",
				"territory": "_Test Territory",
			}
		).insert()
	return customer_name
