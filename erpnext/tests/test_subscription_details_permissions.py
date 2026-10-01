import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.payment_request.payment_request import get_subscription_details
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.tests.permission_test_utils import (
	as_user,
	assert_not_found,
	assert_refused,
	assert_refused_for_names,
	assert_refused_without,
	disable_mandatory_accounting_dimensions,
	insert_test_record,
	make_fenced_user,
)


class TestSubscriptionDetailsPermissions(FrappeTestCase):
	def setUp(self):
		disable_mandatory_accounting_dimensions()
		self.invoice_a = self.make_invoice_with_subscription("_Test Customer", "UP-SUB-A")
		self.invoice_b = self.make_invoice_with_subscription("_Test Customer 1", "UP-SUB-B")

	def tearDown(self):
		frappe.db.rollback()

	def make_invoice_with_subscription(self, customer, subscription):
		invoice = create_sales_invoice(customer=customer, do_not_save=True)
		invoice.insert()
		insert_test_record(
			"Subscription",
			{
				"name": subscription,
				"party_type": "Customer",
				"party": customer,
				"company": "_Test Company",
				"start_date": frappe.utils.nowdate(),
			},
		)
		insert_test_record(
			"Subscription Plan Detail",
			{
				"parent": subscription,
				"parenttype": "Subscription",
				"parentfield": "plans",
				"idx": 1,
				"qty": 2,
				"plan": "PLAN-" + subscription,
			},
		)
		insert_test_record(
			"Subscription Invoice",
			{
				"parent": subscription,
				"parenttype": "Subscription",
				"parentfield": "invoices",
				"idx": 1,
				"document_type": "Sales Invoice",
				"invoice": invoice.name,
			},
		)
		return invoice.name

	def details_kwargs(self, name):
		return {"reference_doctype": "Sales Invoice", "reference_name": name}

	def test_get_subscription_details_refuses_an_invoice_outside_the_customer_fence(self):
		fenced = make_fenced_user(
			"subscription-fenced@example.com", ["Accounts User"], [("Customer", "_Test Customer")]
		)
		with as_user(fenced):
			assert_refused_for_names(
				self, get_subscription_details, self.details_kwargs, [self.invoice_b], caller_supplied=True
			)
			assert_refused_without(
				self,
				["linked to", "_Test Customer 1"],
				get_subscription_details,
				**self.details_kwargs(self.invoice_b),
			)
			plans = get_subscription_details(**self.details_kwargs(self.invoice_a))
		self.assertEqual(plans[0].plan, "PLAN-UP-SUB-A")

	def test_get_subscription_details_allows_an_unfenced_accounts_user(self):
		user = make_fenced_user("subscription-open@example.com", ["Accounts User"])
		with as_user(user):
			plans = get_subscription_details(**self.details_kwargs(self.invoice_b))
		self.assertEqual(plans[0].plan, "PLAN-UP-SUB-B")

	def test_get_subscription_details_refuses_empty_names_and_finds_no_other_value(self):
		user = make_fenced_user("subscription-open@example.com", ["Accounts User"])
		with as_user(user):
			for name in ("", None):
				assert_refused(self, get_subscription_details, **self.details_kwargs(name))
			for name in (0, False, {"name": ["like", "%"]}, ["like", "%"]):
				assert_not_found(self, get_subscription_details, **self.details_kwargs(name))
