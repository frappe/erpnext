# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.utils import add_days, getdate, today

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.selling.doctype.customer import customer_overview
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.tests.utils import ERPNextTestSuite

CUSTOMER = "_Test Customer"
COMPANY = "_Test Company"


class TestCustomerOverview(ERPNextTestSuite):
	def test_overview_sections(self):
		data = customer_overview.get_customer_overview(CUSTOMER, COMPANY)
		self.assertEqual(data["company"], COMPANY)
		self.assertEqual(data["period"], "Current Fiscal Year")
		self.assertIn("net_sales", data["position"])
		self.assertFalse(data["errors"])

	def test_receivables_ageing_adds_up_to_outstanding(self):
		data = customer_overview.get_customer_receivables(CUSTOMER, COMPANY)
		self.assertIn("limit", data["credit"])
		self.assertEqual(data["ageing"]["total"], data["outstanding"]["value"])
		self.assertEqual(data["ageing"]["overdue"], data["overdue"]["value"])

	def test_unknown_period_falls_back(self):
		data = customer_overview.get_customer_overview(CUSTOMER, COMPANY, period="Forever")
		self.assertEqual(data["period"], "Current Fiscal Year")

	def test_invoice_data_needs_accounts_access(self):
		with patch.object(customer_overview, "accounts_access", return_value=False):
			data = customer_overview.get_customer_overview(CUSTOMER, COMPANY)

			receivables = customer_overview.get_customer_receivables(CUSTOMER, COMPANY)

		self.assertEqual(data["position"], {})
		self.assertIsNone(data["trend"])
		self.assertNotIn("invoices", data["pipeline"])
		self.assertIsNone(receivables)

	def test_company_outside_user_permissions_is_refused(self):
		with patch.object(
			frappe.permissions, "get_user_permissions", return_value={"Company": [{"doc": "_Test Company 1"}]}
		):
			self.assertRaises(
				frappe.PermissionError, customer_overview.get_customer_overview, CUSTOMER, COMPANY
			)
			self.assertRaises(
				frappe.PermissionError, customer_overview.get_customer_transactions, CUSTOMER, COMPANY
			)
			self.assertRaises(
				frappe.PermissionError, customer_overview.get_customer_receivables, CUSTOMER, COMPANY
			)

	def test_transactions_are_capped(self):
		rows = customer_overview.get_customer_transactions(CUSTOMER, COMPANY, limit=500)
		self.assertLessEqual(len(rows), 100)
		dates = [r["date"] for r in rows]
		self.assertEqual(dates, sorted(dates, reverse=True))

	def test_customer_without_read_access_is_refused(self):
		with patch.object(frappe, "has_permission", return_value=False):
			self.assertRaises(
				frappe.PermissionError, customer_overview.get_customer_overview, CUSTOMER, COMPANY
			)
			self.assertRaises(
				frappe.PermissionError, customer_overview.get_customer_receivables, CUSTOMER, COMPANY
			)
			self.assertRaises(frappe.PermissionError, customer_overview.get_customer_companies, CUSTOMER)

	def test_credit_used_counts_unbilled_orders(self):
		before = customer_overview.get_customer_receivables(CUSTOMER, COMPANY)["credit"]["used"]
		so = make_sales_order(customer=CUSTOMER, company=COMPANY)
		after = customer_overview.get_customer_receivables(CUSTOMER, COMPANY)["credit"]["used"]
		self.assertEqual(after - before, so.base_grand_total)

	def test_totals_follow_user_permissions(self):
		customer = frappe.copy_doc(frappe.get_doc("Customer", CUSTOMER))
		customer.customer_name = "Overview Restricted Customer"
		customer.insert()
		si = create_sales_invoice(customer=customer.name, company=COMPANY, parent_cost_center="Main - _TC")
		as_of = getdate(today())
		user = create_user("customer_overview_restricted@example.com", "Accounts User", "Sales User")
		frappe.permissions.add_user_permission("Cost Center", "_Test Cost Center 2 - _TC", user.name)
		self.addCleanup(
			frappe.permissions.remove_user_permission, "Cost Center", "_Test Cost Center 2 - _TC", user.name
		)

		everyone = customer_overview.net_sales(customer.name, COMPANY, as_of, as_of)
		with self.set_user(user.name):
			restricted = customer_overview.net_sales(customer.name, COMPANY, as_of, as_of)
			unpaid = customer_overview.unpaid_invoices(customer.name, COMPANY, as_of)

		self.assertEqual(everyone - restricted, si.base_net_total)
		with self.set_user(user.name):
			self.assertNotIn(
				si.name, frappe.get_list("Sales Invoice", filters={"customer": customer.name}, pluck="name")
			)
		self.assertEqual(unpaid["count"], 0)

	def test_last_twelve_months_has_twelve_calendar_buckets(self):
		as_of = getdate("2026-09-30")
		start, end = customer_overview.resolve_period("Last 12 Months", COMPANY, as_of)
		self.assertEqual(start, getdate("2025-10-01"))
		self.assertEqual(end, as_of)

	def test_credit_balance_has_no_collection_days(self):
		for outstanding in (0, -100):
			self.assertIsNone(
				customer_overview.collection_days(CUSTOMER, COMPANY, getdate(today()), outstanding)
			)

	def test_restricted_user_cannot_read_whole_company_credit_usage(self):
		user = create_user("overview_credit@example.com", "Accounts User", "Sales User")
		frappe.permissions.add_user_permission("Cost Center", "_Test Cost Center 2 - _TC", user.name)
		with self.set_user(user.name), patch.object(customer_overview, "get_customer_outstanding") as total:
			self.assertIsNone(customer_overview.get_customer_receivables(CUSTOMER, COMPANY)["credit"]["used"])
			total.assert_not_called()

	def test_historical_overdue_uses_report_date(self):
		customer = frappe.copy_doc(frappe.get_doc("Customer", CUSTOMER))
		customer.customer_name = "Overview Historical Customer"
		customer.insert()
		si = create_sales_invoice(
			customer=customer.name, company=COMPANY, posting_date=add_days(today(), -60), do_not_submit=True
		)
		si.due_date = add_days(today(), -10)
		for term in si.payment_schedule:
			term.due_date = si.due_date
		si.save().submit()
		user = create_user("overview_history@example.com", "Accounts User", "Sales User")
		with self.set_user(user.name):
			before_due = customer_overview.receivables(customer.name, COMPANY, add_days(today(), -30))
			after_due = customer_overview.receivables(customer.name, COMPANY, today())
		self.assertEqual(before_due["overdue"], 0)
		self.assertEqual(after_due["overdue"], si.base_grand_total)

	def test_companies_include_journal_entry_receivables(self):
		customer = frappe.copy_doc(frappe.get_doc("Customer", CUSTOMER))
		customer.customer_name = "Overview Journal Customer"
		customer.insert()
		entry = make_journal_entry("Debtors - _TC", "Cash - _TC", 100, save=False)
		entry.accounts[0].party_type = "Customer"
		entry.accounts[0].party = customer.name
		entry.insert().submit()
		user = create_user("overview_journal@example.com", "Accounts User", "Sales User")
		with self.set_user(user.name):
			self.assertIn(COMPANY, customer_overview.get_customer_companies(customer.name))
			self.assertEqual(
				customer_overview.get_customer_receivables(customer.name, COMPANY)["outstanding"]["value"],
				100,
			)
		frappe.permissions.add_user_permission("Cost Center", "_Test Cost Center 2 - _TC", user.name)
		with self.set_user(user.name):
			self.assertNotIn(COMPANY, customer_overview.get_customer_companies(customer.name))

	def test_advances_match_summary_report(self):
		from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import execute

		user = create_user("overview_advances@example.com", "Accounts User", "Sales User")
		with self.set_user(user.name):
			rows = execute(
				{
					"company": COMPANY,
					"report_date": today(),
					"party": [CUSTOMER],
					"customer": CUSTOMER,
					"range": "30, 60, 90",
					"ageing_based_on": "Due Date",
				}
			)[1]
			expected = next((r.get("advance") for r in rows if r.get("party") == CUSTOMER), None)
			self.assertEqual(
				customer_overview.get_customer_receivables(CUSTOMER, COMPANY)["advances"]["value"], expected
			)

	def test_advances_missing_report_row_is_not_zero(self):
		with patch(
			"erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary.execute",
			return_value=([], []),
		):
			self.assertIsNone(customer_overview.reported_advances(CUSTOMER, COMPANY, today()))
