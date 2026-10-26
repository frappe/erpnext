from unittest.mock import patch

import frappe
from bs4 import BeautifulSoup
from frappe.utils import get_html_for_route

from erpnext.accounts.doctype.payment_request.payment_request import get_portal_payment_args
from erpnext.accounts.doctype.payment_request.test_payment_request import make_portal_user
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.templates.pages.order import get_payment_details
from erpnext.tests.permission_test_utils import as_user, make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite

MAKE_PAYMENT_REQUEST = "erpnext.accounts.doctype.payment_request.payment_request.make_payment_request"


class TestOrder(ERPNextTestSuite):
	def test_pay_button_only_for_documents_the_portal_can_pay(self):
		so = make_sales_order()
		po = create_purchase_order()
		user = make_portal_user("_test_portal_payer@example.com", so.customer)

		with (
			as_user(user),
			patch.object(frappe, "get_installed_apps", return_value=["frappe", "erpnext", "payments"]),
		):
			self.assertEqual(get_payment_details(so), (True, so.grand_total))
			self.assertEqual(get_payment_details(po), (False, 0))

	def test_pay_button_matches_portal_payment_permissions(self):
		so = make_sales_order()
		invoice = create_sales_invoice()
		user = make_portal_user("_test_portal_payer@example.com", so.customer)
		accounts_user = make_fenced_user("_test_portal_accounts@example.com", ["Accounts User"])
		cancelled_order = make_sales_order()
		cancelled_order.cancel()

		for payer, doc, allowed in (
			(user, so, True),
			(user, invoice, True),
			(user, make_sales_order(customer="_Test Customer 1"), False),
			(user, make_sales_order(do_not_submit=True), False),
			(user, cancelled_order, False),
			(user, create_purchase_order(), False),
			(accounts_user, so, False),
			("Guest", so, False),
		):
			with (
				self.subTest(payer=payer, doctype=doc.doctype, name=doc.name),
				as_user(payer),
				patch.object(frappe, "get_installed_apps", return_value=["frappe", "erpnext", "payments"]),
			):
				self.assertEqual(get_payment_details(doc), (True, doc.grand_total) if allowed else (False, 0))
				if allowed:
					self.assertEqual(get_portal_payment_args(doc.doctype, doc.name, "1").dn, doc.name)
				else:
					self.assertRaises(
						frappe.PermissionError, get_portal_payment_args, doc.doctype, doc.name, "1"
					)

	def test_pay_button_is_a_post_form_to_make_payment_request(self):
		so = make_sales_order(customer="_Test Customer")
		user = make_fenced_user("_test_portal_payer@example.com", ["Customer"])
		customer = frappe.get_doc("Customer", "_Test Customer")
		customer.append("portal_users", {"user": user})
		customer.save()

		self.addCleanup(setattr, frappe.local, "request", None)
		installed_apps = [*frappe.get_installed_apps(), "payments"]
		with as_user(user), patch.object(frappe, "get_installed_apps", return_value=installed_apps):
			frappe.session.data.csrf_token = 'portal-csrf-token"<&'
			html = get_html_for_route(f"/orders/{so.name}")

		pay_button = BeautifulSoup(html, "html.parser").find(id="pay-for-order")
		form = pay_button.find_parent("form")
		fields = {field["name"]: field["value"] for field in form.find_all("input", type="hidden")}

		self.assertEqual(pay_button.name, "button")
		self.assertEqual(form["method"], "post")
		self.assertEqual(form["action"], f"/api/method/{MAKE_PAYMENT_REQUEST}")
		self.assertEqual(
			fields,
			{
				"dn": so.name,
				"dt": "Sales Order",
				"submit_doc": "1",
				"order_type": "Shopping Cart",
				"csrf_token": 'portal-csrf-token"<&',
			},
		)
