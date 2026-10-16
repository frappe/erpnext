# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestWebsiteListForContact(ERPNextTestSuite):
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

	def test_website_permission_respects_user_permissions(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.tests.permission_test_utils import as_user, make_company_fenced_user

		invoice = create_sales_invoice()
		user = make_company_fenced_user("_test_fenced@example.com", ["Accounts User"], "_Test Company 1")

		with as_user(user):
			self.assertFalse(frappe.has_website_permission(invoice))

	def test_website_permission_for_customer_and_supplier_portal_user(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.controllers.website_list_for_contact import has_website_permission
		from erpnext.tests.permission_test_utils import as_user, make_fenced_user

		invoice = make_purchase_invoice(supplier="_Test Supplier", do_not_submit=True)
		user = make_fenced_user("_test_portal_party@example.com", ["Customer", "Supplier"])
		for doctype, name in (("Supplier", "_Test Supplier"), ("Customer", "_Test Customer 1")):
			party = frappe.get_doc(doctype, name)
			party.append("portal_users", {"user": user})
			party.save()

		self.assertTrue(has_website_permission(invoice, "read", user))
		with as_user(user):
			self.assertTrue(has_website_permission(invoice, "read", user))
