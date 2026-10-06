# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestWebsiteListForContact(ERPNextTestSuite):
	def test_website_permission_respects_user_permissions(self):
		# A desk user who is not a portal Customer/Supplier user must not gain access to a
		# document through the website permission check when a User Permission excludes it;
		# the check should defer to the standard document-level permission.
		from erpnext.controllers.website_list_for_contact import has_website_permission
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		so = make_sales_order()
		other_company = frappe.db.get_value("Company", {"name": ["!=", so.company]})

		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"{frappe.generate_hash(length=10)}@example.com",
				"first_name": "Portal Perm",
				"roles": [{"role": "Sales User"}],
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user.name,
				"allow": "Company",
				"for_value": other_company,
			}
		).insert(ignore_permissions=True)

		with self.set_user(user.name):
			self.assertFalse(frappe.has_permission("Sales Order", "read", doc=so.name))
			self.assertFalse(has_website_permission(so, "read", user.name))

	def test_get_list_context_currency_symbols(self):
		# get_list_context builds the enabled-currency symbol map via frappe.get_all (converted from
		# raw SQL). Exercises that query and asserts a known enabled currency is present.
		from erpnext.controllers.website_list_for_contact import get_list_context

		context = get_list_context()

		symbols = json.loads(context["currency_symbols"])
		self.assertIsInstance(symbols, dict)
		self.assertIn("USD", symbols)

	def test_rfq_transaction_list_returns_supplier_rfq(self):
		# rfq_transaction_list filters RFQs by the supplier (parties[0]) and uses SELECT DISTINCT with
		# ORDER BY creation -- both must be valid on Postgres, and the supplier filter must compare to the
		# party value (not a stray `party[0]` column reference).
		from erpnext.buying.doctype.request_for_quotation.test_request_for_quotation import (
			make_request_for_quotation,
		)
		from erpnext.controllers.website_list_for_contact import rfq_transaction_list

		rfq = make_request_for_quotation()
		supplier = rfq.suppliers[0].supplier

		rows = rfq_transaction_list(
			"Request for Quotation Supplier", "Request for Quotation", [supplier], 0, 20
		)
		self.assertIn(rfq.name, [row.name for row in rows])
