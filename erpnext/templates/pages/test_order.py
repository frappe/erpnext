from unittest.mock import patch

import frappe
from bs4 import BeautifulSoup

from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.templates.pages.order import get_context, get_payment_details
from erpnext.tests.permission_test_utils import as_user, make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite

MAKE_PAYMENT_REQUEST = "erpnext.accounts.doctype.payment_request.payment_request.make_payment_request"
MAKE_PORTAL_PURCHASE_INVOICE = (
	"erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice_from_portal"
)


class TestOrder(ERPNextTestSuite):
	@ERPNextTestSuite.change_settings("Buying Settings", {"show_pay_button": 0})
	def test_buying_pay_button_setting_skips_selling_documents(self):
		so = make_sales_order()
		po = create_purchase_order()
		user = make_fenced_user("_test_portal_payer@example.com", ["Accounts User"])

		with (
			as_user(user),
			patch.object(frappe, "get_installed_apps", return_value=["frappe", "erpnext", "payments"]),
		):
			self.assertEqual(get_payment_details(so), (True, so.grand_total))
			self.assertEqual(get_payment_details(po), (False, 0))

	def test_pay_button_matches_portal_payment_permissions(self):
		so = make_sales_order()
		invoice = create_sales_invoice()
		user = make_fenced_user("_test_portal_customer@example.com", ["Customer"])
		accounts_user = make_fenced_user("_test_portal_accounts@example.com", ["Accounts User"])
		customer = frappe.get_doc("Customer", so.customer)
		customer.append("portal_users", {"user": user})
		customer.save()
		cancelled_order = make_sales_order()
		cancelled_order.cancel()

		for payer, doc, allowed in (
			(user, so, True),
			(user, invoice, True),
			(user, make_sales_order(customer="_Test Customer 1"), False),
			(user, make_sales_order(do_not_submit=True), False),
			(user, cancelled_order, False),
			(user, create_purchase_order(), False),
			(accounts_user, so, True),
			("Guest", so, False),
		):
			with (
				self.subTest(payer=payer, doctype=doc.doctype, name=doc.name),
				as_user(payer),
				patch.object(frappe, "get_installed_apps", return_value=["frappe", "erpnext", "payments"]),
			):
				self.assertEqual(get_payment_details(doc), (True, doc.grand_total) if allowed else (False, 0))
				if payer in (user, "Guest"):
					self.assertRaises(
						frappe.PermissionError, make_payment_request, dt=doc.doctype, dn=doc.name
					)

	def test_pay_button_is_hidden_for_purchase_documents(self):
		purchase_order = create_purchase_order(qty=1, rate=100)
		purchase_invoice = make_purchase_invoice(purchase_order.name)
		purchase_invoice.insert()
		purchase_invoice.submit()
		user = make_fenced_user("purchase-portal-payments@example.com", ["Accounts User", "Purchase User"])

		for doc in (purchase_order, purchase_invoice):
			with (
				self.subTest(doctype=doc.doctype),
				as_user(user),
				patch.object(frappe, "get_installed_apps", return_value=["frappe", "erpnext", "payments"]),
				patch.dict(frappe.form_dict, {"doctype": doc.doctype, "name": doc.name}),
			):
				self.assertTrue(frappe.has_permission("Payment Request", "create"))
				self.assertTrue(doc.has_permission("read"))
				context = frappe._dict()
				get_context(context)
				self.assertFalse(context.show_pay_button)
				self.assertEqual(context.pay_amount, 0)
				template = frappe.get_template("erpnext/templates/pages/order.html")
				header = "".join(template.blocks["header_actions"](template.new_context(context)))
				self.assertIsNone(BeautifulSoup(header, "html.parser").find(id="pay-for-order"))

	def test_make_purchase_invoice_is_a_post_form(self):
		purchase_order = create_purchase_order(qty=1, rate=100)
		user = make_fenced_user("purchase-portal-invoice@example.com", ["Accounts User", "Purchase User"])

		with (
			as_user(user),
			patch.dict(frappe.form_dict, {"doctype": purchase_order.doctype, "name": purchase_order.name}),
		):
			frappe.session.data.csrf_token = 'portal-csrf-token"<&'
			context = frappe._dict()
			get_context(context)
			template = frappe.get_template("erpnext/templates/pages/order.html")
			header = "".join(template.blocks["header_actions"](template.new_context(context)))

		button = BeautifulSoup(header, "html.parser").find(attrs={"data-action": "make_purchase_invoice"})
		form = button.find_parent("form")
		fields = {field["name"]: field["value"] for field in form.find_all("input", type="hidden")}

		self.assertEqual(button.name, "button")
		self.assertEqual(form["method"], "post")
		self.assertEqual(form["action"], f"/api/method/{MAKE_PORTAL_PURCHASE_INVOICE}")
		self.assertEqual(
			fields, {"purchase_order_name": purchase_order.name, "csrf_token": 'portal-csrf-token"<&'}
		)

	def test_pay_button_is_a_post_form_to_make_payment_request(self):
		so = make_sales_order(customer="_Test Customer")
		user = make_fenced_user("_test_portal_payer@example.com", ["Accounts User"])

		installed_apps = [*frappe.get_installed_apps(), "payments"]
		with (
			as_user(user),
			patch.object(frappe, "get_installed_apps", return_value=installed_apps),
			patch.dict(frappe.form_dict, {"doctype": so.doctype, "name": so.name}),
			patch.dict(frappe.session.data, {"csrf_token": 'portal-csrf-token"<&'}),
		):
			context = frappe._dict()
			get_context(context)
			template = frappe.get_template("erpnext/templates/pages/order.html")
			html = "".join(template.blocks["header_actions"](template.new_context(context)))

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
