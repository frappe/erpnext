# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import set_request

from erpnext.tests.permission_test_utils import as_user, make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite
from erpnext.www.banking import get_context


class TestBankingPage(ERPNextTestSuite):
	def setUp(self):
		set_request(method="GET", path="/banking")

	def test_page_loads_only_for_desk_users(self):
		with as_user("Guest"):
			self.assertRaises(frappe.Redirect, get_context, {})

		with as_user(make_fenced_user("banking-website@example.com", [])):
			self.assertRaises(frappe.PermissionError, get_context, {})

		with as_user(make_fenced_user("banking-accounts@example.com", ["Accounts User"])):
			self.assertTrue(get_context({}).boot)
