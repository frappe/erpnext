# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.desk.query_report import run
from frappe.permissions import add_user_permission, remove_user_permission
from frappe.tests.utils import FrappeTestCase

from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order


class TestSalesPartnerCommissionSummary(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("Sales Partner", "_Test SP Commission"):
			sp = frappe.new_doc("Sales Partner")
			sp.partner_name = "_Test SP Commission"
			sp.commission_rate = 5
			sp.insert()

		self.filters = {"company": "_Test Company", "doctype": "Sales Order"}
		self.report_name = "Sales Partner Commission Summary"

	def test_company_restriction_not_leaked(self):
		so = make_sales_order(do_not_save=1)
		so.sales_partner = "_Test SP Commission"
		so.save()
		so.submit()

		user = create_user("sp_summary_restricted@example.com", "Sales Manager").name

		# A user permitted on the order's company still sees it
		add_user_permission("Company", "_Test Company", user)
		try:
			frappe.set_user(user)
			permitted_rows = run(self.report_name, self.filters).get("result")[:-1]
		finally:
			frappe.set_user("Administrator")
			remove_user_permission("Company", "_Test Company", user)
		self.assertTrue(any(row.get("name") == so.name for row in permitted_rows))

		# A user restricted to another company does not see it
		add_user_permission("Company", "_Test Company 1", user)
		try:
			frappe.set_user(user)
			restricted_rows = run(self.report_name, self.filters).get("result")[:-1]
		finally:
			frappe.set_user("Administrator")
			remove_user_permission("Company", "_Test Company 1", user)
		self.assertFalse(any(row.get("name") == so.name for row in restricted_rows))
