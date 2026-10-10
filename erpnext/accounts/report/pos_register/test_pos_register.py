# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.pos_register.pos_register import execute
from erpnext.selling.doctype.customer.test_customer import make_customer
from erpnext.tests.utils import ERPNextTestSuite

PAYMENT_ACCOUNTS = {"Cash": "Cash - _TC", "_Test POS Register Card": "_Test Bank - _TC"}


class TestPOSRegister(ERPNextTestSuite):
	def setUp(self):
		self.pos_profile = make_pos_profile().name
		make_card_mode_of_payment()

	def test_report_executes(self):
		# Smoke-guards the raw-SQL -> query-builder port: the report's POS Invoice query must
		# compile and run on both MariaDB and postgres (it returns columns + a row list either way).
		company = frappe.db.get_value("Company", {}, "name")
		columns, data = execute(
			frappe._dict({"company": company, "from_date": add_days(today(), -365), "to_date": today()})
		)
		self.assertTrue(columns)
		self.assertIsInstance(data, list)

	def test_sales_invoices_made_at_the_pos_are_listed(self):
		invoice = self.make_pos_sales_invoice({"Cash": 1000})
		consolidated = self.make_pos_sales_invoice({"Cash": 1000})
		frappe.db.set_value("Sales Invoice", consolidated.name, "is_consolidated", 1)

		rows = self.run_report(group_by="")
		self.assertEqual(
			[(row.invoice_type, row.pos_invoice, row.paid_amount) for row in rows],
			[("Sales Invoice", invoice.name, 1000)],
		)

	def test_payment_method_grouping_counts_each_grand_total_once(self):
		self.make_pos_sales_invoice({"Cash": 600, "_Test POS Register Card": 400})
		self.make_pos_sales_invoice({"Cash": 500}, rate=500)

		subtotals = [row for row in self.run_report(group_by="Payment Method") if row.get("bold")]
		self.assertEqual(
			[(row["mode_of_payment"], row["grand_total"], row["paid_amount"]) for row in subtotals],
			[("Cash", 1500, 1100), ("_Test POS Register Card", 0, 400)],
		)

	def test_change_is_deducted_in_company_currency(self):
		self.make_pos_sales_invoice(
			{"Cash": 15},
			rate=10,
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=50,
		)

		for group_by in ("Customer", "Payment Method"):
			row = self.run_report(group_by=group_by)[0]
			self.assertEqual((row.grand_total, row.paid_amount), (500, 500))

	def test_subtotals_include_only_permitted_invoices(self):
		self.make_pos_sales_invoice({"Cash": 1000})
		self.make_pos_sales_invoice(
			{"Cash": 7000}, rate=7000, customer=make_customer("_Test POS Register Customer")
		)
		user = make_user_restricted_to_customer("_Test Customer")

		frappe.set_user(user)
		try:
			rows = self.run_report(group_by="POS Profile", pos_profile=None)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual([row.get("grand_total") for row in rows if row], [1000, 1000])

	def make_pos_sales_invoice(self, payments, rate=1000, **args):
		si = create_sales_invoice(rate=rate, do_not_save=True, **args)
		si.update({"is_pos": 1, "pos_profile": self.pos_profile, "account_for_change_amount": "Cash - _TC"})
		for mode_of_payment, amount in payments.items():
			si.append(
				"payments",
				{
					"mode_of_payment": mode_of_payment,
					"account": PAYMENT_ACCOUNTS[mode_of_payment],
					"amount": amount,
				},
			)
		si.insert()
		si.submit()
		return si

	def run_report(self, **filters):
		filters = {
			"company": "_Test Company",
			"from_date": today(),
			"to_date": today(),
			"pos_profile": self.pos_profile,
			**filters,
		}
		return execute(frappe._dict(filters))[1]


def make_card_mode_of_payment():
	if not frappe.db.exists("Mode of Payment", "_Test POS Register Card"):
		frappe.get_doc(
			{
				"doctype": "Mode of Payment",
				"mode_of_payment": "_Test POS Register Card",
				"type": "Bank",
				"accounts": [{"company": "_Test Company", "default_account": "_Test Bank - _TC"}],
			}
		).insert()


def make_user_restricted_to_customer(customer):
	user = "test_pos_register@example.com"
	if not frappe.db.exists("User", user):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": user,
				"first_name": "POS Register",
				"roles": [{"role": "Accounts User"}],
			}
		).insert()
	frappe.permissions.add_user_permission("Customer", customer, user)
	return user
