# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.utils import getdate, today

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
		si = create_sales_invoice(customer=CUSTOMER, company=COMPANY, parent_cost_center="Main - _TC")
		as_of = getdate(today())
		user = create_user("customer_overview_restricted@example.com", "Accounts User", "Sales User")
		frappe.permissions.add_user_permission("Cost Center", "_Test Cost Center 2 - _TC", user.name)
		self.addCleanup(
			frappe.permissions.remove_user_permission, "Cost Center", "_Test Cost Center 2 - _TC", user.name
		)

		everyone = customer_overview.net_sales(CUSTOMER, COMPANY, as_of, as_of)
		with self.set_user(user.name):
			restricted = customer_overview.net_sales(CUSTOMER, COMPANY, as_of, as_of)
			unpaid = customer_overview.unpaid_invoices(CUSTOMER, COMPANY, as_of)

		self.assertEqual(everyone - restricted, si.base_net_total)
		self.assertNotIn(
			si.name, frappe.get_all("Sales Invoice", {"cost_center": "_Test Cost Center 2 - _TC"})
		)
		self.assertEqual(unpaid["count"], 0)
