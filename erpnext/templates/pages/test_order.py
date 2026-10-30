from unittest.mock import patch

import frappe
from bs4 import BeautifulSoup
from frappe.utils import get_html_for_route

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

		with patch.object(frappe, "get_installed_apps", return_value=["frappe", "erpnext", "payments"]):
			self.assertEqual(get_payment_details(so), (True, so.grand_total))
			self.assertEqual(get_payment_details(po), (False, 0))

	def test_pay_button_is_a_post_form_to_make_payment_request(self):
		so = make_sales_order(customer="_Test Customer")
		user = make_fenced_user("_test_portal_payer@example.com", ["Customer"])
		customer = frappe.get_doc("Customer", "_Test Customer")
		customer.append("portal_users", {"user": user})
		customer.save()

		self.addCleanup(setattr, frappe.local, "request", None)
		installed_apps = [*frappe.get_installed_apps(), "payments"]
		with as_user(user), patch.object(frappe, "get_installed_apps", return_value=installed_apps):
			frappe.session.data.csrf_token = "portal-csrf-token"
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
				"csrf_token": "portal-csrf-token",
			},
		)
