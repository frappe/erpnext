# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe

from erpnext.selling.doctype.customer import customer_overview
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
