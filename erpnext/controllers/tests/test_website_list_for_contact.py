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

	def test_portal_list_returns_only_row_fields(self):
		from frappe.www.list import get_list_data
		from frappe.www.portal import get as get_portal_list

		from erpnext.selling.doctype.quotation.test_quotation import make_quotation
		from erpnext.tests.permission_test_utils import as_user, make_fenced_user

		quotation = make_quotation(party_name="_Test Customer")
		user = make_fenced_user("_test_portal_customer@example.com", ["Customer"])
		customer = frappe.get_doc("Customer", "_Test Customer")
		customer.append("portal_users", {"user": user})
		customer.save()

		with as_user(user):
			rows = json.loads(frappe.as_json(get_list_data(doctype="Quotation")))
			rendered = get_portal_list(doctype="Quotation")

		row = next(row for row in rows if row["name"] == quotation.name)
		self.assertFalse(row.get("items"))
		self.assertFalse(row.get("payment_schedule"))
		self.assertNotIn("party_name", row)
		self.assertEqual(row["grand_total"], quotation.grand_total)
		self.assertTrue(any(quotation.name in html for html in rendered["result"]))

	def make_drop_ship_purchase_order(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

		purchase_order = create_purchase_order(do_not_save=1)
		purchase_order.customer = "_Test Customer"
		purchase_order.insert()
		purchase_order.submit()
		return purchase_order

	def make_portal_user(self, email, role, party_doctype, party):
		from erpnext.tests.permission_test_utils import make_fenced_user

		user = make_fenced_user(email, [role])
		party_doc = frappe.get_doc(party_doctype, party)
		party_doc.append("portal_users", {"user": user})
		party_doc.save()
		return user

	def test_customer_portal_user_cannot_open_drop_ship_purchase_order(self):
		from erpnext.tests.permission_test_utils import as_user

		purchase_order = self.make_drop_ship_purchase_order()
		user = self.make_portal_user(
			"_test_drop_ship_customer@example.com", "Customer", "Customer", "_Test Customer"
		)

		with as_user(user):
			self.assertFalse(frappe.has_website_permission(purchase_order))

	def test_customer_portal_list_leaves_out_drop_ship_purchase_order(self):
		from frappe.www.list import get_list_data

		from erpnext.tests.permission_test_utils import as_user

		purchase_order = self.make_drop_ship_purchase_order()
		user = self.make_portal_user(
			"_test_drop_ship_customer@example.com", "Customer", "Customer", "_Test Customer"
		)

		with as_user(user):
			rows = get_list_data(doctype="Purchase Order")

		self.assertNotIn(purchase_order.name, [row.name for row in rows])

	def test_supplier_portal_user_still_sees_drop_ship_purchase_order(self):
		from frappe.www.list import get_list_data

		from erpnext.tests.permission_test_utils import as_user

		purchase_order = self.make_drop_ship_purchase_order()
		user = self.make_portal_user(
			"_test_drop_ship_supplier@example.com", "Supplier", "Supplier", "_Test Supplier"
		)

		with as_user(user):
			self.assertTrue(frappe.has_website_permission(purchase_order))
			rows = get_list_data(doctype="Purchase Order")

		self.assertIn(purchase_order.name, [row.name for row in rows])
